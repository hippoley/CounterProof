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
