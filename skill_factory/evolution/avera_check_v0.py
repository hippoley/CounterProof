"""Experimental consumer for AVERA's `avera.check/v0` evidence envelope.

This module validates the transport/evidence boundary agreed with AVERA:
- exact v0 schema and producer identity;
- AVERA's documented digest rule;
- optional JUnit input-byte hashes.

It deliberately does not translate AVERA verdicts into CounterProof claim status and
does not treat JUnit report hashes as source-candidate identity.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

AVERA_CHECK_V0_SCHEMA = "avera.check/v0"
AVERA_TOOL_NAME = "avera"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def avera_check_v0_digest(envelope: dict[str, Any]) -> str:
    """Recompute the v0 digest exactly as documented by AVERA."""
    payload = {key: value for key, value in envelope.items() if key != "digest"}
    text = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def verify_avera_check_v0(
    envelope: dict[str, Any],
    *,
    baseline_bytes: bytes | None = None,
    current_bytes: bytes | None = None,
) -> list[str]:
    """Validate one experimental AVERA envelope without reinterpreting its verdict."""
    failures: list[str] = []

    if envelope.get("schema_version") != AVERA_CHECK_V0_SCHEMA:
        failures.append(
            f"schema_version must be {AVERA_CHECK_V0_SCHEMA!r}"
        )

    tool = envelope.get("tool")
    if not isinstance(tool, dict):
        failures.append("tool must be an object")
    else:
        if tool.get("name") != AVERA_TOOL_NAME:
            failures.append(f"tool.name must be {AVERA_TOOL_NAME!r}")
        version = tool.get("version")
        if not isinstance(version, str) or not version:
            failures.append("tool.version must be a non-empty string")

    policy = envelope.get("policy")
    if not isinstance(policy, str) or not policy:
        failures.append("policy must be a non-empty string")

    inputs = envelope.get("inputs")
    expected_baseline: str | None = None
    expected_current: str | None = None
    if not isinstance(inputs, dict):
        failures.append("inputs must be an object")
    else:
        expected_baseline = inputs.get("baseline_sha256")
        expected_current = inputs.get("current_sha256")
        if not isinstance(expected_baseline, str) or not _SHA256_RE.fullmatch(
            expected_baseline
        ):
            failures.append("inputs.baseline_sha256 must be lowercase SHA-256 hex")
        if not isinstance(expected_current, str) or not _SHA256_RE.fullmatch(
            expected_current
        ):
            failures.append("inputs.current_sha256 must be lowercase SHA-256 hex")

    result = envelope.get("result")
    if not isinstance(result, dict):
        failures.append("result must be an object")
    else:
        verdict = result.get("verdict")
        if not isinstance(verdict, str) or not verdict:
            failures.append("result.verdict must be a non-empty AVERA verdict string")

        gate_status = result.get("gate_status")
        if not isinstance(gate_status, str) or not gate_status:
            failures.append("result.gate_status must be a non-empty string")

        introduced_failures = result.get("introduced_failures")
        if (
            not isinstance(introduced_failures, list)
            or any(
                not isinstance(item, str) or not item
                for item in introduced_failures
            )
        ):
            failures.append(
                "result.introduced_failures must be a list of non-empty strings"
            )

        risk = result.get("risk")
        if not isinstance(risk, str) or not risk:
            failures.append("result.risk must be a non-empty string")

        confidence = result.get("confidence")
        if not isinstance(confidence, str) or not confidence:
            failures.append("result.confidence must be a non-empty string")

        confidence_score = result.get("confidence_score")
        if (
            isinstance(confidence_score, bool)
            or not isinstance(confidence_score, (int, float))
        ):
            failures.append("result.confidence_score must be a JSON number")

    expected_digest = envelope.get("digest")
    if not isinstance(expected_digest, str) or not _SHA256_RE.fullmatch(
        expected_digest
    ):
        failures.append("digest must be lowercase SHA-256 hex")
    else:
        try:
            actual_digest = avera_check_v0_digest(envelope)
        except (TypeError, ValueError):
            failures.append("envelope cannot be serialized with the AVERA v0 digest rule")
        else:
            if actual_digest != expected_digest:
                failures.append(
                    f"digest mismatch: expected {expected_digest}, observed {actual_digest}"
                )

    if baseline_bytes is not None and isinstance(expected_baseline, str):
        observed = _sha256_bytes(baseline_bytes)
        if observed != expected_baseline:
            failures.append(
                "baseline JUnit bytes do not match inputs.baseline_sha256"
            )

    if current_bytes is not None and isinstance(expected_current, str):
        observed = _sha256_bytes(current_bytes)
        if observed != expected_current:
            failures.append(
                "current JUnit bytes do not match inputs.current_sha256"
            )

    return failures
