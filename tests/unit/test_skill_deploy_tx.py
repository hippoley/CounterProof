"""Offline compensation tests for new-only multi-agent Skill deployments."""
from pathlib import Path

import pytest

from skill_factory.skill_deploy_tx import (
    DeploymentTransactionError,
    deploy_new_only,
)


class ManagerSim:
    def __init__(self, *, mode="good", already=()):
        self.agents = {
            "codex": {
                "key": "codex", "deployed": "codex" in already,
                "target_path": "/good",
            },
            "claude_code": {
                "key": "claude_code", "deployed": "claude_code" in already,
                "target_path": "/good",
            },
        }
        self.mode = mode
        self.calls = []

    def call(self, binary, *args):
        self.calls.append(args)
        op = args[0]
        if op == "status":
            return {"agents": list(self.agents.values())}
        wanted = [
            args[index + 1]
            for index, value in enumerate(args)
            if value == "--agent"
        ]
        if op == "deploy":
            for agent in wanted:
                if self.mode == "partial" and agent == "claude_code":
                    continue
                self.agents[agent] = {
                    "key": agent, "deployed": True,
                    "target_path": "/wrong" if self.mode == "mismatch" else "/good",
                }
            if self.mode == "crash":
                raise ValueError("simulated timeout after partial write")
        elif op == "undeploy":
            for agent in wanted:
                self.agents[agent] = {
                    "key": agent, "deployed": False, "target_path": None,
                }
        else:
            raise ValueError(op)
        return {"ok": True, "dry_run": False, "agents": wanted}


def snapshot(path, *, allow_root_link):
    assert allow_root_link is True
    return "goodhash" if str(path) == "/good" else "badhash"


def execute(sim, agents=("codex", "claude_code")):
    return deploy_new_only(
        call=sim.call,
        binary=Path("/manager"),
        reference="demo-skill",
        agents=agents,
        digest="goodhash",
        snapshot=snapshot,
        source_unchanged=lambda: True,
    )


def test_good_both_agents():
    sim = ManagerSim()
    outcome = execute(sim)
    assert outcome["status"] == "VERIFIED_TARGET_BYTES"
    assert outcome["newly_deployed"] == ["codex", "claude_code"]
    assert outcome["compensation"] == "NOT_NEEDED"


def test_partial_rollback_preserves_existing_agent():
    sim = ManagerSim(mode="partial", already=("codex",))
    with pytest.raises(DeploymentTransactionError, match="rollback_new_pairs=CONFIRMED"):
        execute(sim)
    assert sim.agents["codex"]["deployed"] is True
    assert sim.agents["claude_code"]["deployed"] is False
    assert ("deploy", "demo-skill", "--agent", "claude_code") in sim.calls
    assert ("undeploy", "demo-skill", "--agent", "claude_code") in sim.calls


def test_wrong_deployed_bytes_compensated():
    sim = ManagerSim(mode="mismatch")
    with pytest.raises(DeploymentTransactionError, match="rollback_new_pairs=CONFIRMED"):
        execute(sim)
    assert not sim.agents["codex"]["deployed"]


def test_drift_on_existing_refuses_before_any_write():
    sim = ManagerSim(already=("codex",))
    sim.agents["codex"]["target_path"] = "/wrong"
    with pytest.raises(DeploymentTransactionError, match="existing target drift"):
        execute(sim)
    assert not any(call[0] == "deploy" for call in sim.calls)


def test_already_installed_does_not_deploy_again():
    sim = ManagerSim(already=("codex", "claude_code"))
    result = execute(sim)
    assert result["newly_deployed"] == []
    assert result["previously_deployed"] == ["codex", "claude_code"]
    assert not any(call[0] == "deploy" for call in sim.calls)


def test_unknown_target_rejected():
    sim = ManagerSim()
    with pytest.raises(DeploymentTransactionError, match="unknown target agent"):
        execute(sim, agents=("not_real",))


def test_external_cli_crash_compensates():
    sim = ManagerSim(mode="crash")
    with pytest.raises(DeploymentTransactionError, match="rollback_new_pairs=CONFIRMED"):
        execute(sim)
    assert not sim.agents["codex"]["deployed"]
