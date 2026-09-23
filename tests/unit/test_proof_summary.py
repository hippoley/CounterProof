from __future__ import annotations

import json

from click.testing import CliRunner

from skill_factory.evolution.cli import cli
from skill_factory.evolution.proof_summary import (
    build_proof_summary,
    render_proof_summary,
)


def _witness(status: str, mode: str = "precise") -> dict:
    return {
        "status": status,
        "mode": mode,
    }


def _integrity(status: str) -> dict:
    return {
        "status": status,
    }


def test_precise_witness_plus_clean_integrity_is_verified():
    summary = build_proof_summary(
        _witness("witnessed", "precise"),
        _integrity("clean"),
    )

    assert summary.proof_status == "verified"
    assert summary.proof_ready is True
    assert "not a general claim" in render_proof_summary(summary)


def test_changed_judge_overrides_positive_witness():
    summary = build_proof_summary(
        _witness("witnessed", "precise"),
        _integrity("review-required"),
    )

    assert summary.proof_status == "review-required"
    assert summary.proof_ready is False


def test_suite_delta_never_becomes_proof_ready():
    summary = build_proof_summary(
        _witness("suite-delta", "suite"),
        _integrity("clean"),
    )

    assert summary.proof_status == "suite-delta"
    assert summary.proof_ready is False


def test_inconsistent_witnessed_suite_mode_is_inconclusive():
    summary = build_proof_summary(
        _witness("witnessed", "suite"),
        _integrity("clean"),
    )

    assert summary.proof_status == "inconclusive"
    assert summary.proof_ready is False


def test_unknown_integrity_blocks_verified_status():
    summary = build_proof_summary(
        _witness("witnessed", "precise"),
        _integrity("unknown"),
    )

    assert summary.proof_status == "integrity-unknown"
    assert summary.proof_ready is False


def test_proof_summary_cli_writes_machine_contract(tmp_path):
    witness = tmp_path / "witness.json"
    integrity = tmp_path / "integrity.json"
    output = tmp_path / "summary.json"
    markdown = tmp_path / "summary.md"

    witness.write_text(
        json.dumps(_witness("witnessed", "precise")),
        encoding="utf-8",
    )
    integrity.write_text(
        json.dumps(_integrity("clean")),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        [
            "proof-summary",
            "--witness-json",
            str(witness),
            "--integrity-json",
            str(integrity),
            "--out",
            str(output),
            "--markdown-out",
            str(markdown),
            "--require-proof-ready",
        ],
    )

    assert result.exit_code == 0, result.output
    raw = json.loads(output.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1
    assert raw["proof_status"] == "verified"
    assert raw["proof_ready"] is True
    assert markdown.exists()


def test_proof_summary_cli_gate_rejects_non_verified(tmp_path):
    witness = tmp_path / "witness.json"
    integrity = tmp_path / "integrity.json"

    witness.write_text(
        json.dumps(_witness("suite-delta", "suite")),
        encoding="utf-8",
    )
    integrity.write_text(
        json.dumps(_integrity("clean")),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        [
            "proof-summary",
            "--witness-json",
            str(witness),
            "--integrity-json",
            str(integrity),
            "--out",
            str(tmp_path / "summary.json"),
            "--markdown-out",
            str(tmp_path / "summary.md"),
            "--require-proof-ready",
        ],
    )

    assert result.exit_code != 0
    assert "proof-ready required, got status=suite-delta" in result.output
