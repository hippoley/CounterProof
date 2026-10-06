import pytest

from skill_factory.evolution.evidence_lifecycle import (
    EvidenceLifecycle,
    merge_lifecycle_signals,
    validate_lifecycle_transition,
)


@pytest.mark.parametrize(
    ("previous", "current"),
    [
        (EvidenceLifecycle.CURRENT, EvidenceLifecycle.CURRENT),
        (EvidenceLifecycle.CURRENT, EvidenceLifecycle.STALE),
        (EvidenceLifecycle.CURRENT, EvidenceLifecycle.CONFLICTING),
        (EvidenceLifecycle.CURRENT, EvidenceLifecycle.SUPERSEDED),
        (EvidenceLifecycle.STALE, EvidenceLifecycle.SUPERSEDED),
        (EvidenceLifecycle.CONFLICTING, EvidenceLifecycle.SUPERSEDED),
        (EvidenceLifecycle.SUPERSEDED, EvidenceLifecycle.SUPERSEDED),
    ],
)
def test_allowed_lifecycle_transitions(previous, current):
    validate_lifecycle_transition(previous, current)


@pytest.mark.parametrize(
    ("previous", "current"),
    [
        (EvidenceLifecycle.SUPERSEDED, EvidenceLifecycle.CURRENT),
        (EvidenceLifecycle.SUPERSEDED, EvidenceLifecycle.STALE),
        (EvidenceLifecycle.STALE, EvidenceLifecycle.CURRENT),
        (EvidenceLifecycle.CONFLICTING, EvidenceLifecycle.CURRENT),
    ],
)
def test_lifecycle_does_not_silently_move_backwards(previous, current):
    with pytest.raises(ValueError, match="invalid evidence lifecycle transition"):
        validate_lifecycle_transition(previous, current)


@pytest.mark.parametrize(
    ("signals", "expected"),
    [
        ((EvidenceLifecycle.CURRENT, EvidenceLifecycle.STALE), EvidenceLifecycle.STALE),
        (
            (EvidenceLifecycle.STALE, EvidenceLifecycle.CONFLICTING),
            EvidenceLifecycle.CONFLICTING,
        ),
        (
            (EvidenceLifecycle.CONFLICTING, EvidenceLifecycle.SUPERSEDED),
            EvidenceLifecycle.SUPERSEDED,
        ),
        (
            (
                EvidenceLifecycle.CURRENT,
                EvidenceLifecycle.STALE,
                EvidenceLifecycle.CONFLICTING,
                EvidenceLifecycle.SUPERSEDED,
            ),
            EvidenceLifecycle.SUPERSEDED,
        ),
    ],
)
def test_lifecycle_signal_precedence(signals, expected):
    assert merge_lifecycle_signals(*signals) is expected


def test_lifecycle_signal_merge_requires_input():
    with pytest.raises(ValueError, match="at least one"):
        merge_lifecycle_signals()
