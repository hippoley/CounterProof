import json

import pytest

from skill_factory.evolution.external_execution_receipt import (
    admit_external_execution_receipt,
)


def _write_inputs(tmp_path, *, receipt_updates=None, provenance_updates=None):
    receipt = {
        "schema_version": 2,
        "disposition": "reexecuted",
        "producer": "agent-done-or-not@0.13.1",
        "repo": "hippoley/CounterProof",
        "commit": "1" * 40,
        "tree": "2" * 40,
        "dirty": False,
        "label": "counterproof-tests",
        "command": "pytest -q",
        "exit_code": 0,
        "sha256": "3" * 64,
        "verifier": {"kind": "external"},
        "ci": {"run_id": 123},
        "ref": "refs/heads/main",
    }
    provenance = {
        "producer": {
            "repository": "mohamedzhioua/agent-done-or-not",
            "tag": "v0.13.1",
            "resolved_commit": "4" * 40,
            "done_gate_sha256": "5" * 64,
        }
    }
    receipt.update(receipt_updates or {})
    provenance.update(provenance_updates or {})
    receipt_path = tmp_path / "receipt.json"
    provenance_path = tmp_path / "provenance.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    return receipt_path, provenance_path


def test_external_execution_receipt_is_admitted_only_as_bounded_input(tmp_path):
    receipt_path, provenance_path = _write_inputs(tmp_path)

    admitted = admit_external_execution_receipt(receipt_path, provenance_path)

    assert admitted["receipt_type"] == "EXTERNAL_EXECUTION_EVIDENCE_INPUT"
    assert admitted["admission"] == "BOUND_EXECUTION_INPUT"
    assert admitted["producer"]["identity"] == "agent-done-or-not@0.13.1"
    assert admitted["candidate"] == {
        "repository": "hippoley/CounterProof",
        "commit": "1" * 40,
        "tree": "2" * 40,
        "dirty": False,
    }
    assert admitted["execution"]["exit_code"] == 0
    assert "does not establish that the candidate is correct" in admitted["semantic_boundary"]


@pytest.mark.parametrize(
    ("updates", "error"),
    [
        ({"schema_version": 1}, "schema_version 2"),
        ({"disposition": "cached"}, "disposition=reexecuted"),
        ({"dirty": True}, "clean captured candidate"),
        ({"commit": "short"}, "full git SHA"),
        ({"sha256": "bad"}, "64 lowercase hex"),
    ],
)
def test_external_execution_receipt_fails_closed_on_unbound_or_weak_inputs(
    tmp_path, updates, error
):
    receipt_path, provenance_path = _write_inputs(tmp_path, receipt_updates=updates)

    with pytest.raises((ValueError, TypeError), match=error):
        admit_external_execution_receipt(receipt_path, provenance_path)


def test_external_execution_receipt_rejects_producer_tag_mismatch(tmp_path):
    receipt_path, provenance_path = _write_inputs(
        tmp_path,
        receipt_updates={"producer": "agent-done-or-not@0.13.0"},
    )

    with pytest.raises(ValueError, match="does not match frozen tag"):
        admit_external_execution_receipt(receipt_path, provenance_path)


def test_real_agent_done_receipt_remains_admissible_as_bounded_input():
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    fixture = root / "examples" / "interop" / "agent-done-v2-real"

    admitted = admit_external_execution_receipt(
        fixture / "receipt.json",
        fixture / "provenance.json",
    )

    assert admitted["admission"] == "BOUND_EXECUTION_INPUT"
    assert admitted["producer"]["tag"] == "v0.13.1"
    assert admitted["producer"]["resolved_commit"] == (
        "4a801bf056519af5a845e773260ef23796eea3ff"
    )
    assert admitted["candidate"]["repository"] == "hippoley/CounterProof"
    assert admitted["execution"]["exit_code"] == 0
    assert "does not establish that the candidate is correct" in admitted["semantic_boundary"]
