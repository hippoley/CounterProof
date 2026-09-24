from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

from skill_factory.evolution.cli import cli
from skill_factory.evolution.witness import (
    changed_test_files,
    changed_test_support_files,
    render_witness_markdown,
    render_witness_review_note,
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


def test_witness_command_without_placeholder_runs_verbatim(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo, base_value=1)
    _add_head_test(repo, head_value=2, expected=2)

    witness = run_regression_witness(
        repo,
        base_ref=base,
        test_command=f"{sys.executable} -m pytest -q",
        timeout_seconds=30,
    )

    assert witness.status == "suite-delta"
    assert witness.mode == "suite"
    assert witness.witnessed is False
    assert witness.head is not None
    assert "tests/test_regression.py" not in witness.head.argv
    assert "not labeled a Regression Witness" in render_witness_markdown(witness)


def test_changed_test_detection_covers_common_non_python_conventions(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo, base_value=1)
    (repo / "pkg").mkdir()
    (repo / "pkg" / "thing_test.go").write_text(
        "package pkg\n",
        encoding="utf-8",
    )
    (repo / "src").mkdir()
    (repo / "src" / "ThingTest.java").write_text(
        "class ThingTest {}\n",
        encoding="utf-8",
    )
    (repo / "spec").mkdir()
    (repo / "spec" / "thing_spec.rb").write_text(
        "describe 'thing' do\nend\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add cross-language tests")

    files = set(changed_test_files(repo, base_ref=base))

    assert "pkg/thing_test.go" in files
    assert "src/ThingTest.java" in files
    assert "spec/thing_spec.rb" in files


def test_changed_conftest_is_replayed_with_changed_test(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo, base_value=1)

    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    tests = repo / "tests"
    tests.mkdir()
    (tests / "conftest.py").write_text(
        "import pytest\n\n"
        "@pytest.fixture\n"
        "def expected_value():\n"
        "    return 2\n",
        encoding="utf-8",
    )
    (tests / "test_regression.py").write_text(
        "from app import VALUE\n\n"
        "def test_regression(expected_value):\n"
        "    assert VALUE == expected_value\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fix with fixture-backed regression test")

    witness = run_regression_witness(
        repo,
        base_ref=base,
        test_command=_pytest_command(),
        timeout_seconds=30,
    )

    assert witness.status == "witnessed"
    assert "tests/conftest.py" in witness.support_files
    assert "tests/test_regression.py" in witness.support_files
    baseline_text = (
        (witness.base_with_head_tests.stdout if witness.base_with_head_tests else "")
        + (witness.base_with_head_tests.stderr if witness.base_with_head_tests else "")
    )
    assert "fixture 'expected_value' not found" not in baseline_text
    payload = witness_to_dict(witness)
    assert payload["schema_version"] == 3
    assert "tests/conftest.py" in payload["support_files"]
    assert "Test-support closure" in render_witness_markdown(witness)


def test_changed_test_support_detection_includes_root_and_nested_conftest(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo, base_value=1)
    (repo / "conftest.py").write_text("ROOT = True\n", encoding="utf-8")
    tests = repo / "tests"
    tests.mkdir()
    (tests / "conftest.py").write_text("NESTED = True\n", encoding="utf-8")
    (tests / "test_regression.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add test support")

    support = set(changed_test_support_files(repo, base_ref=base))

    assert "conftest.py" in support
    assert "tests/conftest.py" in support
    assert "tests/test_regression.py" in support


def test_src_layout_replay_imports_base_source_not_head_source(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "counterproof@example.test")
    _git(repo, "config", "user.name", "Counterproof Test")

    package = repo / "src" / "demo"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "value.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base src layout")
    base = _git(repo, "rev-parse", "HEAD")

    (package / "value.py").write_text("VALUE = 2\n", encoding="utf-8")
    tests = repo / "tests"
    tests.mkdir()
    (tests / "test_regression.py").write_text(
        "from demo.value import VALUE\n\n"
        "def test_regression():\n"
        "    assert VALUE == 2\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fix src code plus regression test")

    witness = run_regression_witness(
        repo,
        base_ref=base,
        test_command=_pytest_command(),
        timeout_seconds=30,
    )

    assert witness.status == "witnessed"
    assert witness.head is not None and witness.head.returncode == 0
    assert witness.base_with_head_tests is not None
    assert witness.base_with_head_tests.returncode == 1


