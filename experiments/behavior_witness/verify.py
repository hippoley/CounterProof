#!/usr/bin/env python3
"""Minimal deterministic verifier for the black-box behavior witness experiment."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def compare(mode: str, expected: Any, actual: Any) -> bool | None:
    if mode == "exact-json":
        return expected == actual
    if mode == "exact-text":
        if not isinstance(expected, str) or not isinstance(actual, str):
            return None
        return expected == actual
    if mode == "casefold-text":
        if not isinstance(expected, str) or not isinstance(actual, str):
            return None
        return expected.casefold() == actual.casefold()
    return None


def verify(contract: dict[str, Any], candidate: dict[str, Any]) -> tuple[str, str]:
    try:
        mode = contract["comparator"]["mode"]
        expected = contract["reference_observation"]["output"]
        actual = candidate["observation"]["output"]
        expected_probe = contract["probe"]["id"]
        actual_probe = candidate["probe_id"]
    except (KeyError, TypeError):
        return "UNKNOWN", "required contract or observation field is missing"

    if expected_probe != actual_probe:
        return "UNKNOWN", f"probe mismatch: expected {expected_probe!r}, got {actual_probe!r}"

    result = compare(mode, expected, actual)
    if result is None:
        return "UNKNOWN", f"unsupported or ill-typed comparator: {mode!r}"
    if result:
        return "PASS", f"candidate matches frozen reference under {mode}"
    return "FAIL", f"candidate differs from frozen reference under {mode}"


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: verify.py CONTRACT.json CANDIDATE.json", file=sys.stderr)
        return 2

    try:
        contract = load(argv[1])
        candidate = load(argv[2])
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"UNKNOWN: {exc}")
        return 2

    verdict, reason = verify(contract, candidate)
    print(f"{verdict}: {reason}")
    return {"PASS": 0, "FAIL": 1, "UNKNOWN": 2}[verdict]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
