"""Example EvoPR probe adapter driven by environment variables."""
from __future__ import annotations

import json
import os
import sys


def evaluate(variant: str, payload: dict[str, object]) -> bool:
    normal = bool(payload.get("normal"))
    attack = bool(payload.get("attack"))

    if variant == "baseline":
        return normal
    if variant == "policy":
        return True
    if variant in {"skill", "prompt"}:
        return normal or not attack
    raise ValueError(f"unknown variant: {variant}")


def main() -> int:
    variant = os.environ.get("COUNTERPROOF_VARIANT", os.environ.get("EVOPR_VARIANT", ""))
    case_id = os.environ.get("COUNTERPROOF_CASE_ID", os.environ.get("EVOPR_CASE_ID", ""))
    payload_raw = os.environ.get("COUNTERPROOF_CASE_JSON", os.environ.get("EVOPR_CASE_JSON", "{}"))
    try:
        payload = json.loads(payload_raw)
        ok = evaluate(variant, payload)
    except (ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "case_id": case_id,
                "variant": variant,
                "payload": payload,
                "verdict": "PASS" if ok else "FAIL",
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
