from pathlib import Path

import pytest
from click.testing import CliRunner

from skill_factory.evolution.capabilities import capability_report
from skill_factory.evolution.cli import cli as evo_cli
from skill_factory.evolution.models import (
    CandidateMutation,
    Evidence,
    EvolutionPacket,
    Hypothesis,
    ReplayResult,
)
from skill_factory.evolution.replay import run_replay_manifest, serialize_replays
from skill_factory.evolution.report import render_evolution_pr


def test_candidate_promotes_only_without_regression_or_risk():
    candidate = CandidateMutation(
        id="c1",
        surface="policy",
        title="guard",
        hypothesis_id="h1",
        behavior_diff="before -> after",
        replay_results=(
            ReplayResult("case-1", "regression", "pass", 0.0, 1.0),
            ReplayResult("case-2", "holdout", "pass", 1.0, 1.0),
        ),
    )
    assert candidate.eligible_for_promotion is True
    assert candidate.regression_count == 0


def test_regression_blocks_promotion():
    candidate = CandidateMutation(
        id="c1",
        surface="policy",
        title="guard",
        hypothesis_id="h1",
        behavior_diff="before -> after",
        replay_results=(
            ReplayResult("fixed", "regression", "pass", 0.0, 1.0),
            ReplayResult("broke", "holdout", "pass", 1.0, 0.0),
        ),
    )
    assert candidate.mean_delta == 0.0
    assert candidate.regression_count == 1
    assert candidate.eligible_for_promotion is False


def test_risk_flag_blocks_promotion():
    candidate = CandidateMutation(
        id="c1",
        surface="skill",
        title="guard",
        hypothesis_id="h1",
        behavior_diff="before -> after",
        replay_results=(ReplayResult("fixed", "regression", "pass", 0.0, 1.0),),
        risk_flags=("latency increase",),
    )
    assert candidate.eligible_for_promotion is False


def test_infra_error_is_not_counted_as_behavior_regression():
    candidate = CandidateMutation(
        id="c1",
        surface="tool",
        title="guard",
        hypothesis_id="h1",
        behavior_diff="before -> after",
        replay_results=(
            ReplayResult("fixed", "regression", "pass", 0.0, 1.0),
            ReplayResult("infra", "holdout", "infra_error", 1.0, 0.0),
        ),
    )
    assert candidate.regression_count == 0
    assert candidate.mean_delta == 1.0


def test_evidence_confidence_bounds_are_enforced():
    with pytest.raises(ValueError):
        Evidence(
            source="bad",
            kind="human",
            verdict="negative",
            confidence=1.5,
            note="invalid confidence",
        )


def test_report_contains_behavior_change_and_replay_matrix():
    candidate = CandidateMutation(
        id="c1",
        surface="policy",
        title="guard",
        hypothesis_id="h1",
        behavior_diff="query first -> validate first",
        replay_results=(ReplayResult("case-1", "regression", "pass", 0.0, 1.0),),
        rollback_ref="policy@old",
    )
    packet = EvolutionPacket(
        packet_id="evo-1",
        agent="demo-agent",
        failure_summary="premature query",
        decision_capsule="selected query before validation",
        outcome_receipt="review blocked it",
        hypotheses=(
            Hypothesis(
                id="h1",
                mechanism="missing policy guard",
                target_surface="policy",
                uncertainty=0.1,
            ),
        ),
        candidates=(candidate,),
        selected_candidate_id="c1",
    )

    report = render_evolution_pr(packet)
    assert "EvoPR" in report
    assert "Causal hypotheses" in report
    assert "Replay matrix" in report
    assert "query first -> validate first" in report
    assert "Eligible for promotion." in report


def test_evopr_cli_builds_real_example(tmp_path):
    output = tmp_path / "EVOLUTION_PR.md"
    example = Path("examples/evolution_pr.json")

    result = CliRunner().invoke(
        evo_cli,
        ["build", str(example), "--out", str(output)],
    )

    assert result.exit_code == 0, result.output
    assert output.exists()
    rendered = output.read_text(encoding="utf-8")
    assert "evo-tenant-scope-001" in rendered
    assert "Enforce tenant validation precondition" in rendered
    assert "security-holdout" in rendered
    assert "Eligible for promotion." in rendered


def test_real_command_replay_executes_baseline_and_candidate():
    executed = run_replay_manifest(Path("examples/replay_suite.json"))
    payload = serialize_replays(executed)
    cases = {case["case_id"]: case for case in payload["cases"]}

    assert cases["failure-418"]["baseline_score"] == 0.0
    assert cases["failure-418"]["candidate_score"] == 1.0
    assert cases["cross-tenant-attack-07"]["baseline_score"] == 0.0
    assert cases["cross-tenant-attack-07"]["candidate_score"] == 1.0
    assert cases["normal-lookup-12"]["baseline_score"] == 1.0
    assert cases["normal-lookup-12"]["candidate_score"] == 1.0
    assert all(case["verdict"] == "pass" for case in payload["cases"])


def test_evopr_replay_cli_writes_measured_results(tmp_path):
    output = tmp_path / "replay.json"
    result = CliRunner().invoke(
        evo_cli,
        ["replay", "examples/replay_suite.json", "--out", str(output)],
    )

    assert result.exit_code == 0, result.output
    assert "Executed 3 replay cases" in result.output
    assert output.exists()
    assert '"candidate_score": 1.0' in output.read_text(encoding="utf-8")


def test_capability_audit_is_explicit_about_unimplemented_features():
    report = capability_report()
    by_id = {item["id"]: item for item in report["capabilities"]}

    assert by_id["command-replay"]["status"] == "tested"
    assert by_id["playground"]["status"] == "demo"
    assert by_id["causal-selector"]["status"] == "planned"
    assert by_id["online-rollout"]["status"] == "planned"


def test_evopr_audit_cli_reports_truth_table():
    result = CliRunner().invoke(evo_cli, ["audit"])

    assert result.exit_code == 0, result.output
    assert "[TESTED ] Deterministic baseline/candidate command replay" in result.output
    assert "[DEMO   ] Interactive causal playground" in result.output
    assert "[PLANNED] Automatic causal hypothesis generation and falsification" in result.output
