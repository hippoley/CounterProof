from pathlib import Path

from click.testing import CliRunner

from skill_factory.evolution.cli import cli as evo_cli
from skill_factory.evolution.models import (
    CandidateMutation,
    EvolutionPacket,
    Hypothesis,
    ReplayResult,
)
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
