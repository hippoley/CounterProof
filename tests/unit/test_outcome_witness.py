import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from skill_factory.evolution.outcome_witness import (
    OutcomeWitnessError,
    validate_outcome_witness,
)

FIXTURE = Path("examples/outcome_witness/window-contradicted.json")


def _fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_physical_window_example_is_admitted_when_fresh():
    payload = _fixture()
    validate_outcome_witness(
        payload,
        now=datetime(2026, 10, 8, 3, 30, 1, tzinfo=timezone.utc),
    )


def test_ack_style_record_without_external_observation_is_not_a_witness():
    payload = _fixture()
    payload.pop("observation")

    with pytest.raises(OutcomeWitnessError, match="observation"):
        validate_outcome_witness(
            payload,
            now=datetime(2026, 10, 8, 3, 30, 1, tzinfo=timezone.utc),
        )


def test_stale_observation_cannot_claim_contradicted():
    payload = _fixture()

    with pytest.raises(OutcomeWitnessError, match="stale observation"):
        validate_outcome_witness(
            payload,
            now=datetime(2026, 10, 8, 3, 31, 0, tzinfo=timezone.utc),
        )


def test_stale_observation_may_remain_inconclusive():
    payload = _fixture()
    payload["verdict"] = "INCONCLUSIVE"

    validate_outcome_witness(
        payload,
        now=datetime(2026, 10, 8, 3, 31, 0, tzinfo=timezone.utc),
    )


def test_executor_ack_is_not_allowed_to_replace_observer_authority():
    payload = _fixture()
    payload["observer"]["authority"] = ""

    with pytest.raises(OutcomeWitnessError, match="authority"):
        validate_outcome_witness(
            payload,
            now=datetime(2026, 10, 8, 3, 30, 1, tzinfo=timezone.utc),
        )


def test_action_reference_mismatch_is_rejected():
    payload = _fixture()

    with pytest.raises(OutcomeWitnessError, match="action_ref"):
        validate_outcome_witness(
            payload,
            now=datetime(2026, 10, 8, 3, 30, 1, tzinfo=timezone.utc),
            expected_action_ref={
                "type": "otel_span",
                "id": "different-action",
            },
        )


def test_matching_action_reference_is_admitted():
    payload = _fixture()

    validate_outcome_witness(
        payload,
        now=datetime(2026, 10, 8, 3, 30, 1, tzinfo=timezone.utc),
        expected_action_ref=payload["action_ref"],
    )
