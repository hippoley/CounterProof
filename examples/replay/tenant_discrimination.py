"""Deterministic fixture for active causal discrimination."""
from __future__ import annotations

import sys


PASS_MATRIX = {
    "baseline": {"normal-lookup-12"},
    "policy": {
        "failure-418",
        "cross-tenant-attack-07",
        "normal-lookup-12",
    },
    "skill": {
        "failure-418",
        "normal-lookup-12",
    },
    "prompt": {
        "failure-418",
        "normal-lookup-12",
    },
}


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: tenant_discrimination.py "
            "baseline|policy|skill|prompt CASE_ID",
            file=sys.stderr,
        )
        return 2

    variant, case_id = sys.argv[1], sys.argv[2]
    if variant not in PASS_MATRIX:
        print(f"unknown variant: {variant}", file=sys.stderr)
        return 2

    ok = case_id in PASS_MATRIX[variant]
    print(f"{variant}:{case_id}:{'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
