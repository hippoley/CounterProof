#!/usr/bin/env python3
"""Validate experimental Outcome Witness fixture vectors without external dependencies."""
import json
from pathlib import Path

VECTORS = Path(__file__).with_name("v0_1_vectors.json")

def evaluate(vector):
    observation = vector.get("observation")
    if observation is None:
        return "INCONCLUSIVE"
    observer = vector.get("observer") or {}
    if observer.get("independent_of_executor") is not True:
        return "INCONCLUSIVE"
    age = observation.get("age_ms")
    limit = observation.get("max_age_ms")
    if (not isinstance(age, (int, float)) or isinstance(age, bool)
            or not isinstance(limit, (int, float)) or isinstance(limit, bool)
            or age < 0 or limit < 0 or age > limit):
        return "INCONCLUSIVE"
    intent = vector["intent"]
    if intent.get("predicate") != "position":
        return "INCONCLUSIVE"
    return "VERIFIED" if observation.get("value") == intent.get("expected") else "CONTRADICTED"

def main():
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    assert data["status"] == "fixture_only_not_external_observation"
    vectors = data["vectors"]
    assert len({v["id"] for v in vectors}) == len(vectors)
    for v in vectors:
        actual = evaluate(v)
        assert actual == v["expected_verdict"], (v["id"], actual, v["expected_verdict"])
        print(f'{v["id"]}: {actual}')
    print(f"PASS {len(vectors)} frozen illustrative vectors; no live hardware verified")

if __name__ == "__main__":
    main()
