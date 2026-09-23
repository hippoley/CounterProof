"""Tiny executable fixture used to prove EvoPR runs real baseline/candidate commands."""
from __future__ import annotations

import sys


def allowed(mode: str, case_id: str) -> bool:
    if mode == "baseline":
        return case_id == "normal-lookup-12"
    if mode == "candidate":
        return case_id in {
            "failure-418",
            "cross-tenant-attack-07",
            "normal-lookup-12",
        }
    raise ValueError(f"unknown mode: {mode}")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: tenant_policy.py baseline|candidate CASE_ID", file=sys.stderr)
        return 2
    mode, case_id = sys.argv[1], sys.argv[2]
    ok = allowed(mode, case_id)
    print(f"{mode}:{case_id}:{'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
