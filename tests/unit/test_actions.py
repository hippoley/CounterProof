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
    assert action["inputs"]["require-witness"]["default"] == "false"
    assert action["inputs"]["result-protocol"]["default"] == "exit-code"
    assert action["inputs"]["require-clean-integrity"]["default"] == "false"
    assert "evidence-mode" in action["outputs"]
    assert "integrity-status" in action["outputs"]

    names = [step["name"] for step in action["runs"]["steps"]]
    assert names == [
        "Install Counterproof",
        "Resolve base ref",
        "Check PR head checkout",
        "Fetch base commit",
        "Run Regression Witness",
        "Check proof integrity",
        "Publish sticky witness comment",
    ]


def test_legacy_witness_subpath_remains_compatible():
    action = _load("actions/witness/action.yml")

    assert action["name"] == "Counterproof Regression Witness"
    assert action["inputs"]["test-command"]["required"] is True
    assert action["inputs"]["result-protocol"]["default"] == "exit-code"
    assert "suite-delta" in action["outputs"]["status"]["description"]
    assert "evidence-mode" in action["outputs"]


def test_advanced_behavior_proof_is_explicit_subpath():
    action = _load("actions/behavior-proof/action.yml")

    assert action["name"] == "Counterproof Behavior Proof"
    assert "trace" in action["inputs"]
    assert "experiment-manifest" in action["inputs"]
    assert "selection-state" in action["outputs"]

    names = [step["name"] for step in action["runs"]["steps"]]
    assert "Build Behavior Proof" in names
    assert "Publish sticky PR proof" in names


def test_root_and_subpath_install_from_correct_action_paths():
    root = Path("action.yml").read_text(encoding="utf-8")
    witness = Path("actions/witness/action.yml").read_text(encoding="utf-8")
    advanced = Path("actions/behavior-proof/action.yml").read_text(encoding="utf-8")

    assert 'python -m pip install "${{ github.action_path }}"' in root
    assert 'python -m pip install "${{ github.action_path }}/../.."' in witness
    assert 'python -m pip install "${{ github.action_path }}/../.."' in advanced


def test_witness_actions_forward_result_protocol_to_cli():
    for path in ("action.yml", "actions/witness/action.yml"):
        text = Path(path).read_text(encoding="utf-8")
        assert "RESULT_PROTOCOL: ${{ inputs.result-protocol }}" in text
        assert '--result-protocol "$RESULT_PROTOCOL"' in text


def test_actions_do_not_execute_untrusted_pr_text_as_shell():
    texts = [
        Path("action.yml").read_text(encoding="utf-8"),
        Path("actions/witness/action.yml").read_text(encoding="utf-8"),
        Path("actions/behavior-proof/action.yml").read_text(encoding="utf-8"),
    ]
    dangerous_contexts = (
        "github.event.pull_request.body",
        "github.event.issue.body",
        "github.event.head_commit.message",
    )
    for text in texts:
        for context in dangerous_contexts:
            assert context not in text


def test_witness_comment_failure_stays_non_fatal():
    text = Path("action.yml").read_text(encoding="utf-8")

    assert "::warning::Regression Witness generated" in text
    assert "pull-requests: write permission" in text
