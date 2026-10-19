"""Offline fail-closed integration tests with a simulated Skills Manager protocol.

These test our adapter/gate logic, NOT the real upstream Rust executable or real
agent behavior. Never count them as production or independent quality evidence.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from skill_factory.skill_gate import (
    GateError, _checked_receipt, _digest, create_key, evaluate, promote,
)
from skill_factory.skills_mode import skill_mode


MANAGER = r'''#!PYTHON
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
if args[0:2] != ["--json", "skills"]:
    sys.exit(3)
command = args[2]
root = Path(os.environ["SIM_SKILL_DIR"])
name = "demo-skill"
target_root = Path(os.environ["SIM_TARGETS"])
agent_names = [
    args[i + 1] for i, item in enumerate(args)
    if item == "--agent" and i + 1 < len(args)
]
if command == "show":
    print(json.dumps({"id": "skill-test-001", "name": name, "path": str(root)}))
elif command == "deploy":
    preview = "--dry-run" in args
    if not preview and os.environ.get("SIM_DEPLOY_MODE") != "partial":
        for agent in agent_names:
            target = target_root / agent / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink():
                target.unlink()
            if os.environ.get("SIM_DEPLOY_MODE") == "stale":
                stale = target_root / "stale-target"
                stale.mkdir(parents=True, exist_ok=True)
                (stale / "SKILL.md").write_text("this is not the evaluated Skill")
                target.symlink_to(stale, target_is_directory=True)
            else:
                target.symlink_to(root, target_is_directory=True)
    print(json.dumps({
        "ok": True, "action": "deploy", "dry_run": preview,
        "agents": agent_names, "changed_pairs": len(agent_names),
    }))
elif command == "status":
    agents = []
    for agent in ("codex", "claude_code"):
        target = target_root / agent / name
        agents.append({
            "key": agent, "deployed": target.is_symlink(),
            "target_path": str(target) if target.is_symlink() else None,
        })
    print(json.dumps({"agents": agents}))
else:
    sys.exit(4)
'''

RUNNER = r'''#!PYTHON
import json
import os
import sys

payload = json.load(sys.stdin)
case = payload["case_id"]
expected = "correct-" + case
mode = os.environ.get("SIM_RUNNER_MODE", "good")
if payload["arm"] == "skill":
    output = "wrong" if mode == "regress" and case == "case-2" else expected
elif mode == "no-gain":
    output = expected
elif case == "case-1":
    output = "wrong"
else:
    output = expected
print(json.dumps({"output": output}))
'''


@pytest.fixture
def rig(tmp_path, monkeypatch):
    skill = tmp_path / "library" / "demo-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: demo-skill\n"
        "description: Use when proving independently scoped agent behavior.\n---\n"
        "## Purpose\nCheck reproducible local behavior.\n"
        "## When to use\nWhen external evidence is needed.\n"
        "## Procedure\nRead the evaluated Skill.\n", encoding="utf-8",
    )
    manager = tmp_path / "sim-manager"
    manager.write_text(MANAGER.replace("#!PYTHON", f"#!{sys.executable}"),
                       encoding="utf-8")
    manager.chmod(0o755)
    runner = tmp_path / "sim-runner"
    runner.write_text(RUNNER.replace("#!PYTHON", f"#!{sys.executable}"),
                      encoding="utf-8")
    runner.chmod(0o755)
    suite = tmp_path / "holdout.json"
    suite.write_text(json.dumps({
        "schema_version": "counterproof.skill-suite/v0.1",
        "suite_id": "external-test-fixture",
        "cases": [
            {
                "id": f"case-{i}", "prompt": f"Task {i}",
                "expected_output": f"correct-case-{i}",
            }
            for i in range(1, 5)
        ],
    }), encoding="utf-8")
    key = create_key(tmp_path / "local-key")
    monkeypatch.setenv("SIM_SKILL_DIR", str(skill))
    monkeypatch.setenv("SIM_TARGETS", str(tmp_path / "targets"))
    return {
        "skill": skill, "manager": str(manager), "runner": str(runner),
        "suite": suite, "key": key, "tmp": tmp_path,
    }


def _receipt(rig):
    return evaluate(
        rig["manager"], "demo-skill", rig["suite"], rig["runner"],
        key_file=rig["key"],
    )


def _write(rig, receipt):
    path = rig["tmp"] / "receipt.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    return path


def test_key_is_local_secret_and_not_overwritten(rig):
    assert len(rig["key"].read_bytes()) == 32
    with pytest.raises(GateError):
        create_key(rig["key"])


def test_evaluate_has_measured_paired_cases(rig):
    receipt = _receipt(rig)
    assert receipt["verdict"] == "PASS_SCOPED"
    assert receipt["gain_cases"] == 1
    assert receipt["regression_cases"] == 0
    assert len(receipt["cases"]) == 4
    assert [case["execution_order"] for case in receipt["cases"]] == [
        ["baseline", "skill"],
        ["skill", "baseline"],
        ["baseline", "skill"],
        ["skill", "baseline"],
    ]
    assert receipt["independence"] == "PATH_SEPARATED_ONLY_AUTHORSHIP_NOT_VERIFIED"
    assert _checked_receipt(_write(rig, receipt), rig["key"]) == receipt


def test_explicit_runner_regression_blocks_promotion(rig):
    runner = Path(rig["runner"])
    runner.write_text(
        runner.read_text().replace(
            'mode = os.environ.get("SIM_RUNNER_MODE", "good")',
            'mode = "regress"',
        ), encoding="utf-8",
    )
    receipt = _receipt(rig)
    assert receipt["verdict"] == "FAIL"
    with pytest.raises(GateError, match="did not pass"):
        promote(
            rig["manager"], "demo-skill", _write(rig, receipt),
            ("codex",), key_file=rig["key"], suite_path=rig["suite"],
        )


def test_no_gain_blocks_promotion(rig):
    runner = Path(rig["runner"])
    runner.write_text(
        runner.read_text().replace(
            'mode = os.environ.get("SIM_RUNNER_MODE", "good")',
            'mode = "no-gain"',
        ), encoding="utf-8",
    )
    receipt = _receipt(rig)
    assert receipt["gain_cases"] == 0
    assert receipt["verdict"] == "FAIL"


def test_forged_digest_without_key_is_rejected(rig):
    receipt = _receipt(rig)
    receipt["gain_cases"] = 999
    receipt["receipt_sha256"] = _digest({
        k: v for k, v in receipt.items()
        if k not in ("receipt_sha256", "attestation_hmac_sha256")
    })
    with pytest.raises(GateError, match="attestation"):
        _checked_receipt(_write(rig, receipt), rig["key"])


def test_altered_skill_after_eval_blocks_promotion(rig):
    receipt = _receipt(rig)
    (rig["skill"] / "SKILL.md").write_text(
        (rig["skill"] / "SKILL.md").read_text() + "\nmodified\n",
        encoding="utf-8",
    )
    with pytest.raises(GateError, match="changed since evaluation"):
        promote(
            rig["manager"], "demo-skill", _write(rig, receipt), ("codex",),
            key_file=rig["key"], suite_path=rig["suite"],
        )


def test_changed_holdout_blocks_promotion(rig):
    receipt = _receipt(rig)
    rig["suite"].write_text(rig["suite"].read_text() + " ", encoding="utf-8")
    with pytest.raises(GateError, match="suite changed"):
        promote(
            rig["manager"], "demo-skill", _write(rig, receipt), ("codex",),
            key_file=rig["key"], suite_path=rig["suite"],
        )


def test_changed_runner_blocks_promotion(rig):
    receipt = _receipt(rig)
    runner = Path(rig["runner"])
    runner.write_text(runner.read_text() + "\n# changed\n", encoding="utf-8")
    with pytest.raises(GateError, match="runner changed"):
        promote(
            rig["manager"], "demo-skill", _write(rig, receipt), ("codex",),
            key_file=rig["key"], suite_path=rig["suite"],
        )


def test_preflight_is_non_mutating_and_apply_needs_confirmation(rig):
    receipt = _receipt(rig)
    path = _write(rig, receipt)
    first = promote(
        rig["manager"], "demo-skill", path, ("codex", "claude_code"),
        key_file=rig["key"], suite_path=rig["suite"],
    )
    assert first["status"] == "PREFLIGHT_ONLY"
    assert not (rig["tmp"] / "targets").exists()
    with pytest.raises(GateError, match="confirm-sha256"):
        promote(
            rig["manager"], "demo-skill", path, ("codex",),
            key_file=rig["key"], suite_path=rig["suite"], apply=True,
        )


def test_explicit_apply_verifies_both_target_trees(rig):
    receipt = _receipt(rig)
    result = promote(
        rig["manager"], "demo-skill", _write(rig, receipt),
        ("codex", "claude_code"), key_file=rig["key"], suite_path=rig["suite"],
        apply=True, confirm_sha256=receipt["source"]["tree_sha256"],
    )
    assert result["status"] == "VERIFIED_TARGET_BYTES"
    for agent in ("codex", "claude_code"):
        assert (rig["tmp"] / "targets" / agent / "demo-skill").is_symlink()


def test_partial_deployment_cannot_be_reported_as_success(rig, monkeypatch):
    receipt = _receipt(rig)
    monkeypatch.setenv("SIM_DEPLOY_MODE", "partial")
    with pytest.raises(GateError, match="PARTIAL_DEPLOYMENT"):
        promote(
            rig["manager"], "demo-skill", _write(rig, receipt),
            ("codex", "claude_code"), key_file=rig["key"],
            suite_path=rig["suite"], apply=True,
            confirm_sha256=receipt["source"]["tree_sha256"],
        )


def test_duplicate_agents_are_rejected(rig):
    receipt = _receipt(rig)
    with pytest.raises(GateError, match="unique"):
        promote(
            rig["manager"], "demo-skill", _write(rig, receipt),
            ("codex", "codex"), key_file=rig["key"], suite_path=rig["suite"],
        )


def test_cli_runs_explicit_eval_and_preflight(rig):
    receipt_path = rig["tmp"] / "cli-eval.json"
    result = CliRunner().invoke(
        skill_mode, [
            "evaluate", "demo-skill",
            "--suite", str(rig["suite"]),
            "--runner-binary", rig["runner"],
            "--manager-binary", rig["manager"],
            "--key", str(rig["key"]),
            "--out", str(receipt_path),
        ],
    )
    assert result.exit_code == 0, result.output
    receipt = json.loads(receipt_path.read_text())
    next_result = CliRunner().invoke(
        skill_mode, [
            "promote", "demo-skill",
            "--suite", str(rig["suite"]), "--receipt", str(receipt_path),
            "--key", str(rig["key"]), "--manager-binary", rig["manager"],
            "--agent", "codex",
        ],
    )
    assert next_result.exit_code == 0, next_result.output
    assert "PREFLIGHT_ONLY" in next_result.output
    assert not (rig["tmp"] / "targets").exists()


def test_changed_manager_binary_blocks_promotion(rig):
    receipt = _receipt(rig)
    binary = Path(rig["manager"])
    binary.write_text(binary.read_text() + "\n# Upgraded behind our back\n")
    with pytest.raises(GateError, match="Manager binary changed"):
        promote(
            rig["manager"], "demo-skill", _write(rig, receipt), ("codex",),
            key_file=rig["key"], suite_path=rig["suite"],
        )


def test_attestation_key_must_not_be_deployable_skill_file(rig):
    key_in_skill = create_key(rig["skill"] / "signing-secret")
    with pytest.raises(GateError, match="outside the managed Skill"):
        evaluate(
            rig["manager"], "demo-skill", rig["suite"], rig["runner"],
            key_file=key_in_skill,
        )


def test_external_suite_must_not_live_in_skill_dir(rig):
    internal = rig["skill"] / "leaked-holdout.json"
    internal.write_bytes(rig["suite"].read_bytes())
    with pytest.raises(GateError, match="outside managed Skill"):
        evaluate(
            rig["manager"], "demo-skill", internal, rig["runner"],
            key_file=rig["key"],
        )


def test_wrong_signing_key_cannot_promote(rig):
    receipt = _receipt(rig)
    other_key = create_key(rig["tmp"] / "other-attestation")
    with pytest.raises(GateError, match="attestation failed"):
        promote(
            rig["manager"], "demo-skill", _write(rig, receipt), ("codex",),
            key_file=other_key, suite_path=rig["suite"],
        )


def test_manager_claims_deployed_but_target_bytes_differ(rig, monkeypatch):
    receipt = _receipt(rig)
    monkeypatch.setenv("SIM_DEPLOY_MODE", "stale")
    with pytest.raises(GateError, match="PARTIAL_DEPLOYMENT"):
        promote(
            rig["manager"], "demo-skill", _write(rig, receipt),
            ("codex", "claude_code"), key_file=rig["key"],
            suite_path=rig["suite"], apply=True,
            confirm_sha256=receipt["source"]["tree_sha256"],
        )


def test_skill_mutation_during_model_run_fails_closed(rig):
    runner = Path(rig["runner"])
    code = runner.read_text()
    anchor = 'print(json.dumps({"output": output}))'
    assert anchor in code
    runner.write_text(code.replace(
        anchor,
        'if payload["arm"] == "skill":\n'
        '    from pathlib import Path\n'
        '    doc = Path(payload["skill_path"]) / "SKILL.md"\n'
        '    doc.write_text(doc.read_text() + "\\nmodel mutated skill")\n'
        + anchor,
    ), encoding="utf-8")
    with pytest.raises(GateError, match="mutated during paired evaluation"):
        _receipt(rig)


def test_invalid_runner_output_is_not_a_passing_eval(rig):
    runner = Path(rig["runner"])
    code = runner.read_text()
    runner.write_text(code.replace(
        'print(json.dumps({"output": output}))',
        'print(json.dumps({"unexpected": True}))',
    ), encoding="utf-8")
    with pytest.raises(GateError, match="must contain a string output"):
        _receipt(rig)
