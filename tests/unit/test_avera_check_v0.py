from __future__ import annotations

import copy
import json
from pathlib import Path

from skill_factory.evolution.avera_check_v0 import (
    AVERA_CHECK_V0_SCHEMA,
    avera_check_v0_digest,
    verify_avera_check_v0,
)

FIXTURE_DIR = Path("examples/handoff/avera-check-v0")


def _fixture() -> tuple[dict, bytes, bytes]:
    envelope = json.loads((FIXTURE_DIR / "envelope.json").read_text(encoding="utf-8"))
    baseline = (FIXTURE_DIR / "baseline.xml").read_bytes()
    current = (FIXTURE_DIR / "current.xml").read_bytes()
    return envelope, baseline, current


def test_upstream_avera_v0_frozen_example_verifies_end_to_end():
    envelope, baseline, current = _fixture()

    assert envelope["schema_version"] == AVERA_CHECK_V0_SCHEMA
    assert avera_check_v0_digest(envelope) == envelope["digest"]
    assert verify_avera_check_v0(
        envelope,
        baseline_bytes=baseline,
        current_bytes=current,
    ) == []


def test_avera_v0_verifier_detects_envelope_tamper_without_reinterpreting_verdict():
    envelope, _, _ = _fixture()
    tampered = copy.deepcopy(envelope)
    tampered["result"]["verdict"] = "passed"

    failures = verify_avera_check_v0(tampered)

    assert any("digest mismatch" in failure for failure in failures)
    assert envelope["result"]["verdict"] == "confirmed_regression"


def test_avera_v0_verifier_detects_input_byte_drift():
    envelope, baseline, current = _fixture()

    failures = verify_avera_check_v0(
        envelope,
        baseline_bytes=baseline + b"\n",
        current_bytes=current,
    )

    assert failures == [
        "baseline JUnit bytes do not match inputs.baseline_sha256"
    ]


def test_avera_v0_verifier_rejects_schema_or_producer_drift():
    envelope, _, _ = _fixture()
    drifted = copy.deepcopy(envelope)
    drifted["schema_version"] = "avera.check/v1"
    drifted["tool"]["name"] = "not-avera"

    failures = verify_avera_check_v0(drifted)

    assert "schema_version must be 'avera.check/v0'" in failures
    assert "tool.name must be 'avera'" in failures
    assert any("digest mismatch" in failure for failure in failures)


def test_avera_v0_fixture_does_not_claim_source_candidate_identity():
    envelope, _, _ = _fixture()

    assert set(envelope["inputs"]) == {"baseline_sha256", "current_sha256"}
    assert "candidate" not in envelope
    assert "head_sha" not in envelope
    assert "base_sha" not in envelope
