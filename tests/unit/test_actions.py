from __future__ import annotations

from pathlib import Path

import yaml


def _load(path: str) -> dict:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def test_root_action_is_regression_witness():
    action = _load("action.yml")

    assert action["name"] == "Counterproof Regression Witness"
    assert action["runs"]["using"] == "composite"
    assert action["inputs"]["test-command"]["required"] is True
    assert "integrity-status" in action["outputs"]

    steps = action["runs"]["steps"]
    names = [step["name"] for step in steps]
    assert "Run Regression Witness" in names
    assert "Check proof integrity" in names


def test_advanced_behavior_proof_action_is_valid_composite_action():
    action = _load("actions/behavior-proof/action.yml")

    assert action["name"] == "Counterproof Behavior Proof"
    assert action["runs"]["using"] == "composite"
    assert "trace" in action["inputs"]
    assert "experiment-manifest" in action["inputs"]
    assert "selection-state" in action["outputs"]

    steps = action["runs"]["steps"]
    names = [step["name"] for step in steps]
    assert "Install Counterproof" in names
    assert "Build Behavior Proof" in names
    assert "Publish sticky PR proof" in names


def test_regression_witness_action_alias_is_valid_composite_action():
    action = _load("actions/witness/action.yml")

    assert action["name"] == "Counterproof Regression Witness"
    assert action["runs"]["using"] == "composite"
    assert action["inputs"]["test-command"]["required"] is True
    assert action["inputs"]["require-witness"]["default"] == "false"
    assert action["inputs"]["require-clean-integrity"]["default"] == "false"
    assert "integrity-status" in action["outputs"]

    steps = action["runs"]["steps"]
    names = [step["name"] for step in steps]
    assert names == [
        "Install Counterproof",
        "Resolve base ref",
        "Check PR head checkout",
        "Fetch base commit",
        "Run Regression Witness",
        "Check proof integrity",
        "Publish sticky witness comment",
    ]


def test_witness_action_keeps_comment_failure_non_fatal():
    text = Path("actions/witness/action.yml").read_text(encoding="utf-8")

    assert "::warning::Regression Witness generated" in text
    assert "pull-requests: write permission" in text


def test_actions_do_not_execute_pr_text_as_shell():
    root = Path("action.yml").read_text(encoding="utf-8")
    witness = Path("actions/witness/action.yml").read_text(encoding="utf-8")
    behavior = Path("actions/behavior-proof/action.yml").read_text(encoding="utf-8")

    dangerous_contexts = [
        "github.event.pull_request.body",
        "github.event.issue.body",
        "github.event.head_commit.message",
    ]
    for context in dangerous_contexts:
        assert context not in root
        assert context not in witness
        assert context not in behavior


def test_root_and_alias_emit_compact_proof_card():
    for path in ("action.yml", "actions/witness/action.yml"):
        text = Path(path).read_text(encoding="utf-8")
        assert "| Regression Witness | **{witness_status}** |" in text
        assert "| PR head + PR tests | **{verdict(head)}** |" in text
        assert "| Base code + same tests | **{verdict(base)}** |" in text
        assert "| Proof Integrity | **{integrity_status}** |" in text
        assert "<summary>Evidence details</summary>" in text
        assert "cat \"$report\"" not in text


def test_root_action_is_marketplace_default_not_advanced_causal_entry():
    root = _load("action.yml")
    advanced = _load("actions/behavior-proof/action.yml")

    assert root["name"] == "Counterproof Regression Witness"
    assert "test-command" in root["inputs"]
    assert "trace" not in root["inputs"]

    assert advanced["name"] == "Counterproof Behavior Proof"
    assert "trace" in advanced["inputs"]
    assert "experiment-manifest" in advanced["inputs"]
