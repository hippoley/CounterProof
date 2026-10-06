from __future__ import annotations

from enum import Enum


class EvidenceLifecycle(str, Enum):
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"
    STALE = "STALE"
    CONFLICTING = "CONFLICTING"


def validate_lifecycle_transition(previous: EvidenceLifecycle, current: EvidenceLifecycle) -> None:
    allowed = {
        EvidenceLifecycle.CURRENT: {
            EvidenceLifecycle.CURRENT,
            EvidenceLifecycle.SUPERSEDED,
            EvidenceLifecycle.STALE,
            EvidenceLifecycle.CONFLICTING,
        },
        EvidenceLifecycle.STALE: {
            EvidenceLifecycle.STALE,
            EvidenceLifecycle.SUPERSEDED,
            EvidenceLifecycle.CONFLICTING,
        },
        EvidenceLifecycle.CONFLICTING: {
            EvidenceLifecycle.CONFLICTING,
            EvidenceLifecycle.SUPERSEDED,
        },
        EvidenceLifecycle.SUPERSEDED: {
            EvidenceLifecycle.SUPERSEDED,
        },
    }
    if current not in allowed[previous]:
        raise ValueError(
            f"invalid evidence lifecycle transition: {previous.value} -> {current.value}"
        )


_LIFECYCLE_PRECEDENCE = {
    EvidenceLifecycle.CURRENT: 0,
    EvidenceLifecycle.STALE: 1,
    EvidenceLifecycle.CONFLICTING: 2,
    EvidenceLifecycle.SUPERSEDED: 3,
}


def merge_lifecycle_signals(
    *signals: EvidenceLifecycle,
) -> EvidenceLifecycle:
    if not signals:
        raise ValueError("at least one evidence lifecycle signal is required")
    return max(signals, key=_LIFECYCLE_PRECEDENCE.__getitem__)


def resolve_effective_lifecycle(
    declared: EvidenceLifecycle,
    *,
    freshness_signal: EvidenceLifecycle | None = None,
    graph_signal: EvidenceLifecycle | None = None,
) -> EvidenceLifecycle:
    signals = [declared]
    if freshness_signal is not None:
        signals.append(freshness_signal)
    if graph_signal is not None:
        signals.append(graph_signal)
    return merge_lifecycle_signals(*signals)
