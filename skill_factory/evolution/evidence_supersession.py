from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .claim_matrix import EvidenceScope, OverallClaim


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
