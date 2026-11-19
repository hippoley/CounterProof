#!/usr/bin/env python3
"""Illustrative evidence-boundary checker; NOT a SCITT or capsule verifier."""
import json
import sys
from pathlib import Path

def classify(record):
    declared_digest = record.get("statement_digest")
    actual_digest = record.get("actual_statement_digest")
    if declared_digest is not None and actual_digest is not None and declared_digest != actual_digest:
        return "REFERENCE_MISMATCH"
    obs = record.get("object_observation")
    if not isinstance(obs, dict) or obs.get("quality") != "measured" or not obs.get("sensor_id"):
        return "UNCHECKABLE"
    declared = record.get("declared_window_position")
    measured = obs.get("position")
    if isinstance(declared, bool) or isinstance(measured, bool) or not isinstance(declared, (int, float)) or not isinstance(measured, (int, float)):
        return "UNCHECKABLE"
    if abs(declared - measured) > 0.01:
        return "INCONSISTENT"
    if record.get("independence_proven") is not True:
        return "INDEPENDENCE_UNPROVEN"
    return "CONSISTENT_LIMITED"

def run(path):
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("expected a list of test cases")
    actual = [{"id": c["id"], "expected": c["expected"], "actual": classify(c)} for c in records]
    ok = all(v["actual"] == v["expected"] for v in actual)
    print(json.dumps({"passed":ok,"cases":actual,"disclaimer":"Illustrative tests only; no physical proof or SCITT conformance"}, indent=2))
    return 0 if ok else 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify.py CASES_JSON")
    raise SystemExit(run(sys.argv[1]))
