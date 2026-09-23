from __future__ import annotations

import json

from click.testing import CliRunner

from skill_factory.evolution.cli import cli
from skill_factory.evolution.onboarding import detect_test_runner, init_github


def test_detects_pytest_from_tests_directory(tmp_path):
    (tmp_path / "tests").mkdir()

    detection = detect_test_runner(tmp_path)

    assert detection.runner == "pytest"
    assert detection.command == "python -m pytest -q {tests}"
    assert detection.confidence == "medium"
    assert detection.ecosystem == "python"
    assert "python -m pip install pytest" in detection.setup_commands


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
    assert detection.confidence == "high"
    assert detection.ecosystem == "node"
    assert detection.setup_commands == ("npm install",)


def test_detects_go_and_uses_whole_suite(tmp_path):
    (tmp_path / "go.mod").write_text("module example.com/demo\n", encoding="utf-8")

    detection = detect_test_runner(tmp_path)

    assert detection.runner == "go-test"
    assert detection.command == "go test ./..."
    assert "{tests}" not in detection.command
    assert detection.ecosystem == "go"


def test_init_github_generates_pr_head_checkout_and_counterproof_action(tmp_path):
    (tmp_path / "tests").mkdir()

    destination, detection = init_github(
        tmp_path,
        require_witness=True,
        require_clean_integrity=True,
    )

    assert detection is not None
    assert detection.runner == "pytest"
    text = destination.read_text(encoding="utf-8")
    assert "github.event.pull_request.head.sha" in text
    assert "fetch-depth: 0" in text
    assert "hippoley/SkillFactory@main" in text
    assert 'test-command: "python -m pytest -q {tests}"' in text
    assert 'require-witness: "true"' in text
    assert 'require-clean-integrity: "true"' in text
    assert 'require-proof-ready: "false"' in text
    assert "python -m pip install pytest" in text


def test_init_github_respects_explicit_command(tmp_path):
    destination, detection = init_github(
        tmp_path,
        test_command="./scripts/regression-check",
    )

    assert detection is None
    text = destination.read_text(encoding="utf-8")
    assert 'test-command: "./scripts/regression-check"' in text


def test_init_github_refuses_overwrite_without_force(tmp_path):
    (tmp_path / "tests").mkdir()
    destination, _ = init_github(tmp_path)
    destination.write_text("custom\n", encoding="utf-8")

    try:
        init_github(tmp_path)
    except FileExistsError as exc:
        assert "--force" in str(exc)
    else:
        raise AssertionError("expected FileExistsError")

    assert destination.read_text(encoding="utf-8") == "custom\n"


def test_init_github_cli_is_one_command_onboarding(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        [
            "init-github",
            "--repo",
            str(tmp_path),
            "--require-witness",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Detected pytest" in result.output
    assert "Wrote" in result.output
    workflow = tmp_path / ".github" / "workflows" / "counterproof.yml"
    assert workflow.exists()
    assert 'require-witness: "true"' in workflow.read_text(encoding="utf-8")


def test_init_github_generates_node_setup_and_lockfile_install(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"devDependencies": {"vitest": "^3.0.0"}}),
        encoding="utf-8",
    )
    (tmp_path / "package-lock.json").write_text("{}\n", encoding="utf-8")

    destination, detection = init_github(tmp_path)

    assert detection is not None
    assert detection.runner == "vitest"
    text = destination.read_text(encoding="utf-8")
    assert "actions/setup-node@v4" in text
    assert 'node-version: "22"' in text
    assert "npm ci" in text
    assert 'test-command: "npx vitest run {tests}"' in text


def test_init_github_generates_go_setup(tmp_path):
    (tmp_path / "go.mod").write_text("module example.com/demo\n", encoding="utf-8")

    destination, detection = init_github(tmp_path)

    assert detection is not None
    assert detection.runner == "go-test"
    text = destination.read_text(encoding="utf-8")
    assert "actions/setup-go@v5" in text
    assert "go-version-file: go.mod" in text
    assert 'test-command: "go test ./..."' in text


def test_explicit_command_does_not_invent_project_install_steps(tmp_path):
    destination, detection = init_github(
        tmp_path,
        test_command="./scripts/regression-check",
    )

    assert detection is None
    text = destination.read_text(encoding="utf-8")
    assert "Install your project's dependencies before Counterproof." in text
    assert "npm ci" not in text
    assert "python -m pip install pytest" not in text


