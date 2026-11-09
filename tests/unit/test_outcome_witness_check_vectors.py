import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "examples/outcome_witness/check_vectors.py"
FIXTURE = ROOT / "examples/outcome_witness/v0_1_vectors.json"
SPEC = importlib.util.spec_from_file_location("outcome_witness_check_vectors", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _good_vector():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return next(v for v in data["vectors"] if v["id"] == "fresh-closed")


def test_nonfinite_and_negative_freshness_never_verifies():
    for field in ("age_ms", "max_age_ms"):
        for value in (float("nan"), float("inf"), float("-inf"), -1, True):
            vector = _good_vector()
            vector["observation"][field] = value
            assert MODULE.evaluate(vector) == "INCONCLUSIVE", (field, value)


def test_malformed_execution_reference_never_verifies():
    for value in (None, "", "   ", 123, [], {}):
        vector = _good_vector()
        vector["action"]["execution_ref"] = value
        assert MODULE.evaluate(vector) == "INCONCLUSIVE", value


def test_non_object_vector_never_verifies():
    for vector in (None, [], "fresh-closed", 42):
        assert MODULE.evaluate(vector) == "INCONCLUSIVE", vector


def test_all_frozen_vectors_keep_their_declared_verdicts():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for vector in data["vectors"]:
        assert MODULE.evaluate(vector) == vector["expected_verdict"], vector["id"]
