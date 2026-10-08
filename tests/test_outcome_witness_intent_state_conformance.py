import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
BRIDGE = ROOT / "experiments" / "outcome-witness-intent-state-conformance" / "bridge.py"
FIXTURES = BRIDGE.parent / "fixtures"

spec = importlib.util.spec_from_file_location("outcome_witness_conformance_bridge", BRIDGE)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def load(name):
    return json.loads((FIXTURES / name).read_text())


def test_verified_authorized_effect_passes():
    out = bridge.evaluate(load("window-verified.json"), load("window-policy.json"))
    assert out["verdict"] == "PASS"
    assert out["reason"] == "verified_effect_within_authorized_contract"


def test_contradicted_effect_fails():
    out = bridge.evaluate(load("window-contradicted.json"), load("window-policy.json"))
    assert out["verdict"] == "FAIL"


def test_inconclusive_never_upgrades_to_pass():
    witness = load("window-verified.json")
    witness["verdict"] = "INCONCLUSIVE"
    witness["observation"] = {}
    out = bridge.evaluate(witness, load("window-policy.json"))
    assert out["verdict"] == "INDETERMINATE"


def test_verified_but_unauthorized_effect_fails():
    policy = {"authorized_effects": {}}
    out = bridge.evaluate(load("window-verified.json"), policy)
    assert out["verdict"] == "FAIL"
    assert out["reason"] == "effect_not_authorized"
