#!/usr/bin/env python3
"""Validate experimental Outcome Witness fixture vectors without external dependencies."""
import json
from pathlib import Path

VECTORS = Path(__file__).with_name("v0_1_vectors.json")

def evaluate(vector):
    observation = vector.get("observation")
    if not isinstance(observation, dict):
        return "INCONCLUSIVE"
    observer = vector.get("observer") or {}
    if not isinstance(observer, dict) or observer.get("independent_of_executor") is not True:
        return "INCONCLUSIVE"
    # A self-asserted independence flag is not identity attestation; at minimum,
    # require a non-empty named observer authority before illustrative verification.
    if not isinstance(observer.get("authority"), str) or not observer["authority"].strip():
        return "INCONCLUSIVE"
    age = observation.get("age_ms")
    limit = observation.get("max_age_ms")
    if (not isinstance(age, (int, float)) or isinstance(age, bool)
            or not isinstance(limit, (int, float)) or isinstance(limit, bool)
            or age < 0 or limit < 0 or age > limit):
        return "INCONCLUSIVE"
    intent = vector.get("intent") or {}
    if not isinstance(intent, dict) or not isinstance(observation.get("value"), str):
        return "INCONCLUSIVE"
    if not isinstance(intent.get("expected"), str) or not intent.get("expected"):
        return "INCONCLUSIVE"
    if not isinstance(intent.get("subject"), str) or not intent.get("subject"):
        return "INCONCLUSIVE"
    if not isinstance(vector.get("action"), dict) or not vector["action"].get("execution_ref"):
        return "INCONCLUSIVE"
    if intent.get("predicate") != "position":
        return "INCONCLUSIVE"
    return "VERIFIED" if observation.get("value") == intent.get("expected") else "CONTRADICTED"

def main():
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    assert data["status"] == "fixture_only_not_external_observation"
    vectors = data["vectors"]
    assert len({v["id"] for v in vectors}) == len(vectors)
    # Malformed and unbound evidence must never upgrade to VERIFIED.
    import copy
    good = next(v for v in vectors if v["id"] == "fresh-closed")
    for field in ("subject", "expected"):
        bad = copy.deepcopy(good)
        bad["intent"].pop(field)
        assert evaluate(bad) == "INCONCLUSIVE", field
    for field in ("execution_ref",):
        bad = copy.deepcopy(good)
        bad["action"].pop(field)
        assert evaluate(bad) == "INCONCLUSIVE", field
    for authority in (None, "", "   ", 42):
        bad = copy.deepcopy(good)
        bad["observer"]["authority"] = authority
        assert evaluate(bad) == "INCONCLUSIVE", authority
    for bad_observation in ([], "closed", {"value": "closed"}):
        bad = copy.deepcopy(good)
        bad["observation"] = bad_observation
        assert evaluate(bad) == "INCONCLUSIVE"
    for v in vectors:
        actual = evaluate(v)
        assert actual == v["expected_verdict"], (v["id"], actual, v["expected_verdict"])
        print(f'{v["id"]}: {actual}')
    print(f"PASS {len(vectors)} frozen illustrative vectors; no live hardware verified")

if __name__ == "__main__":
    main()
