"""Independent, proposal-scoped consumer for the 14 criterionMet parity cases.

This is *not* an implementation of a SCITT draft, a signature verifier, or the
producer's Python/Go reader. It checks the downstream reporting boundary after
evidence has already met the fixture's stated authenticated/bound/trusted/fresh
preconditions. Never use it to make a real-world completion assertion.
"""
from __future__ import annotations

from typing import Any


def judge_criterion(controller: Any, criterion: str, reported: str) -> tuple[str, str, str]:
    """Return (decision, reason, owed) from the pinned proposal-layer test contract."""
    if controller not in (None, "succeeded", "failed"):
        raise ValueError("unsupported controller")
    if criterion not in ("true", "false", "absent", "null"):
        raise ValueError("unsupported criterionMet")
    if reported not in ("NOT_PROVIDED", "PROVEN_TO_POLICY", "NOT_SATISFIED", "INDETERMINATE", "CONFLICT"):
        raise ValueError("unsupported reported result")

    if criterion in ("absent", "null"):
        owed = "INDETERMINATE"
    elif criterion == "false" and controller == "succeeded":
        owed = "CONFLICT"
    elif criterion == "false":
        owed = "NOT_SATISFIED"
    else:
        owed = "PROVEN_TO_POLICY"

    if reported == owed:
        return "conformant", "result_follows_presentation", owed
    if criterion in ("absent", "null"):
        if reported == "NOT_SATISFIED":
            return "nonconformant", "negative_without_observation", owed
        return "ambiguous", "criterion_unreported", owed
    if owed == "CONFLICT" and reported in ("NOT_SATISFIED", "PROVEN_TO_POLICY"):
        return "ambiguous", "conflict_erased", owed
    if reported == "INDETERMINATE":
        return "ambiguous", "observation_outcome_not_reported", owed

    # Unsupported disagreement: do not manufacture normative certainty.
    return "ambiguous", "outside_pinned_subset", owed
