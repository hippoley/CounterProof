import json
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
    ProbeSpec,
    ReplayResult,
)
from skill_factory.evolution.replay import run_replay_manifest, serialize_replays
from skill_factory.evolution.report import render_evolution_pr
from skill_factory.evolution.trace import compile_trace, load_trace


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
    assert by_id["trace-ingestion"]["status"] == "tested"
    assert by_id["one-command-proof"]["status"] == "tested"
    assert by_id["causal-selector"]["status"] == "partial"
    assert by_id["online-rollout"]["status"] == "planned"


def test_evopr_audit_cli_reports_truth_table():
    result = CliRunner().invoke(evo_cli, ["audit"])

    assert result.exit_code == 0, result.output
    assert "[TESTED ] Deterministic baseline/candidate command replay" in result.output
    assert "[DEMO   ] Interactive causal playground" in result.output
    assert "[TESTED ] Generic JSON / JSONL trace ingestion" in result.output
    assert "[PARTIAL] Heuristic causal hypothesis proposals" in result.output


def test_committed_capability_json_matches_runtime_manifest():
    committed = json.loads(Path("site/data/capabilities.json").read_text(encoding="utf-8"))
    assert committed == capability_report()


def test_frontend_contract_contains_required_interaction_targets():
    html = Path("site/index.html").read_text(encoding="utf-8")
    js = Path("site/app.js").read_text(encoding="utf-8")

    for element_id in (
        "caseReel",
        "hypothesisLenses",
        "spliceBtn",
        "worldSvg",
        "runProofBtn",
        "proofResult",
        "promoteBtn",
        "rollbackBtn",
        "capabilityGrid",
    ):
        assert f'id="{element_id}"' in html

    for handler in ("spliceWorld", "runProof", "acceptMutation", "rollback"):
        assert handler in js


