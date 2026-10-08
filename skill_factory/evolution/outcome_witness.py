"""Validation for experimental CounterProof Outcome Witness v0.1.

The validator intentionally owns only format and freshness admission. It does not
interpret arbitrary domain oracle expressions or claim that an observer is
authoritative merely because the witness says so.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "outcome-witness-v0.1.schema.json"


class OutcomeWitnessError(ValueError):
    """Raised when an Outcome Witness cannot be admitted."""


def _parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OutcomeWitnessError(f"invalid observed_at: {value}") from exc
    if parsed.tzinfo is None:
        raise OutcomeWitnessError("observed_at must include a timezone")
    return parsed.astimezone(timezone.utc)


def load_outcome_witness(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_outcome_witness(payload)
    return payload


def validate_outcome_witness(
    payload: dict[str, Any],
    *,
    now: datetime | None = None,
    expected_action_ref: dict[str, str] | None = None,
) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.Draft202012Validator(schema).validate(payload)
    except jsonschema.ValidationError as exc:
        where = ".".join(str(item) for item in exc.absolute_path)
        prefix = f"{where}: " if where else ""
        raise OutcomeWitnessError(f"{prefix}{exc.message}") from exc

    if expected_action_ref is not None:
        observed_ref = payload["action_ref"]
        expected_type = expected_action_ref.get("type")
        expected_id = expected_action_ref.get("id")
        if observed_ref.get("type") != expected_type or observed_ref.get("id") != expected_id:
            raise OutcomeWitnessError(
                "action_ref does not match the action being evaluated"
            )

    observed_at = _parse_utc(payload["observed_at"])
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise OutcomeWitnessError("validation time must include a timezone")
    current = current.astimezone(timezone.utc)

    age_ms = max(0.0, (current - observed_at).total_seconds() * 1000)
    if age_ms > payload["max_age_ms"] and payload["verdict"] != "INCONCLUSIVE":
        raise OutcomeWitnessError(
            "stale observation cannot support VERIFIED or CONTRADICTED; "
            "use INCONCLUSIVE or obtain a fresh observation"
        )
