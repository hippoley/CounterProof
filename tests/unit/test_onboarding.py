from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from skill_factory.evolution.cli import cli
from skill_factory.evolution.onboarding import (
    detect_runner,
    initialize_github,
    render_workflow,
)


def test_detect_python_and_render_valid_workflow(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='demo'\nversion='0.0.1'\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()

    guess = detect_runner(tmp_path)
    assert guess.ecosystem == "python"
    assert guess.test_command == "python -m pytest -q {tests}"

    workflow = render_workflow(guess)
    parsed = yaml.safe_load(workflow)
    assert parsed["name"] == "Counterproof"
    assert parsed["permissions"]["contents"] == "read"
    assert parsed["permissions"]["pull-requests"] == "write"
    assert "github.event.pull_request.head.sha" in workflow
    assert "actions/witness@main" in workflow


def test_detect_node_test_runners(tmp_path):
    cases = [
        ("vitest run", "npx vitest run {tests}"),
        ("jest", "npx jest {tests} --runInBand"),
        ("playwright test", "npx playwright test {tests}"),
    ]
    for index, (script, expected) in enumerate(cases):
        repo = tmp_path / str(index)
        repo.mkdir()
        (repo / "package.json").write_text(
            json.dumps({"scripts": {"test": script}}),
            encoding="utf-8",
        )
        assert detect_runner(repo).test_command == expected


def test_detect_go_and_ruby(tmp_path):
    go = tmp_path / "go"
    go.mkdir()
    (go / "go.mod").write_text("module demo\n", encoding="utf-8")
    assert detect_runner(go).test_command == "go test ./..."

    ruby = tmp_path / "ruby"
    ruby.mkdir()
    (ruby / "Gemfile").write_text("source 'https://rubygems.org'\n", encoding="utf-8")
    assert detect_runner(ruby).test_command == "bundle exec rspec {tests}"


def test_init_refuses_low_confidence_unknown_repo_without_command(tmp_path):
    with pytest.raises(ValueError, match="Could not infer a test command safely"):
        initialize_github(tmp_path)


def test_init_accepts_explicit_command_for_unknown_repo(tmp_path):
    path, guess = initialize_github(
        tmp_path,
        test_command="./scripts/regression-check",
        action_ref="v0.2.0",
    )

    assert path.is_file()
    assert guess.confidence == "explicit"
    text = path.read_text(encoding="utf-8")
    assert 'test-command: "./scripts/regression-check"' in text
    assert "actions/witness@v0.2.0" in text


def test_init_does_not_overwrite_existing_workflow_without_force(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    path, _ = initialize_github(tmp_path)
    original = path.read_text(encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        initialize_github(tmp_path)

    assert path.read_text(encoding="utf-8") == original


def test_init_can_enable_strict_gates(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    path, _ = initialize_github(
        tmp_path,
        require_witness=True,
        require_clean_integrity=True,
    )
    text = path.read_text(encoding="utf-8")

    assert 'require-witness: "true"' in text
    assert 'require-clean-integrity: "true"' in text


def test_counterproof_init_cli_is_advisory_by_default(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    result = CliRunner().invoke(
        cli,
        ["init", "--repo", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert "Detected python test stack" in result.output
    assert "advisory mode" in result.output
    workflow = tmp_path / ".github" / "workflows" / "counterproof.yml"
    assert workflow.is_file()
