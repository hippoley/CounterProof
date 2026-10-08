#!/usr/bin/env python3
"""Experimental independent-consumer CLI for frozen Outcome Witness JSON.

No trust or observer authentication is performed. Not a production trust gate.
"""
import argparse
import json
import sys
from pathlib import Path

from check_vectors import evaluate


def consume(payload):
    if not isinstance(payload, dict):
        raise ValueError("expected JSON object")
    if payload.get("version") != "0.1-experimental":
        raise ValueError("unsupported contract version")
    if payload.get("status") != "fixture_only_not_external_observation":
        raise ValueError("untrusted fixture-only consumer refuses live attestation claims")
    vectors = payload.get("vectors")
    if not isinstance(vectors, list) or not vectors:
        raise ValueError("expected nonempty vectors array")
    if any(not isinstance(v, dict) for v in vectors):
        raise ValueError("every vector must be an object")
    ids = [v.get("id") for v in vectors]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("vector ids must be nonempty and unique")
    return [{"id": v["id"], "verdict": evaluate(v)} for v in vectors]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="fixture-only JSON envelope")
    parser.add_argument("--output", type=Path, help="optional result JSON output")
    args = parser.parse_args()
    try:
        result = {"version": "0.1-experimental", "trust_profile": "fixture_only",
                  "results": consume(json.loads(args.input.read_text(encoding="utf-8")))}
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    else:
        sys.stdout.write(serialized)


if __name__ == "__main__":
    main()