def test_init_github_rejects_strong_gate_for_full_suite_runner(tmp_path):
    (tmp_path / "go.mod").write_text("module example.com/demo\n", encoding="utf-8")

    try:
        init_github(tmp_path, require_witness=True)
    except ValueError as exc:
        message = str(exc)
        assert "full-suite command" in message
        assert "--require-witness requires a precise command containing {tests}" in message
    else:
        raise AssertionError("expected ValueError for full-suite strong witness gate")


def test_init_github_allows_full_suite_reporting_without_strong_gate(tmp_path):
    (tmp_path / "go.mod").write_text("module example.com/demo\n", encoding="utf-8")

    destination, detection = init_github(tmp_path)

    assert detection is not None
    assert detection.runner == "go-test"
    text = destination.read_text(encoding="utf-8")
    assert 'test-command: "go test ./..."' in text
    assert 'require-witness: "false"' in text
    assert 'require-proof-ready: "false"' in text



def test_generic_npm_test_is_suite_mode(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"test": "custom-runner --all"}}),
        encoding="utf-8",
    )

    detection = detect_test_runner(tmp_path)

    assert detection.runner == "npm-test"
    assert detection.command == "npm test"
    assert "{tests}" not in detection.command


def test_strong_gate_rejects_generic_npm_suite(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"test": "custom-runner --all"}}),
        encoding="utf-8",
    )

    try:
        init_github(tmp_path, require_witness=True)
    except ValueError as exc:
        assert "npm-test is configured as a full-suite command" in str(exc)
    else:
        raise AssertionError("expected ValueError for generic npm full-suite gate")


def test_action_ref_can_pin_generated_workflow(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")

    destination, _ = init_github(
        tmp_path,
        action_ref="v0.2.0",
    )

    text = destination.read_text(encoding="utf-8")
    assert "uses: hippoley/SkillFactory@v0.2.0" in text


def test_action_ref_rejects_yaml_or_ref_injection(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")

    for bad_ref in ("main\n    run: echo pwned", "../main", "main@evil", ""):
        try:
            init_github(tmp_path, action_ref=bad_ref, force=True)
        except ValueError as exc:
            assert "action_ref must be a conservative Git ref" in str(exc)
        else:
            raise AssertionError(f"expected ValueError for {bad_ref!r}")


def test_counterproof_init_is_primary_onboarding_alias(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        [
            "init",
            "--repo",
            str(tmp_path),
            "--action-ref",
            "v0.2.0",
            "--require-witness",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Detected pytest" in result.output
    assert "Evidence mode: precise" in result.output
    assert "Action ref: v0.2.0" in result.output
    assert "Gates: witness=required, integrity=advisory" in result.output
    workflow = tmp_path / ".github" / "workflows" / "counterproof.yml"
    assert workflow.exists()
    text = workflow.read_text(encoding="utf-8")
    assert "uses: hippoley/SkillFactory@v0.2.0" in text


def test_init_github_remains_compatible_alias(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        ["init-github", "--repo", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert "Evidence mode: precise" in result.output



def test_counterproof_init_defaults_to_advisory_gates(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        ["init", "--repo", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert "Gates: witness=advisory, integrity=advisory" in result.output
    workflow = tmp_path / ".github" / "workflows" / "counterproof.yml"
    text = workflow.read_text(encoding="utf-8")
    assert 'require-witness: "false"' in text
    assert 'require-clean-integrity: "false"' in text
    assert 'require-proof-ready: "false"' in text



def test_counterproof_init_strict_generates_verified_gate(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        ["init", "--repo", str(tmp_path), "--strict"],
    )

    assert result.exit_code == 0, result.output
    assert "Gate mode: strict (VERIFIED proof required)" in result.output
    workflow = tmp_path / ".github" / "workflows" / "counterproof.yml"
    text = workflow.read_text(encoding="utf-8")
    assert 'require-proof-ready: "true"' in text
    assert 'require-witness: "false"' in text
    assert 'require-clean-integrity: "false"' in text


def test_counterproof_init_strict_rejects_suite_only_runner(tmp_path):
    (tmp_path / "go.mod").write_text("module example.com/demo\n", encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        ["init", "--repo", str(tmp_path), "--strict"],
    )

    assert result.exit_code != 0
    assert "--strict/--require-proof-ready requires a precise command containing {tests}" in result.output


def test_direct_onboarding_strict_contract_sets_unified_gate(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")

    destination, _ = init_github(
        tmp_path,
        require_proof_ready=True,
    )

    text = destination.read_text(encoding="utf-8")
    assert 'require-proof-ready: "true"' in text
