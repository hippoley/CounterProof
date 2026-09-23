import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from skill_factory.evolution.adapter_binding import bind_probe_adapter
from skill_factory.evolution.capabilities import capability_report
from skill_factory.evolution.cli import cli as evo_cli
from skill_factory.evolution.discriminate import (
    DiscriminationRun,
    VariantEvidence,
    discrimination_to_dict,
    render_discrimination_markdown,
    run_discrimination_manifest,
)
from skill_factory.evolution.models import (
    CandidateMutation,
    Evidence,
    EvolutionPacket,
    Hypothesis,
    ProbeSpec,
    ReplayResult,
)
from skill_factory.evolution.probe_planner import (
    build_probe_scaffold,
    plan_next_probes,
    render_probe_plan,
)
from skill_factory.evolution.receipt import file_sha256
from skill_factory.evolution.replay import (
    CommandOutcome,
    interpret_command_outcome,
    parse_structured_probe_result,
    run_replay_manifest,
    serialize_replays,
)
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


def test_active_discrimination_finds_only_policy_survivor():
    run = run_discrimination_manifest(
        Path("examples/discrimination_suite.json"),
        surfaces=("policy", "skill", "prompt"),
    )

    by_surface = {item.surface: item for item in run.variants}
    assert run.discriminated_surface == "policy"
    assert by_surface["policy"].status == "survived"
    assert by_surface["policy"].failure_count == 0
    assert by_surface["skill"].status == "falsified"
    assert by_surface["prompt"].status == "falsified"
    assert by_surface["skill"].failure_count == 1
    assert by_surface["prompt"].failure_count == 1


def test_discrimination_report_never_claims_unique_causal_truth():
    run = run_discrimination_manifest(
        Path("examples/discrimination_suite.json"),
        surfaces=("policy", "skill", "prompt"),
    )
    rendered = render_discrimination_markdown(
        run,
        mechanisms={
            "policy": "commit gate missing",
            "skill": "instruction missing",
            "prompt": "prompt underspecified",
        },
    )

    assert "Only **policy** survived" in rendered
    assert "does not establish unique causal truth" in rendered
    assert "cross-tenant-attack-07" in rendered


def test_discrimination_keeps_multiple_survivors_ambiguous():
    perfect = (
        ReplayResult("failure", "regression", "pass", 0.0, 1.0),
        ReplayResult("normal", "holdout", "pass", 1.0, 1.0),
    )
    run = DiscriminationRun(
        variants=(
            VariantEvidence(surface="policy", replays=perfect, outcomes=()),
            VariantEvidence(surface="skill", replays=perfect, outcomes=()),
        )
    )

    assert run.discriminated_surface is None
    assert {item.surface for item in run.survivors} == {"policy", "skill"}
    rendered = render_discrimination_markdown(run)
    assert "Multiple hypotheses survived" in rendered
    assert "add a case where their predicted behaviors differ" in rendered


def test_discrimination_can_reject_the_entire_candidate_set():
    failed = (
        ReplayResult("failure", "regression", "fail", 0.0, 0.0),
    )
    run = DiscriminationRun(
        variants=(
            VariantEvidence(surface="policy", replays=failed, outcomes=()),
            VariantEvidence(surface="skill", replays=failed, outcomes=()),
        )
    )

    assert run.discriminated_surface is None
    assert run.survivors == ()
    assert "No tested hypothesis survived" in render_discrimination_markdown(run)


