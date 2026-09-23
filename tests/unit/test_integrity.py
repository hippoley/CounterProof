from __future__ import annotations

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from skill_factory.evolution.cli import cli
from skill_factory.evolution.integrity import (
    inspect_proof_integrity,
    integrity_to_dict,
    render_integrity_markdown,
)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _init_repo(path: Path) -> str:
    path.mkdir()
    _git(path, "init")
    _git(path, "config", "user.email", "counterproof@example.test")
    _git(path, "config", "user.name", "Counterproof Test")
    (path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    tests = path / "tests"
    tests.mkdir()
    (tests / "test_value.py").write_text(
        "from app import VALUE\n\n"
        "def test_value():\n"
        "    assert VALUE == 1\n",
        encoding="utf-8",
    )
    workflows = path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "name: CI\n"
        "on:\n"
        "  pull_request:\n"
        "  push:\n"
        "jobs:\n"
        "  test:\n"
        "    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )
    _git(path, "add", ".")
    _git(path, "commit", "-m", "base")
    return _git(path, "rev-parse", "HEAD")


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


def test_integrity_clean_for_code_only_change(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    _commit(repo, "code only")

    report = inspect_proof_integrity(repo, base_ref=base)

    assert report.status == "clean"
    assert report.findings == ()
    assert report.high_risk_count == 0
    assert "No deterministic evidence-integrity risks" in render_integrity_markdown(
        report
    )


def test_integrity_flags_deleted_test(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    (repo / "tests" / "test_value.py").unlink()
    _commit(repo, "delete test")

    report = inspect_proof_integrity(repo, base_ref=base)
    codes = {item.code for item in report.findings}

    assert report.status == "review-required"
    assert "test-deleted" in codes
    assert report.high_risk_count >= 1


def test_integrity_flags_added_skip_marker(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    (repo / "tests" / "test_value.py").write_text(
        "import pytest\n"
        "from app import VALUE\n\n"
        "@pytest.mark.skip(reason='agent shortcut')\n"
        "def test_value():\n"
        "    assert VALUE == 1\n",
        encoding="utf-8",
    )
    _commit(repo, "skip test")

    report = inspect_proof_integrity(repo, base_ref=base)
    codes = {item.code for item in report.findings}

    assert "pytest-skip" in codes
    assert report.high_risk_count >= 1


def test_integrity_flags_ci_weakening(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    workflow = repo / ".github" / "workflows" / "ci.yml"
    workflow.write_text(
        "name: CI\n"
        "on:\n"
        "  push:\n"
        "jobs:\n"
        "  test:\n"
        "    runs-on: ubuntu-latest\n"
        "    continue-on-error: true\n"
        "    steps:\n"
        "      - run: pytest || true\n",
        encoding="utf-8",
    )
    _commit(repo, "weaken CI")

    report = inspect_proof_integrity(repo, base_ref=base)
    codes = {item.code for item in report.findings}

    assert "evidence-config-changed" in codes
    assert "pull-request-trigger-removed" in codes
    assert "continue-on-error" in codes
    assert "shell-ignore-failure" in codes
    assert report.high_risk_count >= 3


def test_integrity_cli_can_gate_review_required(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    (repo / "tests" / "test_value.py").unlink()
    _commit(repo, "delete test")
    report_path = tmp_path / "integrity.md"
    json_path = tmp_path / "integrity.json"

    result = CliRunner().invoke(
        cli,
        [
            "integrity",
            "--repo",
            str(repo),
            "--base",
            base,
            "--out",
            str(report_path),
            "--json-out",
            str(json_path),
            "--require-clean",
        ],
    )

    assert result.exit_code != 0
    assert "proof integrity review required" in result.output
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    assert raw["status"] == "review-required"
    assert raw["high_risk_count"] >= 1
    assert any(item["code"] == "test-deleted" for item in raw["findings"])


def test_integrity_payload_is_machine_readable(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    _commit(repo, "code only")

    payload = integrity_to_dict(inspect_proof_integrity(repo, base_ref=base))

    assert payload["schema_version"] == 1
    assert payload["status"] == "clean"
    assert payload["findings"] == []
