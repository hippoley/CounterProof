from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

from skill_factory.evolution.cli import cli
from skill_factory.evolution.local_check import resolve_base_ref, run_local_check


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


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "counterproof@example.test")
    _git(repo, "config", "user.name", "Counterproof Test")

    (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")

    _git(repo, "checkout", "-b", "feature/fix")
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    tests = repo / "tests"
    tests.mkdir()
    (tests / "test_regression.py").write_text(
        "from app import VALUE\n\n"
        "def test_regression():\n"
        "    assert VALUE == 2\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fix plus regression test")
    return repo


def test_resolve_base_falls_back_to_local_main(tmp_path):
    repo = _repo(tmp_path)

    ref, commit = resolve_base_ref(repo)

    assert ref == "main"
    assert commit == _git(repo, "rev-parse", "main")


def test_local_check_auto_detects_pytest_and_verifies_regression(tmp_path):
    repo = _repo(tmp_path)

    result = run_local_check(
        repo,
        test_command=f"{sys.executable} -m pytest -q {{tests}}",
        timeout_seconds=30,
    )

    assert result.status == "verified"
    assert result.ready is True
    assert result.base_ref == "main"
    assert result.witness.status == "witnessed"
    assert result.integrity.status == "clean"


def test_counterproof_check_cli_is_one_command_local_proof(tmp_path):
    repo = _repo(tmp_path)

    result = CliRunner().invoke(
        cli,
        [
            "check",
            "--repo",
            str(repo),
            "--test-command",
            f"{sys.executable} -m pytest -q {{tests}}",
            "--strict",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Status           VERIFIED" in result.output
    assert "Proof ready      YES" in result.output
    assert "Base             main" in result.output
    assert "Regression       WITNESSED" in result.output


def test_counterproof_check_strict_rejects_weak_test(tmp_path):
    repo = _repo(tmp_path)
    # Rewrite the test so it already passes on base.
    (repo / "tests" / "test_regression.py").write_text(
        "def test_regression():\n"
        "    assert True\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "weaken regression test")

    result = CliRunner().invoke(
        cli,
        [
            "check",
            "--repo",
            str(repo),
            "--test-command",
            f"{sys.executable} -m pytest -q {{tests}}",
            "--strict",
        ],
    )

    assert result.exit_code != 0
    assert "Counterproof strict check failed" in result.output
