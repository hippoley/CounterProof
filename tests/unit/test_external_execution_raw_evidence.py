import json
from pathlib import Path

import pytest

from skill_factory.evolution.external_execution_receipt import (
    admit_external_execution_receipt,
)

FIXTURE = Path("examples/interop/agent-done-v2-raw-2026-11-09")


def admit(fixture=FIXTURE):
    return admit_external_execution_receipt(
        fixture / "receipt.json",
        fixture / "provenance.json",
        ledger_path=fixture / "ledger.jsonl",
        log_path=fixture / "counterproof-unit.log",
        context_path=fixture / "capture-context.json",
    )


def test_raw_capture_bytes_are_verified_and_merge_preview_is_not_pr_head():
    result = admit()

    assert result["admission"] == "BOUND_EXECUTION_INPUT"
    assert result["candidate"]["commit_role"] == "github_pull_request_merge_preview"
    assert result["candidate"]["commit"] == "5a5b6b988a3c047f6ab6a389fac8aeea09fc039c"
    assert result["pull_request"] == {
        "head_sha": "6cc606816a8e2689292ee91c9b58016a0de41061",
        "base_sha": "7f57d31137540a0f3d40d5a6eeb5dac5d7c19a37",
        "merge_preview_sha": "5a5b6b988a3c047f6ab6a389fac8aeea09fc039c",
    }
    assert result["candidate"]["commit"] not in {
        result["pull_request"]["head_sha"],
        result["pull_request"]["base_sha"],
    }
    assert result["evidence_integrity"]["receipt_matches_final_ledger_line"] is True
    assert result["evidence_integrity"]["producer_output_digest_matches_log_bytes"] is True
    assert result["evidence_limits"]["receipt_kind"] == "capture_execution_not_pr_review"
    assert "unsigned_self_report" in result["evidence_limits"]["authenticity"]
    assert result["execution"]["exit_code"] == 0


def test_raw_capture_rejects_modified_output_log(tmp_path: Path):
    log = tmp_path / "counterproof-unit.log"
    log.write_bytes((FIXTURE / "counterproof-unit.log").read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="does not match preserved log bytes"):
        admit_external_execution_receipt(
            FIXTURE / "receipt.json",
            FIXTURE / "provenance.json",
            ledger_path=FIXTURE / "ledger.jsonl",
            log_path=log,
            context_path=FIXTURE / "capture-context.json",
        )


def test_raw_capture_rejects_receipt_not_equal_to_final_ledger_line(tmp_path: Path):
    receipt = json.loads((FIXTURE / "receipt.json").read_text(encoding="utf-8"))
    receipt["exit_code"] = 1
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="do not match the final producer ledger line"):
        admit_external_execution_receipt(
            receipt_path,
            FIXTURE / "provenance.json",
            ledger_path=FIXTURE / "ledger.jsonl",
            log_path=FIXTURE / "counterproof-unit.log",
            context_path=FIXTURE / "capture-context.json",
        )


def test_raw_capture_rejects_mismatched_github_merge_context(tmp_path: Path):
    context = json.loads((FIXTURE / "capture-context.json").read_text(encoding="utf-8"))
    context["github_sha"] = "0" * 40
    context_path = tmp_path / "capture-context.json"
    context_path.write_text(json.dumps(context), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match producer receipt commit"):
        admit_external_execution_receipt(
            FIXTURE / "receipt.json",
            FIXTURE / "provenance.json",
            ledger_path=FIXTURE / "ledger.jsonl",
            log_path=FIXTURE / "counterproof-unit.log",
            context_path=context_path,
        )
