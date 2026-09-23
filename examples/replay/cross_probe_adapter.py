"""Fixture-only adapter for generated crossed diagnostic probes.

This adapter validates EvoPR plumbing, not target-domain semantics. It treats the
payload's focus_surface as the only intervention expected to pass.
"""
from __future__ import annotations

import json
import os
import sys


def main() -> int:
    variant = os.environ.get("EVOPR_VARIANT", "")
    payload_raw = os.environ.get("EVOPR_CASE_JSON", "{}")
    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if variant == "baseline":
        print("baseline: diagnostic fixture remains failing")
        return 1

    focus_surface = str(payload.get("focus_surface", ""))
    if not focus_surface:
        print("missing focus_surface", file=sys.stderr)
        return 2

    ok = variant == focus_surface
    print(
        json.dumps(
            {
                "variant": variant,
                "focus_surface": focus_surface,
                "design": payload.get("design"),
                "verdict": "PASS" if ok else "FAIL",
                "fixture_only": True,
            }
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