def test_build_can_attach_measured_replay_without_manual_json_copy(tmp_path):
    output = tmp_path / "measured.md"
    result = CliRunner().invoke(
        evo_cli,
        [
            "build",
            "examples/evolution_pr.json",
            "--replay-manifest",
            "examples/replay_suite.json",
            "--out",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    rendered = output.read_text(encoding="utf-8")
    assert "failure-418" in rendered
    assert "cross-tenant-attack-07" in rendered
    assert "normal-lookup-12" in rendered
    assert "Eligible for promotion." in rendered


def test_explicit_replay_failure_blocks_promotion_even_with_positive_score_delta():
    candidate = CandidateMutation(
        id="c-fail",
        surface="policy",
        title="bad candidate",
        hypothesis_id="h1",
        behavior_diff="before -> after",
        replay_results=(
            ReplayResult("case", "regression", "fail", 0.0, 0.8),
        ),
    )
    assert candidate.mean_delta == 0.8
    assert candidate.failure_count == 1
    assert candidate.eligible_for_promotion is False


def test_replay_scores_must_be_normalized():
    with pytest.raises(ValueError):
        ReplayResult("case", "regression", "pass", 0.0, 1.2)


def test_packet_rejects_dangling_hypothesis_reference():
    with pytest.raises(ValueError):
        EvolutionPacket(
            packet_id="broken",
            agent="agent",
            failure_summary="failure",
            decision_capsule="capsule",
            outcome_receipt="receipt",
            hypotheses=(),
            candidates=(
                CandidateMutation(
                    id="c1",
                    surface="policy",
                    title="guard",
                    hypothesis_id="missing",
                    behavior_diff="before -> after",
                ),
            ),
        )


def test_packet_rejects_missing_selected_candidate():
    with pytest.raises(ValueError):
        EvolutionPacket(
            packet_id="broken",
            agent="agent",
            failure_summary="failure",
            decision_capsule="capsule",
            outcome_receipt="receipt",
            hypotheses=(
                Hypothesis(
                    id="h1",
                    mechanism="mechanism",
                    target_surface="policy",
                ),
            ),
            candidates=(),
            selected_candidate_id="missing",
        )


def test_replay_case_cwd_cannot_escape_declared_root(tmp_path):
    manifest = tmp_path / "suite.json"
    manifest.write_text(
        json.dumps(
            {
                "root": ".",
                "cases": [
                    {
                        "case_id": "escape",
                        "suite": "security",
                        "cwd": "..",
                        "baseline": ["python", "-c", "raise SystemExit(0)"],
                        "candidate": ["python", "-c", "raise SystemExit(0)"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="escapes declared root"):
        run_replay_manifest(manifest)


def test_trace_compiler_extracts_tenant_failure_without_manual_packet():
    trace = load_trace(Path("examples/traces/tenant_failure.json"))
    packet = compile_trace(trace)

    assert packet.packet_id == "evo-tenant-scope-418"
    assert packet.failure_summary == (
        "Agent queried tenant data before validating tenant scope."
    )
    assert len(packet.evidence) == 2
    assert packet.hypotheses[0].target_surface == "policy"
    assert packet.hypotheses[0].uncertainty <= 0.05
    assert packet.candidates[0].surface == "policy"
    assert len(packet.probes) == len(packet.hypotheses)
    assert packet.probes[0].hypothesis_id == packet.hypotheses[0].id
    assert "execution precondition" in packet.probes[0].intervention
    assert packet.metadata["compiler"] == "trace-heuristic-v0.1"
    assert packet.selected_candidate_id is None


def test_trace_compiler_generalizes_to_homeai_mid_utterance_correction():
    trace = load_trace(Path("examples/traces/homeai_correction.json"))
    packet = compile_trace(trace)

    surfaces = [hypothesis.target_surface for hypothesis in packet.hypotheses]
    assert surfaces[0] == "policy"
    assert "skill" in surfaces
    assert "memory" in surfaces
    assert "不对，卧室那个" in packet.outcome_receipt
    assert "semantic_state" in packet.decision_capsule


def test_jsonl_trace_loader_supports_stream_exports(tmp_path):
    trace_file = tmp_path / "trace.jsonl"
    trace_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "trace_meta",
                        "trace_id": "stream-1",
                        "agent": "stream-agent",
                        "task": "stream task",
                    }
                ),
                json.dumps(
                    {
                        "type": "decision",
                        "goal": "act",
                        "world_state": {"state": "provisional"},
                        "selected_action": "execute",
                        "guards": {"ready": False},
                    }
                ),
                json.dumps(
                    {
                        "type": "human_correction",
                        "text": "wait until final",
                        "surface_hint": "policy",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    trace = load_trace(trace_file)
    packet = compile_trace(trace)
    assert trace["trace_id"] == "stream-1"
    assert packet.hypotheses[0].target_surface == "policy"


def test_evopr_ingest_cli_builds_packet_from_raw_trace(tmp_path):
    output = tmp_path / "packet.json"
    result = CliRunner().invoke(
        evo_cli,
        [
            "ingest",
            "examples/traces/tenant_failure.json",
            "--surface",
            "policy",
            "--out",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    raw = json.loads(output.read_text(encoding="utf-8"))
    assert raw["selected_candidate_id"] == "C1"
    assert raw["metadata"]["source_trace_id"] == "tenant-scope-418"
    assert raw["hypotheses"][0]["target_surface"] == "policy"
    assert raw["probes"][0]["hypothesis_id"] == raw["hypotheses"][0]["id"]


def test_evopr_prove_runs_trace_to_measured_behavior_proof(tmp_path):
    output = tmp_path / "proof.md"
    packet_output = tmp_path / "packet.json"
    result = CliRunner().invoke(
        evo_cli,
        [
            "prove",
            "examples/traces/tenant_failure.json",
            "--replay-manifest",
            "examples/replay_suite.json",
            "--surface",
            "policy",
            "--packet-out",
            str(packet_output),
            "--out",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    rendered = output.read_text(encoding="utf-8")
    measured = json.loads(packet_output.read_text(encoding="utf-8"))

    assert "## Provenance" in rendered
    assert "## 3b. Discriminating probes" in rendered
    assert "selection mode:** explicit-surface" in rendered
    assert "failure-418" in rendered
    assert "Eligible for promotion." in rendered
    selected = next(
        candidate
        for candidate in measured["candidates"]
        if candidate["id"] == measured["selected_candidate_id"]
    )
    assert len(selected["replay_results"]) == 3
    assert all(item["verdict"] == "pass" for item in selected["replay_results"])


def test_report_rejects_explicit_failed_replay_even_without_score_regression():
    candidate = CandidateMutation(
        id="c-fail",
        surface="policy",
        title="failed replay",
        hypothesis_id="h1",
        behavior_diff="before -> after",
        replay_results=(ReplayResult("case", "holdout", "fail", 0.0, 0.8),),
    )
    packet = EvolutionPacket(
        packet_id="evo-fail",
        agent="agent",
        failure_summary="failure",
        decision_capsule="capsule",
        outcome_receipt="receipt",
        hypotheses=(
            Hypothesis(
                id="h1",
                mechanism="mechanism",
                target_surface="policy",
            ),
        ),
        candidates=(candidate,),
    )

    rendered = render_evolution_pr(packet)
    assert "**REJECT**" in rendered


def test_packet_rejects_probe_for_unknown_hypothesis():
    with pytest.raises(ValueError):
        EvolutionPacket(
            packet_id="broken-probe",
            agent="agent",
            failure_summary="failure",
            decision_capsule="capsule",
            outcome_receipt="receipt",
            probes=(
                ProbeSpec(
                    id="P1",
                    hypothesis_id="missing",
                    intervention="change one thing",
                    expected_if_true="failure disappears",
                    falsifier="failure survives",
                ),
            ),
        )
