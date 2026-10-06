from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from .claim_matrix import EvidenceScope, OverallClaim, load_claim_matrix
from .evidence_lifecycle import EvidenceLifecycle


class EvidencePolarity(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    INCONCLUSIVE = "INCONCLUSIVE"


class EvidenceRelation(str, Enum):
    SUPERSEDES = "SUPERSEDES"
    CONFLICTS = "CONFLICTS"
    PARALLEL = "PARALLEL"
    UNRELATED = "UNRELATED"


@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    claim_key: str
    observed_at: datetime
    scope: EvidenceScope
    overall_claim: OverallClaim


@dataclass(frozen=True)
class EvidenceRelationResult:
    relation: EvidenceRelation
    old_id: str
    new_id: str
    reason: str


def claim_polarity(claim: OverallClaim) -> EvidencePolarity:
    if claim is OverallClaim.PROVEN:
        return EvidencePolarity.SUPPORTS
    if claim is OverallClaim.CONTRADICTED:
        return EvidencePolarity.CONTRADICTS
    return EvidencePolarity.INCONCLUSIVE


def resolve_evidence_relation(
    old: EvidenceRecord,
    new: EvidenceRecord,
) -> EvidenceRelationResult:
    if old.claim_key != new.claim_key:
        return EvidenceRelationResult(
            relation=EvidenceRelation.UNRELATED,
            old_id=old.id,
            new_id=new.id,
            reason="evidence refers to different claims",
        )

    if new.observed_at <= old.observed_at:
        raise ValueError(
            "new evidence must have observed_at later than old evidence"
        )

    old_polarity = claim_polarity(old.overall_claim)
    new_polarity = claim_polarity(new.overall_claim)

    if EvidencePolarity.INCONCLUSIVE in {old_polarity, new_polarity}:
        return EvidenceRelationResult(
            relation=EvidenceRelation.PARALLEL,
            old_id=old.id,
            new_id=new.id,
            reason="at least one evidence record is not claim-directional",
        )

    if old_polarity is not new_polarity:
        return EvidenceRelationResult(
            relation=EvidenceRelation.CONFLICTS,
            old_id=old.id,
            new_id=new.id,
            reason=(
                f"new evidence {new_polarity.value.lower()} the claim while "
                f"old evidence {old_polarity.value.lower()} it"
            ),
        )

    if new.scope.rank >= old.scope.rank:
        return EvidenceRelationResult(
            relation=EvidenceRelation.SUPERSEDES,
            old_id=old.id,
            new_id=new.id,
            reason=(
                "newer claim-directional evidence has the same polarity "
                "and equal-or-stronger scope"
            ),
        )

    return EvidenceRelationResult(
        relation=EvidenceRelation.PARALLEL,
        old_id=old.id,
        new_id=new.id,
        reason=(
            "newer evidence has the same polarity but weaker evidence scope"
        ),
    )


@dataclass(frozen=True)
class EvidenceGraph:
    records: tuple[EvidenceRecord, ...]
    relations: tuple[EvidenceRelationResult, ...]
    lifecycle_suggestions: dict[str, EvidenceLifecycle]


def evidence_record_from_mapping(raw: dict[str, Any]) -> EvidenceRecord:
    try:
        observed_at = datetime.fromisoformat(str(raw["observed_at"]).replace("Z", "+00:00"))
        if observed_at.tzinfo is None:
            raise ValueError("observed_at must include a timezone")
        return EvidenceRecord(
            id=str(raw["id"]),
            claim_key=str(raw["claim_key"]),
            observed_at=observed_at,
            scope=EvidenceScope(raw["scope"]),
            overall_claim=OverallClaim(raw["overall_claim"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid evidence record: {exc}") from exc


def evidence_record_from_claim_reference(
    graph_path: Path,
    raw: dict[str, Any],
) -> EvidenceRecord:
    graph_dir = graph_path.parent.resolve()
    manifest_path = (graph_dir / str(raw["manifest"])).resolve()
    try:
        manifest_path.relative_to(graph_dir)
    except ValueError as exc:
        raise ValueError(
            "evidence graph manifest references must stay within the graph directory"
        ) from exc

    manifest = load_claim_matrix(manifest_path)
    claim_id = str(raw["claim_id"])
    claim = next((item for item in manifest.claims if item.id == claim_id), None)
    if claim is None:
        raise ValueError(
            f"claim {claim_id!r} not found in {raw['manifest']!r}"
        )

    try:
        observed_at = datetime.fromisoformat(
            str(raw["observed_at"]).replace("Z", "+00:00")
        )
        if observed_at.tzinfo is None:
            raise ValueError("observed_at must include a timezone")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid evidence record: {exc}") from exc

    stable_source = claim.receipt_case or manifest.source_pr or manifest.title
    claim_key = str(raw.get("claim_key") or f"{stable_source}:{claim.id}")
    return EvidenceRecord(
        id=str(raw["id"]),
        claim_key=claim_key,
        observed_at=observed_at,
        scope=claim.evidence_scope,
        overall_claim=claim.overall_claim,
    )


def build_evidence_graph(records: list[EvidenceRecord]) -> EvidenceGraph:
    ids = [record.id for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("evidence record ids must be unique")

    relations: list[EvidenceRelationResult] = []
    lifecycle = {record.id: EvidenceLifecycle.CURRENT for record in records}

    by_claim: dict[str, list[EvidenceRecord]] = {}
    for record in records:
        by_claim.setdefault(record.claim_key, []).append(record)

    for claim_records in by_claim.values():
        ordered = sorted(claim_records, key=lambda record: record.observed_at)
        for old_index, old in enumerate(ordered):
            for new in ordered[old_index + 1 :]:
                result = resolve_evidence_relation(old, new)
                relations.append(result)
                if result.relation is EvidenceRelation.SUPERSEDES:
                    lifecycle[old.id] = EvidenceLifecycle.SUPERSEDED
                elif result.relation is EvidenceRelation.CONFLICTS:
                    if lifecycle[old.id] is not EvidenceLifecycle.SUPERSEDED:
                        lifecycle[old.id] = EvidenceLifecycle.CONFLICTING
                    if lifecycle[new.id] is not EvidenceLifecycle.SUPERSEDED:
                        lifecycle[new.id] = EvidenceLifecycle.CONFLICTING

    return EvidenceGraph(
        records=tuple(records),
        relations=tuple(relations),
        lifecycle_suggestions=lifecycle,
    )


def load_evidence_graph(path: Path) -> EvidenceGraph:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError("invalid evidence graph manifest")
    evidence = raw.get("evidence")
    if not isinstance(evidence, list):
        raise TypeError("evidence graph requires an evidence list")
    records = [
        evidence_record_from_claim_reference(path, item)
        if isinstance(item, dict) and "manifest" in item
        else evidence_record_from_mapping(item)
        for item in evidence
    ]
    return build_evidence_graph(records)
