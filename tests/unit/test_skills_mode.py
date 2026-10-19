"""Offline tests: inspect is non-executing and Manager forwards argument vectors."""
import hashlib
import json

from click.testing import CliRunner

from skill_factory.skills_mode import skill_mode


def test_commands_exposed():
    result = CliRunner().invoke(skill_mode, ["--help"])
    assert result.exit_code == 0
    for name in ("inspect", "evolve", "manager"):
        assert name in result.output


def test_skill_static_receipt_is_not_proof_or_deployment(tmp_path):
    skill_dir = tmp_path / "demo"
    skill_dir.mkdir()
    content = (
        "---\nname: demo\ndescription: Use when checking local skill metadata.\n---\n"
        "## Purpose\nConfirm static shape.\n## When to use\nIn a test.\n"
        "## Procedure\nInspect only.\n"
    )
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    result = CliRunner().invoke(
        skill_mode, ["inspect", str(skill_dir), "--json-output"]
    )
    assert result.exit_code == 0, result.output
    receipt = json.loads(result.output)
    assert receipt["static_verdict"] == "PASS"
    assert receipt["evaluation_status"] == "NOT_RUN"
    assert receipt["deployment_status"] == "NOT_PERFORMED"
    assert receipt["skill_md_sha256"] == hashlib.sha256(content.encode()).hexdigest()


def test_inspect_never_executes_skill_scripts(tmp_path):
    skill_dir = tmp_path / "demo"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Use when checking execution safety.\n---\n"
        "## Procedure\nInspect only.\n",
        encoding="utf-8",
    )
    (skill_dir / "scripts").mkdir()
    (skill_dir / "scripts" / "run.py").write_text(
        "from pathlib import Path\nPath('unwanted').touch()\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(
        skill_mode, ["inspect", str(skill_dir), "--json-output"]
    )
    assert result.exit_code == 0, result.output
    assert not (tmp_path / "unwanted").exists()


def test_inspect_rejects_linked_directory(tmp_path):
    skill_dir = tmp_path / "demo"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("hello", encoding="utf-8")
    alias = tmp_path / "alias"
    alias.symlink_to(skill_dir, target_is_directory=True)
    result = CliRunner().invoke(skill_mode, ["inspect", str(alias)])
    assert result.exit_code != 0
    assert "symlink" in result.output


def test_missing_manager_binary_is_reported():
    result = CliRunner().invoke(
        skill_mode,
        ["manager", "--binary", "/not/a/real/binary", "--", "skills", "list"],
    )
    assert result.exit_code != 0
    assert "not found" in result.output


def test_manager_preserves_arguments_without_shell(tmp_path):
    binary = tmp_path / "skills-manager-cli"
    output = tmp_path / "argv.json"
    binary.write_text(
        "#!/usr/bin/env python3\nimport json, sys\nfrom pathlib import Path\n"
        f"Path({str(output)!r}).write_text(json.dumps(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    binary.chmod(0o755)
    result = CliRunner().invoke(
        skill_mode,
        ["manager", "--binary", str(binary), "--",
         "skills", "status", "a;echo UNWANTED"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(output.read_text()) == [
        "skills", "status", "a;echo UNWANTED"
    ]

def test_counterproof_cli_registers_skill_mode():
    from skill_factory.evolution.cli import cli

    result = CliRunner().invoke(cli, ["skill", "--help"])
    assert result.exit_code == 0, result.output
    assert "inspect" in result.output
    assert "manager" in result.output
    assert "evolve" in result.output


def test_manager_bridge_blocks_unevaluated_deploy():
    result = CliRunner().invoke(
        skill_mode, ["manager", "--", "skills", "deploy", "my-skill", "--agent", "codex"],
    )
    assert result.exit_code != 0
    assert "direct mutation blocked" in result.output


def test_manager_bridge_blocks_install_and_sync():
    for argv in (
        ("skills", "install", "/tmp/untrusted"),
        ("skills", "sync"),
        ("presets", "deploy", "work"),
        ("git", "pull"),
    ):
        result = CliRunner().invoke(skill_mode, ["manager", "--", *argv])
        assert result.exit_code != 0
        assert "direct mutation blocked" in result.output
