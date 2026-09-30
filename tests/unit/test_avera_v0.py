from __future__ import annotations

import copy

import pytest

from skill_factory.evolution.avera_v0 import (
    AVERA_CHECK_V0,
    canonical_json_bytes,
    envelope_digest,
    load_avera_check_v0,
)


def _payload() -> dict:
    payload = {
        "schema_version": AVERA_CHECK_V0,
        "tool": {"name": "avera", "version": "0.1.0"},
        "policy": "general",
        "inputs": {
            "baseline_sha256": "a" * 64,
            "current_sha256": "b" * 64,
        },
        "result": {
            "verdict": "confirmed_regression",
            "gate_status": "block",
            "introduced_failures": ["pkg.tests.test_thing"],
            "risk": "high",
            "confidence": "deterministic",
            "confidence_score": 1.0,
        },
    }
    payload["digest"] = envelope_digest(payload)
    return payload


def test_proposed_avera_v0_is_sufficiently_parseable_as_external_evidence():
    envelope = load_avera_check_v0(_payload())

    assert envelope.schema_version == "avera.check/v0"
    assert envelope.tool.name == "avera"
    assert envelope.result.introduced_failures == ["pkg.tests.test_thing"]


def test_digest_is_invariant_to_object_key_order():
    payload = _payload()
    without_digest = {k: v for k, v in reversed(list(payload.items())) if k != "digest"}

    assert envelope_digest(without_digest) == payload["digest"]


def test_digest_changes_when_evidence_changes():
    payload = _payload()
    mutated = copy.deepcopy(payload)
    mutated["result"]["introduced_failures"].append("pkg.tests.test_other")

    with pytest.raises(ValueError, match="digest mismatch"):
        load_avera_check_v0(mutated)


def test_input_hashes_are_required_and_exact_sha256_hex():
    payload = _payload()
    payload["inputs"]["baseline_sha256"] = "not-a-sha"

    with pytest.raises(ValueError, match="invalid AVERA v0 evidence envelope"):
        load_avera_check_v0(payload)


def test_schema_version_is_namespaced_string_for_simple_dispatch():
    payload = _payload()
    payload["schema_version"] = "v0"
    unsigned = {k: v for k, v in payload.items() if k != "digest"}
    payload["digest"] = envelope_digest(unsigned)

    with pytest.raises(ValueError, match="unsupported AVERA schema_version"):
        load_avera_check_v0(payload)


def test_canonicalization_is_utf8_sorted_compact_and_rejects_nan():
    left = {"z": "é", "a": {"b": 2, "a": 1}}
    right = {"a": {"a": 1, "b": 2}, "z": "é"}

    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert canonical_json_bytes(left) == '{"a":{"a":1,"b":2},"z":"é"}'.encode()

    with pytest.raises(ValueError):
        canonical_json_bytes({"score": float("nan")})


def test_valid_envelope_does_not_claim_counterproof_candidate_provenance():
    envelope = load_avera_check_v0(_payload())

    # The AVERA envelope binds the two JUnit byte streams and the AVERA result.
    # Commit/PR identity belongs to the consuming review claim, not this envelope.
    assert not hasattr(envelope, "base_sha")
    assert not hasattr(envelope, "head_sha")
