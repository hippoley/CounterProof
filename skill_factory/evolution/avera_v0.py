"""Experimental consumer contract for AVERA check --json v0 envelopes.

This module is intentionally consumer-side only. It validates the proposed
mikheil-galoian/avera#12 envelope without claiming that the draft is stable or
that CounterProof owns AVERA verdict semantics.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


AVERA_CHECK_V0 = "avera.check/v0"


class _StrictModel(BaseModel):
    """Reject fields outside the experimental v0 envelope contract."""

    model_config = ConfigDict(extra="forbid")


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    """Return the exact v0 digest serialization proposed for interop testing.

    The contract is deliberately explicit: UTF-8, sorted object keys, no
    insignificant whitespace, JSON-native values only, and NaN/Infinity
    rejected. This is a testable proposal, not a security signature.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def envelope_digest(payload_without_digest: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload_without_digest)).hexdigest()


class AveraTool(_StrictModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)


class AveraInputs(_StrictModel):
    baseline_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class AveraResult(_StrictModel):
    verdict: str = Field(min_length=1)
    gate_status: str = Field(min_length=1)
    introduced_failures: list[str]
    risk: str | None = None
    confidence: str | None = None
    confidence_score: float | None = None


class AveraCheckV0Envelope(_StrictModel):
    schema_version: str
    tool: AveraTool
    policy: str = Field(min_length=1)
    inputs: AveraInputs
    result: AveraResult
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_contract(self) -> AveraCheckV0Envelope:
        if self.schema_version != AVERA_CHECK_V0:
            raise ValueError(
                f"unsupported AVERA schema_version: {self.schema_version!r}"
            )
        if self.tool.name != "avera":
            raise ValueError(f"unexpected tool name: {self.tool.name!r}")

        payload = self.model_dump(mode="json")
        expected = payload.pop("digest")
        actual = envelope_digest(payload)
        if actual != expected:
            raise ValueError(
                f"AVERA envelope digest mismatch: expected {expected}, got {actual}"
            )
        return self


def load_avera_check_v0(payload: dict[str, Any]) -> AveraCheckV0Envelope:
    """Validate an experimental AVERA v0 envelope.

    A valid envelope is still ordinary external evidence. It does not become a
    CounterProof WITNESSED claim until a caller binds it to a concrete claim and
    independently establishes candidate/source provenance.
    """
    try:
        return AveraCheckV0Envelope.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"invalid AVERA v0 evidence envelope: {exc}") from exc
