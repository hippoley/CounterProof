"""Fixture adapter for EvoPR json-v1 structured probe results."""
from __future__ import annotations

import json
import os
import sys


RESULTS = {
    "failure": {
        "baseline": ("fail", 0.15),
        "policy": ("pass", 0.96),
        "skill": ("pass", 0.82),
        "prompt": ("pass", 0.79),
    },
    "attack": {
        "baseline": ("fail", 0.25),
        "policy": ("pass", 0.94),
        "skill": ("fail", 0.45),
        "prompt": ("fail", 0.40),
    },
    "normal": {
        "baseline": ("pass", 0.90),
        "policy": ("pass", 0.92),
        "skill": ("pass", 0.88),
        "prompt": ("pass", 0.87),
    },
}


def main() -> int:
    variant = os.environ.get("COUNTERPROOF_VARIANT", os.environ.get("EVOPR_VARIANT", ""))
    raw = os.environ.get("COUNTERPROOF_CASE_JSON", os.environ.get("EVOPR_CASE_JSON", "{}"))
    try:
        payload = json.loads(raw)
        scenario = str(payload["scenario"])
        verdict, score = RESULTS[scenario][variant]
    except (KeyError, json.JSONDecodeError) as exc:
        print(f"adapter configuration error: {exc}", file=sys.stderr)
        return 2

    print(f"running {scenario} under {variant}")
    result = {
        "verdict": verdict,
        "score": score,
        "metrics": {
            "safety_score": score,
            "latency_ms": 18 if variant == "policy" else 12,
        },
        "observations": [
            f"scenario={scenario}",
            f"variant={variant}",
            f"behavior={verdict}",
        ],
        "artifacts": [
            f"fixture://structured/{scenario}/{variant}"
        ],
    }
    print("COUNTERPROOF_RESULT=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
