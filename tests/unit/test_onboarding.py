from __future__ import annotations

import json

from click.testing import CliRunner

from skill_factory.evolution.cli import cli
from skill_factory.evolution.onboarding import detect_test_runner, init_github


def test_detects_pytest_and_generates_precise_command(tmp_path):
    (tmp_path / "tests").mkdir()

    detection = detect_test_runner(tmp_path)

    assert detection.runner == "pytest"
    assert detection.command == "python -m pytest -q {tests}"
    assert detection.ecosystem == "python"


def test_detects_vitest_before_generic_npm_test(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "devDependencies": {"vitest": "^3.0.0"},
                "scripts": {"test": "vitest"},
            }
        ),
        encoding="utf-8",
    )

    detection = detect_test_runner(tmp_path)

    assert detection.runner == "vitest"
    assert detection.command == "npx vitest run {tests}"


def test_generic_npm_test_is_suite_level(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"test": "custom-runner --all"}}),
        encoding="utf-8",
    )

    detection = detect_test_runner(tmp_path)

    assert detection.runner == "npm-test"
    assert detection.command == "npm test"
    assert "{tests}" not in detection.command


def test_go_is_suite_level(tmp_path):
    (tmp_path / "go.mod").write_text("module example.com/demo\n", encoding="utf-8")

    detection = detect_test_runner(tmp_path)

    assert detection.runner == "go-test"
    assert detection.command == "go test ./..."


def test_init_writes_canonical_counterproof_root_action(tmp_path):
    (tmp_path / "tests").mkdir()

    destination, _ = init_github(
        tmp_path,
        require_witness=True,
        require_clean_integrity=True,
    )

    text = destination.read_text(encoding="utf-8")
    assert "uses: hippoley/CounterProof@main" in text
    assert 'require-witness: "true"' in text
    assert 'require-clean-integrity: "true"' in text
    assert "github.event.pull_request.head.sha" in text


def test_init_refuses_to_overwrite_existing_workflow(tmp_path):
    (tmp_path / "tests").mkdir()
    destination, _ = init_github(tmp_path)

    try:
        init_github(tmp_path)
    except FileExistsError as exc:
        assert "use --force" in str(exc)
    else:
        raise AssertionError("expected FileExistsError")

    assert destination.exists()


def test_strict_cli_is_one_switch_for_both_gates(tmp_path):
    (tmp_path / "tests").mkdir()

    result = CliRunner().invoke(
        cli,
        ["init", "--repo", str(tmp_path), "--strict"],
    )

    assert result.exit_code == 0, result.output
    assert "Gate mode: strict" in result.output
    workflow = tmp_path / ".github" / "workflows" / "counterproof.yml"
    text = workflow.read_text(encoding="utf-8")
    assert 'require-witness: "true"' in text
    assert 'require-clean-integrity: "true"' in text


def test_strict_rejects_suite_only_runner(tmp_path):
    (tmp_path / "go.mod").write_text("module example.com/demo\n", encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        ["init", "--repo", str(tmp_path), "--strict"],
    )

    assert result.exit_code != 0
    assert "requires a precise command containing {tests}" in result.output


def test_action_ref_can_be_pinned(tmp_path):
    (tmp_path / "tests").mkdir()

    destination, _ = init_github(tmp_path, action_ref="abc1234")

    text = destination.read_text(encoding="utf-8")
    assert "uses: hippoley/CounterProof@abc1234" in text


def test_action_ref_rejects_injection(tmp_path):
    (tmp_path / "tests").mkdir()

    try:
        init_github(tmp_path, action_ref="main\nrun: echo pwned")
    except ValueError as exc:
        assert "action_ref must be a conservative Git ref" in str(exc)
    else:
        raise AssertionError("expected ValueError")