def test_pytest_infrastructure_exit_is_inconclusive_not_witnessed(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo, base_value=1)
    tests = repo / "tests"
    tests.mkdir()
    (tests / "test_regression.py").write_text(
        "def test_placeholder():\n"
        "    assert True\n",
        encoding="utf-8",
    )

    fake_pytest = repo / "pytest"
    fake_pytest.write_text(
        "#!/usr/bin/env python3\n"
        "import os\n"
        "raise SystemExit(2 if os.environ.get('COUNTERPROOF_WITNESS_SIDE') == 'base-with-head-tests' else 0)\n",
        encoding="utf-8",
    )
    fake_pytest.chmod(0o755)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add regression test and fake pytest harness")

    witness = run_regression_witness(
        repo,
        base_ref=base,
        test_command=str(fake_pytest) + " {tests}",
        timeout_seconds=30,
    )

    assert witness.status == "inconclusive"
    assert witness.witnessed is False
    assert witness.base_with_head_tests is not None
    assert witness.base_with_head_tests.returncode == 2
    assert "Only pytest exit 1" in witness.note



def test_require_witness_rejects_suite_delta(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo, base_value=1)
    _add_head_test(repo, head_value=2, expected=2)
    payload = tmp_path / "suite.json"

    result = CliRunner().invoke(
        cli,
        [
            "witness",
            "--repo",
            str(repo),
            "--base",
            base,
            "--test-command",
            f"{sys.executable} -m pytest -q",
            "--out",
            str(tmp_path / "suite.md"),
            "--json-out",
            str(payload),
            "--require-witness",
        ],
    )

    assert result.exit_code != 0
    assert "regression witness required, got status=suite-delta" in result.output
    raw = json.loads(payload.read_text(encoding="utf-8"))
    assert raw["status"] == "suite-delta"
    assert raw["mode"] == "suite"
    assert raw["witnessed"] is False


def test_precise_witness_serializes_mode(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo, base_value=1)
    _add_head_test(repo, head_value=2, expected=2)

    witness = run_regression_witness(
        repo,
        base_ref=base,
        test_command=_pytest_command(),
        timeout_seconds=30,
    )
    payload = witness_to_dict(witness)

    assert witness.mode == "precise"
    assert payload["mode"] == "precise"
    assert payload["witnessed"] is True
    assert payload["base_sha"] == base
    assert payload["head_sha"] == _git(repo, "rev-parse", "HEAD")
    assert len(payload["evidence_digest_sha256"]) == 64

    report = render_witness_markdown(witness)
    assert "### Execution receipt" in report
    assert f"Head commit: `{payload['head_sha']}`" in report
    assert f"Base commit: `{base}`" in report
    assert "HEAD exit: `0`" in report
    assert "BASE exit: `1`" in report
    assert f"sha256:{payload['evidence_digest_sha256']}" in report
    assert "Raw stdout/stderr tails are preserved in the JSON artifact." in report


def test_review_note_exposes_minimum_reviewer_evidence(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo, base_value=1)
    _add_head_test(repo, head_value=2, expected=2)

    witness = run_regression_witness(
        repo,
        base_ref=base,
        test_command=_pytest_command(),
        timeout_seconds=30,
    )
    payload = witness_to_dict(witness)
    note = render_witness_review_note(
        payload,
        source_url="https://github.com/example/project/pull/42",
        runner_url="https://github.com/example/proof/actions/runs/7",
    )

    assert "Counterproof replay: WITNESSED" in note
    assert payload["head_sha"] in note
    assert payload["base_sha"] in note
    assert "HEAD:" in note and "exit `0`" in note
    assert "BASE:" in note and "exit `1`" in note
    assert "tests/test_regression.py" in note
    assert payload["evidence_digest_sha256"] in note
    assert "does not independently prove every claimed root cause" in note
    assert "[source PR](https://github.com/example/project/pull/42)" in note
    assert "[runner](https://github.com/example/proof/actions/runs/7)" in note


def test_share_witness_cli_writes_review_note(tmp_path):
    repo = tmp_path / "repo"
    base = _init_repo(repo, base_value=1)
    _add_head_test(repo, head_value=2, expected=2)
    witness = run_regression_witness(
        repo,
        base_ref=base,
        test_command=_pytest_command(),
        timeout_seconds=30,
    )

    receipt = tmp_path / "witness.json"
    receipt.write_text(
        json.dumps(witness_to_dict(witness)),
        encoding="utf-8",
    )
    output = tmp_path / "review.md"
    result = CliRunner().invoke(
        cli,
        [
            "share-witness",
            str(receipt),
            "--source-url",
            "https://github.com/example/project/pull/42",
            "--runner-url",
            "https://github.com/example/proof/actions/runs/7",
            "--out",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Review note: witnessed" in result.output
    text = output.read_text(encoding="utf-8")
    assert "Counterproof replay: WITNESSED" in text
    assert "Would this evidence materially help review this change?" in text
