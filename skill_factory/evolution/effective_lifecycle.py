from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .evidence_freshness import FreshnessObservation, resolve_contract_freshness
from .evidence_lifecycle import EvidenceLifecycle, resolve_effective_lifecycle
from .evidence_supersession import EvidenceGraph, load_evidence_graph


@dataclass(frozen=True)
class EffectiveLifecycleObservation:
    contract_id: str
    evidence_id: str | None
    declared: EvidenceLifecycle
    freshness_signal: EvidenceLifecycle | None
    graph_signal: EvidenceLifecycle | None
    effective: EvidenceLifecycle
    freshness_reason: str | None


def resolve_effective_contract_lifecycles(
    suite_file: Path,
    *,
    graph_file: Path | None = None,
    freshness_observations: list[FreshnessObservation] | None = None,
) -> list[EffectiveLifecycleObservation]:
    raw = yaml.safe_load(suite_file.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("contracts"), list):
        raise TypeError("invalid reality contract suite")

    freshness = freshness_observations
    if freshness is None:
        freshness = resolve_contract_freshness(suite_file)
    freshness_by_id = {item.contract_id: item for item in freshness}

    graph: EvidenceGraph | None = load_evidence_graph(graph_file) if graph_file else None

    observations: list[EffectiveLifecycleObservation] = []
    for contract in raw["contracts"]:
        contract_id = str(contract["id"])
        declared = EvidenceLifecycle(
            contract.get("lifecycle", EvidenceLifecycle.CURRENT.value)
        )
        freshness_item = freshness_by_id.get(contract_id)
        freshness_signal: EvidenceLifecycle | None = None
        freshness_reason: str | None = None
        if freshness_item is not None:
            freshness_reason = freshness_item.reason
            if freshness_item.suggested_lifecycle is not declared:
                freshness_signal = freshness_item.suggested_lifecycle

        evidence_id = contract.get("evidence_id")
        graph_signal: EvidenceLifecycle | None = None
        if graph is not None and evidence_id is not None:
            try:
                graph_signal = graph.lifecycle_suggestions[str(evidence_id)]
            except KeyError as exc:
                raise ValueError(
                    f"contract {contract_id!r} evidence_id {evidence_id!r} "
                    "is missing from evidence graph"
                ) from exc

        effective = resolve_effective_lifecycle(
            declared,
            freshness_signal=freshness_signal,
            graph_signal=graph_signal,
        )
        observations.append(
            EffectiveLifecycleObservation(
                contract_id=contract_id,
                evidence_id=str(evidence_id) if evidence_id is not None else None,
                declared=declared,
                freshness_signal=freshness_signal,
                graph_signal=graph_signal,
                effective=effective,
                freshness_reason=freshness_reason,
            )
        )

    return observations
