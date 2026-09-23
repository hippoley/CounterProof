from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

from skill_factory.evolution.cli import cli
from skill_factory.evolution.witness import (
    changed_test_files,
    render_witness_markdown,
    run_regression_witness,
    witness_to_dict,
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


def _init_repo(path: Path, *, base_value: int) -> str:
    path.mkdir()
    _git(path, "init")
    _git(path, "config", "user.email", "counterproof@example.test")
    _git(path, "config", "user.name", "Counterproof Test")
    (path / "app.py").write_text(f"VALUE = {base_value}\n", encoding="utf-8")
    _git(path, "add", ".")
    _git(path, "commit", "-m", "base")
    return _git(path, "rev-parse", "HEAD")


def _add_head_test(repo: Path, *, head_value: int, expected: int) -> None:
    (repo / "app.py").write_text(f"VALUE = {head_value}\n", encoding="utf-8")
    tests = repo / "tests"
    tests.mkdir(exist_ok=True)
    (tests / "test_regression.py").write_text(
        "from app import VALUE\n\n"
        "def test_regression():\n"
        f"    assert VALUE == {expected}\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "agent fix plus regression test")


def _pytest_command() -> str:
    return f"{sys.executable} -m pytest -q {{tests}}"


def test_changed_test_files_detects_pr_tests(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo, base_value=1)
    _add_head_test(repo, head_value=2, expected=2)

    files = changed_test_files(repo, base_ref=base)

    assert files == ("tests/test_regression.py",)


def test_regression_witness_proves_test_fails_before_fix_and_passes_after(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo, base_value=1)
    _add_head_test(repo, head_value=2, expected=2)

    witness = run_regression_witness(
        repo,
        base_ref=base,
        test_command=_pytest_command(),
        timeout_seconds=30,
    )

    assert witness.status == "witnessed"
    assert witness.witnessed is True
    assert witness.head is not None and witness.head.returncode == 0
    assert witness.base_with_head_tests is not None
    assert witness.base_with_head_tests.returncode != 0
    assert "same changed tests fail before the fix" in render_witness_markdown(
        witness
    ).lower()

    payload = witness_to_dict(witness)
    assert payload["witnessed"] is True
    assert payload["tests"] == ["tests/test_regression.py"]


def test_regression_witness_refuses_test_that_already_passed_on_base(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo, base_value=2)
    _add_head_test(repo, head_value=2, expected=2)

    witness = run_regression_witness(
        repo,
        base_ref=base,
        test_command=_pytest_command(),
        timeout_seconds=30,
    )

    assert witness.status == "not-witnessed"
    assert witness.witnessed is False
    assert witness.head is not None and witness.head.returncode == 0
    assert witness.base_with_head_tests is not None
    assert witness.base_with_head_tests.returncode == 0


def test_regression_witness_refuses_head_failing_test(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo, base_value=1)
    _add_head_test(repo, head_value=1, expected=2)

    witness = run_regression_witness(
        repo,
        base_ref=base,
        test_command=_pytest_command(),
        timeout_seconds=30,
    )

    assert witness.status == "head-failing"
    assert witness.witnessed is False
    assert witness.head is not None and witness.head.returncode != 0
    assert witness.base_with_head_tests is None


def test_counterproof_witness_cli_can_gate_on_real_regression(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo, base_value=1)
    _add_head_test(repo, head_value=2, expected=2)
    report = tmp_path / "witness.md"
    payload = tmp_path / "witness.json"

    result = CliRunner().invoke(
        cli,
        [
            "witness",
            "--repo",
            str(repo),
            "--base",
            base,
            "--test-command",
            _pytest_command(),
            "--out",
            str(report),
            "--json-out",
            str(payload),
            "--require-witness",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Regression witness: witnessed" in result.output
    assert report.exists()
    raw = json.loads(payload.read_text(encoding="utf-8"))
    assert raw["status"] == "witnessed"
    assert raw["head"]["returncode"] == 0
    assert raw["base_with_head_tests"]["returncode"] != 0
