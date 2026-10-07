import json
from pathlib import Path

from click.testing import CliRunner

from skill_factory.evolution import cli as cli_module
from skill_factory.evolution.causal_replay import build_causal_replay_receipt


def _write_evidence(path: Path, identity: str, failed: bool, count: int) -> None:
    path.write_text(
        json.dumps(
            {
                "candidate": identity,
                "snapshot": {"failed": failed, "count": count},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_manifest(tmp_path: Path) -> Path:
    _write_evidence(tmp_path / "control.json", "control-sha", False, 0)
    _write_evidence(tmp_path / "bad.json", "bad-sha", True, 3)
    _write_evidence(tmp_path / "revert.json", "revert-sha", False, 0)
    manifest = tmp_path / "causal.yml"
    manifest.write_text(
        """
schema_version: 1
case: example/repo#123
experiment: CONTROL -> BAD -> REVERT
oracle:
  id: runtime-oracle
identity_path: candidate
observation_root: snapshot
candidates:
  CONTROL:
    identity: control-sha
    evidence: control.json
  BAD:
    identity: bad-sha
    evidence: bad.json
  REVERT:
    identity: revert-sha
    evidence: revert.json
expectations:
  - path: failed
    CONTROL: false
    BAD: true
    REVERT: false
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return manifest


def test_causal_replay_cli_writes_receipt_and_summary(tmp_path: Path):
    manifest = _write_manifest(tmp_path)
    receipt_file = tmp_path / "receipt.json"
    summary_file = tmp_path / "summary.md"

    result = CliRunner().invoke(
        cli_module.cli,
        [
            "causal-replay",
            str(manifest),
            "--output",
            str(receipt_file),
            "--summary",
            str(summary_file),
            "--require-witness",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "WITNESSED_CAUSAL_REPLAY" in result.output
    assert receipt_file.exists()
    assert summary_file.exists()


def test_verify_causal_replay_cli_rejects_tamper(tmp_path: Path):
    manifest = _write_manifest(tmp_path)
    receipt_file = tmp_path / "receipt.json"
    receipt = build_causal_replay_receipt(manifest)
    receipt_file.write_text(
        json.dumps(receipt, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_evidence(tmp_path / "bad.json", "bad-sha", False, 0)

    result = CliRunner().invoke(
        cli_module.cli,
        [
            "verify-causal-replay-receipt",
            str(receipt_file),
            "--manifest",
            str(manifest),
        ],
    )

    assert result.exit_code != 0
    assert "candidate BAD evidence identity does not match" in result.output