def test_evopr_discriminate_cli_runs_same_cases_across_surfaces(tmp_path):
    output = tmp_path / "matrix.md"
    payload = tmp_path / "matrix.json"
    result = CliRunner().invoke(
        evo_cli,
        [
            "discriminate",
            "examples/traces/tenant_failure.json",
            "--experiment-manifest",
            "examples/discrimination_suite.json",
            "--surface",
            "policy",
            "--surface",
            "skill",
            "--surface",
            "prompt",
            "--out",
            str(output),
            "--json-out",
            str(payload),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "discriminated 'policy'" in result.output
    assert "not unique causal proof" in result.output
    raw = json.loads(payload.read_text(encoding="utf-8"))
    assert raw["discriminated_surface"] == "policy"
    assert raw["survivors"] == ["policy"]
    assert raw["source_trace_id"] == "tenant-scope-418"
    assert "Only **policy** survived" in output.read_text(encoding="utf-8")


def test_discrimination_rejects_unavailable_surface():
    with pytest.raises(ValueError, match="unavailable"):
        run_discrimination_manifest(
            Path("examples/discrimination_suite.json"),
            surfaces=("router",),
        )


def test_missing_variant_case_is_inconclusive_not_survived(tmp_path):
    manifest = tmp_path / "partial.json"
    manifest.write_text(
        json.dumps(
            {
                "root": ".",
                "cases": [
                    {
                        "case_id": "failure",
                        "baseline": ["python", "-c", "raise SystemExit(1)"],
                        "variants": {
                            "policy": ["python", "-c", "raise SystemExit(0)"],
                        },
                    },
                    {
                        "case_id": "holdout",
                        "baseline": ["python", "-c", "raise SystemExit(0)"],
                        "variants": {
                            "skill": ["python", "-c", "raise SystemExit(0)"],
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    run = run_discrimination_manifest(manifest, surfaces=("policy",))
    policy = run.variants[0]
    assert policy.infra_error_count == 1
    assert policy.status == "inconclusive"
    assert run.discriminated_surface is None


def test_diagnostic_case_identifies_where_candidate_signatures_split():
    run = run_discrimination_manifest(
        Path("examples/discrimination_suite.json"),
        surfaces=("policy", "skill", "prompt"),
    )

    assert run.diagnostic_cases == ("cross-tenant-attack-07",)
    by_surface = {item.surface: item.signature for item in run.variants}
    assert by_surface["policy"] == ("P", "P", "P")
    assert by_surface["skill"] == ("P", "F", "P")
    assert by_surface["prompt"] == ("P", "F", "P")


def test_evopr_evolve_selects_only_unique_survivor_and_attaches_replays(tmp_path):
    output = tmp_path / "review.md"
    packet_output = tmp_path / "packet.json"
    matrix_output = tmp_path / "matrix.md"
    result = CliRunner().invoke(
        evo_cli,
        [
            "evolve",
            "examples/traces/tenant_failure.json",
            "--experiment-manifest",
            "examples/discrimination_suite.json",
            "--surface",
            "policy",
            "--surface",
            "skill",
            "--surface",
            "prompt",
            "--out",
            str(output),
            "--packet-out",
            str(packet_output),
            "--matrix-out",
            str(matrix_output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Unique survivor: policy" in result.output
    packet = json.loads(packet_output.read_text(encoding="utf-8"))
    assert packet["selected_candidate_id"] == "C1"
    assert packet["metadata"]["selection_mode"] == "active-discrimination"
    assert packet["metadata"]["discrimination_result"] == "unique-survivor:policy"
    selected = next(
        item
        for item in packet["candidates"]
        if item["id"] == packet["selected_candidate_id"]
    )
    assert len(selected["replay_results"]) == 3
    review = output.read_text(encoding="utf-8")
    assert "Eligible for promotion." in review
    assert "EvoPR Discrimination Matrix" in review
    assert "cross-tenant-attack-07" in matrix_output.read_text(encoding="utf-8")


def test_evopr_evolve_refuses_automatic_selection_when_survivors_are_ambiguous(
    tmp_path,
):
    fixture = tmp_path / "ambiguous.py"
    fixture.write_text(
        "import sys\nraise SystemExit(0 if sys.argv[1] != 'baseline' else 1)\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "ambiguous.json"
    manifest.write_text(
        json.dumps(
            {
                "root": ".",
                "cases": [
                    {
                        "case_id": "failure",
                        "baseline": ["python", str(fixture), "baseline"],
                        "variants": {
                            "policy": ["python", str(fixture), "policy"],
                            "skill": ["python", str(fixture), "skill"],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "review.md"
    packet_output = tmp_path / "packet.json"
    result = CliRunner().invoke(
        evo_cli,
        [
            "evolve",
            "examples/traces/tenant_failure.json",
            "--experiment-manifest",
            str(manifest),
            "--surface",
            "policy",
            "--surface",
            "skill",
            "--out",
            str(output),
            "--packet-out",
            str(packet_output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "No automatic selection: multiple eligible interventions survived" in result.output
    packet = json.loads(packet_output.read_text(encoding="utf-8"))
    assert packet["selected_candidate_id"] is None
    assert packet["metadata"]["discrimination_result"] == "ambiguous"
    assert packet["metadata"]["runtime_survivors"] == "policy,skill"
    assert packet["metadata"]["eligible_survivors"] == "policy,skill"
    assert packet["metadata"]["prediction_blocked_survivors"] == ""
    review = output.read_text(encoding="utf-8")
    assert "Multiple hypotheses survived" in review
    assert "Eligible for promotion." not in review


def test_next_probe_planner_targets_unresolved_survivor_pair():
    trace = load_trace(Path("examples/traces/tenant_failure.json"))
    packet = compile_trace(trace)
    run = run_discrimination_manifest(
        Path("examples/ambiguous_discrimination_suite.json"),
        surfaces=("policy", "skill"),
    )

    assert run.discriminated_surface is None
    assert run.unresolved_pairs == (("policy", "skill"),)

    suggestions = plan_next_probes(packet, run)
    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion.left_surface == "policy"
    assert suggestion.right_surface == "skill"
    assert "execution precondition / commit gate" in suggestion.vary
    assert "learned instruction / demonstrations" in suggestion.vary

    rendered = render_probe_plan(suggestions)
    assert "Separate policy from skill" in rendered
    assert "experiment-design suggestion" in rendered
    assert "not an executable test case" in rendered


def test_next_probe_planner_returns_nothing_after_unique_discrimination():
    trace = load_trace(Path("examples/traces/tenant_failure.json"))
    packet = compile_trace(trace)
    run = run_discrimination_manifest(
        Path("examples/discrimination_suite.json"),
        surfaces=("policy", "skill", "prompt"),
    )

    assert run.discriminated_surface == "policy"
    assert plan_next_probes(packet, run) == ()


def test_evopr_evolve_writes_next_probe_plan_when_ambiguous(tmp_path):
    output = tmp_path / "review.md"
    packet_output = tmp_path / "packet.json"
    probe_output = tmp_path / "next_probe.md"
    result = CliRunner().invoke(
        evo_cli,
        [
            "evolve",
            "examples/traces/tenant_failure.json",
            "--experiment-manifest",
            "examples/ambiguous_discrimination_suite.json",
            "--surface",
            "policy",
            "--surface",
            "skill",
            "--out",
            str(output),
            "--packet-out",
            str(packet_output),
            "--probe-plan-out",
            str(probe_output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "No automatic selection: multiple eligible interventions survived" in result.output
    assert "Next discriminating probe planned for: policy vs skill" in result.output

    packet = json.loads(packet_output.read_text(encoding="utf-8"))
    assert packet["selected_candidate_id"] is None
    assert packet["metadata"]["discrimination_result"] == "ambiguous"

    probe_text = probe_output.read_text(encoding="utf-8")
    assert "Separate policy from skill" in probe_text
    assert "execution precondition / commit gate" in probe_text
    assert "learned instruction / demonstrations" in probe_text

    review = output.read_text(encoding="utf-8")
    assert "EvoPR Next Probe Plan" in review
    assert "Eligible for promotion." not in review


def test_discriminate_json_exposes_next_probe_suggestions_when_ambiguous(tmp_path):
    output = tmp_path / "matrix.md"
    payload = tmp_path / "matrix.json"
    result = CliRunner().invoke(
        evo_cli,
        [
            "discriminate",
            "examples/traces/tenant_failure.json",
            "--experiment-manifest",
            "examples/ambiguous_discrimination_suite.json",
            "--surface",
            "policy",
            "--surface",
            "skill",
            "--out",
            str(output),
            "--json-out",
            str(payload),
        ],
    )

    assert result.exit_code == 0, result.output
    raw = json.loads(payload.read_text(encoding="utf-8"))
    assert raw["discriminated_surface"] is None
    assert raw["survivors"] == ["policy", "skill"]
    assert len(raw["next_probe_suggestions"]) == 1
    assert raw["next_probe_suggestions"][0]["title"] == "Separate policy from skill"


def test_preregistered_predictions_are_scored_before_selection():
    run = run_discrimination_manifest(
        Path("examples/discrimination_suite.json"),
        surfaces=("policy", "skill", "prompt"),
    )
    by_surface = {item.surface: item for item in run.variants}

    assert run.has_preregistered_predictions is True
    assert by_surface["policy"].expected_signature == ("P", "P", "P")
    assert by_surface["policy"].prediction_status == "supported"
    assert by_surface["policy"].prediction_mismatch_count == 0

    assert by_surface["skill"].expected_signature == ("P", "P", "P")
    assert by_surface["skill"].signature == ("P", "F", "P")
    assert by_surface["skill"].prediction_status == "contradicted"
    assert by_surface["skill"].prediction_mismatch_count == 1

    assert run.discriminated_surface == "policy"
    assert tuple(item.surface for item in run.eligible_survivors) == ("policy",)


def test_surviving_runtime_variant_with_wrong_preregistered_prediction_is_not_selectable():
    replays = (
        ReplayResult("failure", "regression", "pass", 0.0, 1.0),
        ReplayResult("normal", "holdout", "pass", 1.0, 1.0),
    )
    variant = VariantEvidence(
        surface="policy",
        replays=replays,
        outcomes=(),
        predictions=("fail", "pass"),
    )
    run = DiscriminationRun(variants=(variant,))

    assert variant.status == "survived"
    assert variant.prediction_status == "contradicted"
    assert variant.prediction_mismatch_count == 1
    assert run.survivors == (variant,)
    assert run.eligible_survivors == ()
    assert run.prediction_blocked_survivors == (variant,)
    assert run.selection_state == "prediction-blocked"
    assert run.discriminated_surface is None


def test_ambiguous_preregistered_survivors_stay_ambiguous():
    run = run_discrimination_manifest(
        Path("examples/ambiguous_discrimination_suite.json"),
        surfaces=("policy", "skill"),
    )
    by_surface = {item.surface: item for item in run.variants}

    assert by_surface["policy"].prediction_status == "supported"
    assert by_surface["skill"].prediction_status == "supported"
    assert tuple(item.surface for item in run.eligible_survivors) == (
        "policy",
        "skill",
    )
    assert run.discriminated_surface is None
    assert run.unresolved_pairs == (("policy", "skill"),)


def test_discrimination_payload_exposes_preregistered_prediction_evidence():
    run = run_discrimination_manifest(
        Path("examples/discrimination_suite.json"),
        surfaces=("policy", "skill", "prompt"),
    )
    payload = discrimination_to_dict(run)
    by_surface = {item["surface"]: item for item in payload["variants"]}

    assert payload["has_preregistered_predictions"] is True
    assert payload["selection_state"] == "unique-survivor"
    assert payload["eligible_survivors"] == ["policy"]
    assert by_surface["policy"]["prediction_status"] == "supported"
    assert by_surface["skill"]["prediction_status"] == "contradicted"
    assert by_surface["skill"]["prediction_mismatches"] == 1


def test_evopr_evolve_can_emit_reproducible_proof_receipt(tmp_path):
    review = tmp_path / "review.md"
    receipt = tmp_path / "receipt.json"
    result = CliRunner().invoke(
        evo_cli,
        [
            "evolve",
            "examples/traces/tenant_failure.json",
            "--experiment-manifest",
            "examples/discrimination_suite.json",
            "--surface",
            "policy",
            "--surface",
            "skill",
            "--surface",
            "prompt",
            "--out",
            str(review),
            "--receipt-out",
            str(receipt),
        ],
    )

    assert result.exit_code == 0, result.output
    raw = json.loads(receipt.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1
    assert raw["discriminated_surface"] == "policy"
    assert raw["selected_candidate_id"] == "C1"
    assert raw["trace"]["sha256"] == file_sha256(
        Path("examples/traces/tenant_failure.json")
    )
    assert raw["experiment"]["sha256"] == file_sha256(
        Path("examples/discrimination_suite.json")
    )
    assert raw["runtime_signatures"]["policy"] == ["P", "P", "P"]
    assert raw["expected_signatures"]["policy"] == ["P", "P", "P"]
    assert raw["prediction_status"]["skill"] == "contradicted"


def test_verify_receipt_cli_accepts_unchanged_sources(tmp_path):
    receipt = tmp_path / "receipt.json"
    build = CliRunner().invoke(
        evo_cli,
        [
            "evolve",
            "examples/traces/tenant_failure.json",
            "--experiment-manifest",
            "examples/discrimination_suite.json",
            "--surface",
            "policy",
            "--surface",
            "skill",
            "--surface",
            "prompt",
            "--out",
            str(tmp_path / "review.md"),
            "--receipt-out",
            str(receipt),
        ],
    )
    assert build.exit_code == 0, build.output

    verify = CliRunner().invoke(
        evo_cli,
        ["verify-receipt", str(receipt)],
    )
    assert verify.exit_code == 0, verify.output
    assert "VERIFIED" in verify.output


def test_verify_receipt_cli_rejects_changed_trace(tmp_path):
    receipt = tmp_path / "receipt.json"
    build = CliRunner().invoke(
        evo_cli,
        [
            "evolve",
            "examples/traces/tenant_failure.json",
            "--experiment-manifest",
            "examples/discrimination_suite.json",
            "--surface",
            "policy",
            "--surface",
            "skill",
            "--surface",
            "prompt",
            "--out",
            str(tmp_path / "review.md"),
            "--receipt-out",
            str(receipt),
        ],
    )
    assert build.exit_code == 0, build.output

    changed_trace = tmp_path / "changed_trace.json"
    original = json.loads(
        Path("examples/traces/tenant_failure.json").read_text(encoding="utf-8")
    )
    original["task"] = original["task"] + " changed"
    changed_trace.write_text(
        json.dumps(original, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    verify = CliRunner().invoke(
        evo_cli,
        [
            "verify-receipt",
            str(receipt),
            "--trace",
            str(changed_trace),
            "--experiment-manifest",
            "examples/discrimination_suite.json",
        ],
    )
    assert verify.exit_code != 0
    assert "trace hash mismatch" in verify.output


def test_evopr_evolve_reports_prediction_blocked_instead_of_ambiguous(tmp_path):
    manifest = tmp_path / "prediction_blocked.json"
    manifest.write_text(
        json.dumps(
            {
                "root": ".",
                "cases": [
                    {
                        "case_id": "failure",
                        "baseline": ["python", "-c", "raise SystemExit(1)"],
                        "variants": {
                            "policy": {
                                "argv": ["python", "-c", "raise SystemExit(0)"],
                                "expect": "fail",
                            }
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    packet_out = tmp_path / "packet.json"
    review_out = tmp_path / "review.md"

    result = CliRunner().invoke(
        evo_cli,
        [
            "evolve",
            "examples/traces/tenant_failure.json",
            "--experiment-manifest",
            str(manifest),
            "--surface",
            "policy",
            "--out",
            str(review_out),
            "--packet-out",
            str(packet_out),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "blocked by their pre-registered prediction contract" in result.output
    assert "multiple eligible interventions survived" not in result.output

    packet = json.loads(packet_out.read_text(encoding="utf-8"))
    assert packet["selected_candidate_id"] is None
    assert packet["metadata"]["discrimination_result"] == "prediction-blocked"
    assert packet["metadata"]["prediction_blocked_survivors"] == "policy"

    review = review_out.read_text(encoding="utf-8")
    assert "were blocked from selection" in review
    assert "AMBIGUOUS" not in review


def test_env_probe_adapter_matches_command_matrix_behavior():
    run = run_discrimination_manifest(
        Path("examples/adapter_discrimination_suite.json"),
        surfaces=("policy", "skill", "prompt"),
    )
    by_surface = {item.surface: item for item in run.variants}

    assert run.discriminated_surface == "policy"
    assert by_surface["policy"].signature == ("P", "P", "P")
    assert by_surface["policy"].prediction_status == "supported"
    assert by_surface["skill"].signature == ("P", "F", "P")
    assert by_surface["skill"].prediction_status == "contradicted"
    assert by_surface["prompt"].signature == ("P", "F", "P")

    first_outcome = by_surface["policy"].outcomes[0]
    payload = json.loads(first_outcome.stdout)
    assert payload["case_id"] == "failure-418"
    assert payload["variant"] == "policy"
    assert payload["payload"] == {"attack": False, "normal": False}


def test_discrimination_manifest_refuses_draft_execution(tmp_path):
    manifest = tmp_path / "draft.json"
    manifest.write_text(
        json.dumps(
            {
                "status": "draft",
                "adapter": ["python", "-c", "raise SystemExit(0)"],
                "cases": [
                    {
                        "case_id": "draft-case",
                        "variants": {
                            "policy": {"expect": "pass"}
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="status is 'draft'"):
        run_discrimination_manifest(manifest, surfaces=("policy",))


def test_probe_scaffold_crosses_predictions_and_stays_draft():
    trace = load_trace(Path("examples/traces/tenant_failure.json"))
    packet = compile_trace(trace)
    run = run_discrimination_manifest(
        Path("examples/ambiguous_discrimination_suite.json"),
        surfaces=("policy", "skill"),
    )
    suggestions = plan_next_probes(packet, run)
    scaffold = build_probe_scaffold(packet, suggestions)

    assert scaffold["status"] == "draft"
    assert scaffold["review_required"] is True
    assert scaffold["adapter"] == ["TODO_REPLACE_WITH_ADAPTER"]
    assert len(scaffold["cases"]) == 2

    left_case, right_case = scaffold["cases"]
    assert left_case["payload"]["design"] == "isolate-left-lever"
    assert left_case["variants"]["policy"]["expect"] == "pass"
    assert left_case["variants"]["skill"]["expect"] == "fail"

    assert right_case["payload"]["design"] == "isolate-right-lever"
    assert right_case["variants"]["policy"]["expect"] == "fail"
    assert right_case["variants"]["skill"]["expect"] == "pass"


def test_generated_probe_scaffold_cannot_execute_until_reviewed(tmp_path):
    trace = load_trace(Path("examples/traces/tenant_failure.json"))
    packet = compile_trace(trace)
    run = run_discrimination_manifest(
        Path("examples/ambiguous_discrimination_suite.json"),
        surfaces=("policy", "skill"),
    )
    scaffold = build_probe_scaffold(packet, plan_next_probes(packet, run))
    path = tmp_path / "draft_probe.json"
    path.write_text(
        json.dumps(scaffold, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="status is 'draft'"):
        run_discrimination_manifest(path, surfaces=("policy", "skill"))


def test_evopr_evolve_writes_probe_scaffold_for_ambiguous_case(tmp_path):
    review = tmp_path / "review.md"
    scaffold_out = tmp_path / "next_experiment.json"
    result = CliRunner().invoke(
        evo_cli,
        [
            "evolve",
            "examples/traces/tenant_failure.json",
            "--experiment-manifest",
            "examples/ambiguous_discrimination_suite.json",
            "--surface",
            "policy",
            "--surface",
            "skill",
            "--out",
            str(review),
            "--probe-scaffold-out",
            str(scaffold_out),
        ],
    )

    assert result.exit_code == 0, result.output
    scaffold = json.loads(scaffold_out.read_text(encoding="utf-8"))
    assert scaffold["status"] == "draft"
    assert scaffold["source_trace_id"] == "tenant-scope-418"
    assert len(scaffold["cases"]) == 2
    assert scaffold["cases"][0]["variants"]["policy"]["expect"] == "pass"
    assert scaffold["cases"][1]["variants"]["skill"]["expect"] == "pass"


def test_ready_scaffold_still_rejects_unconfigured_adapter_placeholder(tmp_path):
    trace = load_trace(Path("examples/traces/tenant_failure.json"))
    packet = compile_trace(trace)
    run = run_discrimination_manifest(
        Path("examples/ambiguous_discrimination_suite.json"),
        surfaces=("policy", "skill"),
    )
    scaffold = build_probe_scaffold(packet, plan_next_probes(packet, run))
    scaffold["status"] = "ready"
    path = tmp_path / "ready_but_unconfigured.json"
    path.write_text(
        json.dumps(scaffold, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="adapter placeholder has not been replaced"):
        run_discrimination_manifest(path, surfaces=("policy", "skill"))


def test_bind_probe_adapter_records_review_and_makes_scaffold_ready():
    trace = load_trace(Path("examples/traces/tenant_failure.json"))
    packet = compile_trace(trace)
    run = run_discrimination_manifest(
        Path("examples/ambiguous_discrimination_suite.json"),
        surfaces=("policy", "skill"),
    )
    scaffold = build_probe_scaffold(packet, plan_next_probes(packet, run))

    bound = bind_probe_adapter(
        scaffold,
        adapter=("python", "my_probe_adapter.py"),
        reviewed_by="ci-reviewer",
        review_note="Reviewed fixture semantics and intervention isolation.",
    )

    assert bound["status"] == "ready"
    assert bound["review_required"] is False
    assert bound["adapter"] == ["python", "my_probe_adapter.py"]
    assert bound["review"]["reviewed_by"] == "ci-reviewer"
    assert bound["review"]["decision"] == "approved-for-execution"
    assert scaffold["status"] == "draft"
    assert scaffold["adapter"] == ["TODO_REPLACE_WITH_ADAPTER"]


@pytest.mark.parametrize(
    ("adapter", "reviewed_by", "review_note", "message"),
    [
        (("TODO_REPLACE_WITH_ADAPTER",), "reviewer", "ok", "placeholder"),
        ((), "reviewer", "ok", "one or more"),
        (("python", "adapter.py"), "", "ok", "reviewed_by"),
        (("python", "adapter.py"), "reviewer", "", "review_note"),
    ],
)
def test_bind_probe_adapter_rejects_unreviewed_or_placeholder_binding(
    adapter,
    reviewed_by,
    review_note,
    message,
):
    scaffold = {
        "status": "draft",
        "review_required": True,
        "adapter": ["TODO_REPLACE_WITH_ADAPTER"],
        "cases": [{"case_id": "probe-1", "variants": {"policy": {"expect": "pass"}}}],
    }

    with pytest.raises(ValueError, match=message):
        bind_probe_adapter(
            scaffold,
            adapter=adapter,
            reviewed_by=reviewed_by,
            review_note=review_note,
        )


def test_bind_probe_adapter_cli_writes_ready_reviewed_manifest(tmp_path):
    trace = load_trace(Path("examples/traces/tenant_failure.json"))
    packet = compile_trace(trace)
    run = run_discrimination_manifest(
        Path("examples/ambiguous_discrimination_suite.json"),
        surfaces=("policy", "skill"),
    )
    scaffold = build_probe_scaffold(packet, plan_next_probes(packet, run))
    draft = tmp_path / "draft.json"
    ready = tmp_path / "ready.json"
    draft.write_text(
        json.dumps(scaffold, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        evo_cli,
        [
            "bind-probe-adapter",
            str(draft),
            "--adapter",
            "python",
            "--adapter",
            "my_probe_adapter.py",
            "--reviewed-by",
            "ci-reviewer",
            "--review-note",
            "Reviewed case semantics.",
            "--out",
            str(ready),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "status=ready" in result.output
    raw = json.loads(ready.read_text(encoding="utf-8"))
    assert raw["status"] == "ready"
    assert raw["adapter"] == ["python", "my_probe_adapter.py"]
    assert raw["review"]["note"] == "Reviewed case semantics."


def test_diagnostic_fail_is_evidence_not_fitness_regression():
    variant = VariantEvidence(
        surface="policy",
        replays=(
            ReplayResult("diag-pass", "diagnostic", "pass", 0.0, 1.0),
            ReplayResult("diag-fail", "diagnostic", "fail", 0.0, 0.0),
        ),
        outcomes=(),
        predictions=("pass", "fail"),
        roles=("diagnostic", "diagnostic"),
    )
    run = DiscriminationRun(variants=(variant,))

    assert variant.failure_count == 0
    assert variant.regression_count == 0
    assert variant.mean_delta == 0.0
    assert variant.prediction_status == "supported"
    assert variant.status == "diagnostic-only"
    assert run.selection_state == "diagnostic-only"
    assert run.discriminated_surface is None


def test_generated_probe_scaffold_marks_crossed_cases_diagnostic():
    trace = load_trace(Path("examples/traces/tenant_failure.json"))
    packet = compile_trace(trace)
    run = run_discrimination_manifest(
        Path("examples/ambiguous_discrimination_suite.json"),
        surfaces=("policy", "skill"),
    )
    scaffold = build_probe_scaffold(packet, plan_next_probes(packet, run))

    assert scaffold["cases"]
    assert all(case["role"] == "diagnostic" for case in scaffold["cases"])


def test_reviewed_crossed_probe_executes_as_diagnostic_only(tmp_path):
    trace = load_trace(Path("examples/traces/tenant_failure.json"))
    packet = compile_trace(trace)
    ambiguous = run_discrimination_manifest(
        Path("examples/ambiguous_discrimination_suite.json"),
        surfaces=("policy", "skill"),
    )
    scaffold = build_probe_scaffold(packet, plan_next_probes(packet, ambiguous))
    ready = bind_probe_adapter(
        scaffold,
        adapter=("python", str(Path("examples/replay/cross_probe_adapter.py").resolve())),
        reviewed_by="fixture-reviewer",
        review_note="Fixture-only adapter validates crossed-probe plumbing.",
    )
    path = tmp_path / "ready.json"
    path.write_text(
        json.dumps(ready, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    run = run_discrimination_manifest(path, surfaces=("policy", "skill"))
    by_surface = {item.surface: item for item in run.variants}

    assert run.selection_state == "diagnostic-only"
    assert run.discriminated_surface is None
    assert run.declared_diagnostic_cases
    assert by_surface["policy"].prediction_status == "supported"
    assert by_surface["skill"].prediction_status == "supported"
    assert by_surface["policy"].failure_count == 0
    assert by_surface["skill"].failure_count == 0
    assert by_surface["policy"].status == "diagnostic-only"
    assert by_surface["skill"].status == "diagnostic-only"


def test_discrimination_payload_exposes_case_roles():
    variant = VariantEvidence(
        surface="policy",
        replays=(
            ReplayResult("fitness", "regression", "pass", 0.0, 1.0),
            ReplayResult("diagnostic", "probe", "fail", 0.0, 0.0),
        ),
        outcomes=(),
        predictions=("pass", "fail"),
        roles=("fitness", "diagnostic"),
    )
    payload = discrimination_to_dict(DiscriminationRun(variants=(variant,)))
    item = payload["variants"][0]

    assert item["roles"] == ["fitness", "diagnostic"]
    assert item["fitness_case_count"] == 1
    assert item["diagnostic_case_count"] == 1
    assert payload["declared_diagnostic_cases"] == ["diagnostic"]


def test_parse_structured_probe_result_reads_score_metrics_and_evidence():
    result = parse_structured_probe_result(
        'normal log\nEVOPR_RESULT={"verdict":"pass","score":0.82,'
        '"metrics":{"latency_ms":17},"observations":["stable"],'
        '"artifacts":["artifact://trace/1"]}\n'
    )

    assert result is not None
    assert result.verdict == "pass"
    assert result.score == pytest.approx(0.82)
    assert result.metrics["latency_ms"] == 17
    assert result.observations == ("stable",)
    assert result.artifacts == ("artifact://trace/1",)


def test_json_v1_missing_or_broken_result_is_infrastructure_error():
    missing = CommandOutcome(
        argv=("adapter",),
        returncode=0,
        duration_ms=1,
        stdout="no structured result",
        stderr="",
    )
    broken = CommandOutcome(
        argv=("adapter",),
        returncode=0,
        duration_ms=1,
        stdout='EVOPR_RESULT={"verdict":"pass"',
        stderr="",
        probe_result_error="invalid EVOPR_RESULT JSON",
    )

    assert interpret_command_outcome(
        missing,
        protocol="json-v1",
    ).verdict == "infra_error"
    assert interpret_command_outcome(
        broken,
        protocol="json-v1",
    ).verdict == "infra_error"


def test_structured_discrimination_separates_process_success_from_behavior():
    run = run_discrimination_manifest(
        Path("examples/structured_discrimination_suite.json"),
        surfaces=("policy", "skill", "prompt"),
    )
    by_surface = {item.surface: item for item in run.variants}

    assert run.discriminated_surface == "policy"
    assert run.selection_state == "unique-survivor"

    policy = by_surface["policy"]
    assert policy.signature == ("P", "P", "P")
    assert policy.prediction_status == "supported"
    assert [item.candidate_score for item in policy.replays] == pytest.approx(
        [0.96, 0.94, 0.92]
    )
    assert all(outcome is not None for outcome in policy.outcomes)
    assert all(outcome.returncode == 0 for outcome in policy.outcomes if outcome)

    skill = by_surface["skill"]
    assert skill.signature == ("P", "F", "P")
    assert skill.replays[0].candidate_score == pytest.approx(0.82)
    assert skill.replays[0].verdict == "pass"
    assert skill.replays[1].candidate_score == pytest.approx(0.45)
    assert skill.replays[1].verdict == "fail"
    assert skill.prediction_status == "contradicted"
    assert all(outcome.returncode == 0 for outcome in skill.outcomes if outcome)


def test_structured_discrimination_payload_carries_adapter_evidence():
    run = run_discrimination_manifest(
        Path("examples/structured_discrimination_suite.json"),
        surfaces=("policy", "skill", "prompt"),
    )
    payload = discrimination_to_dict(run)
    by_surface = {item["surface"]: item for item in payload["variants"]}

    policy_results = by_surface["policy"]["probe_results"]
    assert policy_results[0]["verdict"] == "pass"
    assert policy_results[0]["score"] == pytest.approx(0.96)
    assert policy_results[0]["metrics"]["safety_score"] == pytest.approx(0.96)
    assert "scenario=failure" in policy_results[0]["observations"]
    assert policy_results[0]["artifacts"] == [
        "fixture://structured/failure/policy"
    ]


def test_signature_uses_behavior_verdict_not_perfect_score():
    variant = VariantEvidence(
        surface="skill",
        replays=(
            ReplayResult("case", "fitness", "pass", 0.2, 0.82),
        ),
        outcomes=(),
        predictions=("pass",),
        roles=("fitness",),
    )

    assert variant.signature == ("P",)
    assert variant.prediction_status == "supported"
