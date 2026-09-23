"""CLI for Counterproof."""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import click

from .adapter_binding import bind_probe_adapter
from .capabilities import capability_report
from .doctor import doctor_json, render_doctor, run_doctor
from .discriminate import (
    discrimination_to_dict,
    render_discrimination_markdown,
    run_discrimination_manifest,
)
from .integrity import (
    inspect_proof_integrity,
    render_integrity_markdown,
    write_integrity_json,
)
from .onboarding import init_github
from .models import (
    CandidateMutation,
    Evidence,
    EvolutionPacket,
    Hypothesis,
    ProbeSpec,
    ReplayResult,
)
from .probe_planner import build_probe_scaffold, plan_next_probes, render_probe_plan
from .receipt import build_proof_receipt, file_sha256, verify_proof_receipt, write_receipt
from .replay import run_replay_manifest, serialize_replays
from .report import render_evolution_pr
from .trace import compile_trace, load_trace, packet_to_dict, select_candidate
from .witness import render_witness_markdown, run_regression_witness, write_witness_json


def _packet_from_json(raw: dict) -> EvolutionPacket:
    evidence = tuple(Evidence(**item) for item in raw.get("evidence", []))
    hypotheses = tuple(Hypothesis(**item) for item in raw.get("hypotheses", []))
    probes = tuple(ProbeSpec(**item) for item in raw.get("probes", []))

    candidates: list[CandidateMutation] = []
    for source in raw.get("candidates", []):
        item = dict(source)
        replay_results = tuple(
            ReplayResult(**result) for result in item.pop("replay_results", [])
        )
        item["artifact_paths"] = tuple(item.get("artifact_paths", []))
        item["risk_flags"] = tuple(item.get("risk_flags", []))
        candidates.append(CandidateMutation(**item, replay_results=replay_results))

    return EvolutionPacket(
        packet_id=raw["packet_id"],
        agent=raw["agent"],
        failure_summary=raw["failure_summary"],
        decision_capsule=raw["decision_capsule"],
        outcome_receipt=raw["outcome_receipt"],
        evidence=evidence,
        hypotheses=hypotheses,
        probes=probes,
        candidates=tuple(candidates),
        selected_candidate_id=raw.get("selected_candidate_id"),
        metadata=raw.get("metadata", {}),
    )


def _attach_measured_replay(packet: EvolutionPacket, replay_manifest: str) -> EvolutionPacket:
    if packet.selected_candidate_id is None:
        raise click.ClickException("replay requires a selected candidate")
    executed = run_replay_manifest(Path(replay_manifest))
    measured = tuple(item.result for item in executed)
    candidates = tuple(
        replace(candidate, replay_results=measured)
        if candidate.id == packet.selected_candidate_id
        else candidate
        for candidate in packet.candidates
    )
    return replace(packet, candidates=candidates)


@click.group()
def cli() -> None:
    """Counterproof: falsifiable change control for self-modifying agents."""


@cli.command("build")
@click.argument("packet_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--out", "out_file", default="EVOLUTION_PR.md", show_default=True)
@click.option(
    "--replay-manifest",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Execute real replay commands and attach results to the selected candidate.",
)
def build(packet_file: str, out_file: str, replay_manifest: str | None) -> None:
    """Build a reviewable behavior PR from an evolution packet."""
    raw = json.loads(Path(packet_file).read_text(encoding="utf-8"))
    packet = _packet_from_json(raw)

    if replay_manifest:
        packet = _attach_measured_replay(packet, replay_manifest)

    output = render_evolution_pr(packet)
    Path(out_file).write_text(output, encoding="utf-8")
    click.echo(f"Built {out_file}")


@cli.command("ingest")
@click.argument("trace_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--out", "out_file", default="EVOLUTION_PACKET.json", show_default=True)
@click.option(
    "--surface",
    type=click.Choice(["skill", "prompt", "policy", "router", "memory", "tool", "eval"]),
    default=None,
    help="Optionally select one generated candidate surface for later replay.",
)
def ingest(trace_file: str, out_file: str, surface: str | None) -> None:
    """Compile a raw JSON/JSONL agent trace into an Evolution Packet."""
    trace = load_trace(Path(trace_file))
    packet = compile_trace(trace)
    if surface is not None:
        try:
            packet = select_candidate(packet, surface=surface)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

    Path(out_file).write_text(
        json.dumps(packet_to_dict(packet), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    click.echo(
        f"Compiled {trace.get('trace_id', Path(trace_file).stem)} -> "
        f"{len(packet.evidence)} evidence items, "
        f"{len(packet.hypotheses)} hypotheses, "
        f"{len(packet.candidates)} candidates."
    )
    if packet.selected_candidate_id:
        click.echo(f"Selected {packet.selected_candidate_id} for surface {surface}.")
    else:
        click.echo("No candidate selected; hypotheses remain proposals until you choose one to test.")
    click.echo(f"Wrote {out_file}")


@cli.command("prove")
@click.argument("trace_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--replay-manifest",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--surface",
    type=click.Choice(["skill", "prompt", "policy", "router", "memory", "tool", "eval"]),
    default=None,
    help="Candidate surface to test. Omit to test the top heuristic hypothesis.",
)
@click.option("--out", "out_file", default="EVOLUTION_PR.md", show_default=True)
@click.option("--packet-out", default=None, type=click.Path(dir_okay=False))
def prove(
    trace_file: str,
    replay_manifest: str,
    surface: str | None,
    out_file: str,
    packet_out: str | None,
) -> None:
    """Compile a trace, select one hypothesis, run replay, and render Behavior Proof."""
    trace = load_trace(Path(trace_file))
    packet = compile_trace(trace)
    try:
        packet = select_candidate(packet, surface=surface)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    selection_mode = "explicit-surface" if surface else "heuristic-top-ranked"
    packet = replace(
        packet,
        metadata={
            **packet.metadata,
            "selection_mode": selection_mode,
        },
    )
    packet = _attach_measured_replay(packet, replay_manifest)

    Path(out_file).write_text(render_evolution_pr(packet), encoding="utf-8")
    if packet_out:
        Path(packet_out).write_text(
            json.dumps(packet_to_dict(packet), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    selected = packet.selected_candidate()
    click.echo(
        f"Proved {packet.packet_id} using {selection_mode}; "
        f"candidate={selected.id if selected else 'none'}."
    )
    if surface is None:
        click.echo(
            "Note: top-ranked attribution is heuristic. Replay validates the tested mutation, "
            "not unique causal truth."
        )
    click.echo(f"Built {out_file}")


@cli.command("evolve")
@click.argument("trace_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--experiment-manifest",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--surface",
    "surfaces",
    multiple=True,
    type=click.Choice(["skill", "prompt", "policy", "router", "memory", "tool", "eval"]),
    help="Mutation surfaces to compare. Repeat the flag. Defaults to compiled trace candidates.",
)
@click.option("--out", "out_file", default="EVOLUTION_REVIEW.md", show_default=True)
@click.option("--matrix-out", default=None, type=click.Path(dir_okay=False))
@click.option("--packet-out", default=None, type=click.Path(dir_okay=False))
@click.option("--probe-plan-out", default=None, type=click.Path(dir_okay=False))
@click.option("--probe-scaffold-out", default=None, type=click.Path(dir_okay=False))
@click.option("--receipt-out", default=None, type=click.Path(dir_okay=False))
def evolve(
    trace_file: str,
    experiment_manifest: str,
    surfaces: tuple[str, ...],
    out_file: str,
    matrix_out: str | None,
    packet_out: str | None,
    probe_plan_out: str | None,
    probe_scaffold_out: str | None,
    receipt_out: str | None,
) -> None:
    """Actively discriminate hypotheses and select only a unique surviving mutation."""
    trace = load_trace(Path(trace_file))
    packet = compile_trace(trace)
    compiled_surfaces = tuple(dict.fromkeys(candidate.surface for candidate in packet.candidates))
    selected_surfaces = surfaces or compiled_surfaces

    try:
        run = run_discrimination_manifest(
            Path(experiment_manifest),
            surfaces=selected_surfaces,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    mechanisms = {
        hypothesis.target_surface: hypothesis.mechanism
        for hypothesis in packet.hypotheses
    }
    matrix = render_discrimination_markdown(run, mechanisms=mechanisms)

    metadata = {
        **packet.metadata,
        "selection_mode": "active-discrimination",
        "tested_surfaces": ",".join(selected_surfaces),
        "diagnostic_cases": ",".join(run.diagnostic_cases),
        "trace_sha256": file_sha256(Path(trace_file)),
        "experiment_sha256": file_sha256(Path(experiment_manifest)),
    }

    if run.discriminated_surface:
        survivor = next(
            item for item in run.variants
            if item.surface == run.discriminated_surface
        )
        selected = next(
            candidate for candidate in packet.candidates
            if candidate.surface == run.discriminated_surface
        )
        candidates = tuple(
            replace(candidate, replay_results=survivor.replays)
            if candidate.id == selected.id
            else candidate
            for candidate in packet.candidates
        )
        packet = replace(
            packet,
            candidates=candidates,
            selected_candidate_id=selected.id,
            metadata={
                **metadata,
                "discrimination_result": (
                    f"unique-survivor:{run.discriminated_surface}"
                ),
            },
        )
    else:
        packet = replace(
            packet,
            metadata={
                **metadata,
                "discrimination_result": run.selection_state,
                "runtime_survivors": ",".join(
                    item.surface for item in run.survivors
                ),
                "eligible_survivors": ",".join(
                    item.surface for item in run.eligible_survivors
                ),
                "prediction_blocked_survivors": ",".join(
                    item.surface for item in run.prediction_blocked_survivors
                ),
            },
        )

    suggestions = plan_next_probes(packet, run)
    probe_plan = render_probe_plan(suggestions)
    review = render_evolution_pr(packet) + "\n\n" + matrix
    if suggestions:
        review += "\n\n" + probe_plan
    Path(out_file).write_text(review, encoding="utf-8")

    if matrix_out:
        Path(matrix_out).write_text(matrix, encoding="utf-8")
    if probe_plan_out:
        Path(probe_plan_out).write_text(probe_plan, encoding="utf-8")
    if probe_scaffold_out:
        scaffold = build_probe_scaffold(packet, suggestions)
        Path(probe_scaffold_out).write_text(
            json.dumps(scaffold, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    if packet_out:
        Path(packet_out).write_text(
            json.dumps(packet_to_dict(packet), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    if receipt_out:
        receipt = build_proof_receipt(
            trace_path=Path(trace_file),
            experiment_path=Path(experiment_manifest),
            packet=packet,
            run=run,
        )
        write_receipt(Path(receipt_out), receipt)

    if run.discriminated_surface:
        selected = packet.selected_candidate()
        click.echo(
            f"Unique survivor: {run.discriminated_surface}; "
            f"selected candidate={selected.id if selected else 'none'}."
        )
        click.echo(
            "Selection is relative to the tested intervention matrix, not proof of "
            "unique causal truth."
        )
    elif len(run.eligible_survivors) > 1:
        click.echo(
            "No automatic selection: multiple eligible interventions survived — "
            + ", ".join(item.surface for item in run.eligible_survivors)
        )
        if suggestions:
            click.echo(
                "Next discriminating probe planned for: "
                + "; ".join(
                    f"{item.left_surface} vs {item.right_surface}"
                    for item in suggestions
                )
            )
    elif run.prediction_blocked_survivors:
        click.echo(
            "No automatic selection: runtime survivor(s) were blocked by their "
            "pre-registered prediction contract — "
            + ", ".join(
                item.surface for item in run.prediction_blocked_survivors
            )
        )
    else:
        click.echo(
            "No automatic selection: none of the tested interventions survived."
        )
    click.echo(f"Built {out_file}")


@cli.command("discriminate")
@click.argument("trace_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--experiment-manifest",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--surface",
    "surfaces",
    multiple=True,
    type=click.Choice(["skill", "prompt", "policy", "router", "memory", "tool", "eval"]),
    help="Mutation surfaces to compare. Repeat the flag. Defaults to compiled trace candidates.",
)
@click.option("--out", "out_file", default="DISCRIMINATION.md", show_default=True)
@click.option("--json-out", default=None, type=click.Path(dir_okay=False))
def discriminate(
    trace_file: str,
    experiment_manifest: str,
    surfaces: tuple[str, ...],
    out_file: str,
    json_out: str | None,
) -> None:
    """Run competing interventions on the same cases to discriminate hypotheses."""
    trace = load_trace(Path(trace_file))
    packet = compile_trace(trace)
    compiled_surfaces = tuple(dict.fromkeys(candidate.surface for candidate in packet.candidates))
    selected_surfaces = surfaces or compiled_surfaces

    try:
        run = run_discrimination_manifest(
            Path(experiment_manifest),
            surfaces=selected_surfaces,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    mechanisms = {
        hypothesis.target_surface: hypothesis.mechanism
        for hypothesis in packet.hypotheses
    }
    report = render_discrimination_markdown(run, mechanisms=mechanisms)
    if suggestions := plan_next_probes(packet, run):
        report += "\n\n" + render_probe_plan(suggestions)
    Path(out_file).write_text(report, encoding="utf-8")

    suggestions = plan_next_probes(packet, run)
    payload = discrimination_to_dict(run)
    payload["source_trace_id"] = packet.metadata.get("source_trace_id", "")
    payload["trace_sha256"] = file_sha256(Path(trace_file))
    payload["experiment_sha256"] = file_sha256(Path(experiment_manifest))
    payload["tested_surfaces"] = list(selected_surfaces)
    payload["interpretation"] = (
        "relative support among tested interventions; not proof of unique causal truth"
    )
    payload["next_probe_suggestions"] = [item.to_dict() for item in suggestions]
    if json_out:
        Path(json_out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    if run.discriminated_surface:
        click.echo(
            f"Current probe matrix discriminated {run.discriminated_surface!r} "
            "from the tested alternatives."
        )
    elif len(run.eligible_survivors) > 1:
        click.echo(
            "Probe matrix is ambiguous; eligible survivors: "
            + ", ".join(item.surface for item in run.eligible_survivors)
        )
    elif run.prediction_blocked_survivors:
        click.echo(
            "Runtime survivor(s) blocked by pre-registered prediction contracts: "
            + ", ".join(
                item.surface for item in run.prediction_blocked_survivors
            )
        )
    else:
        click.echo("No tested surface survived the current probe matrix.")
    click.echo("This is relative evidence, not unique causal proof.")
    click.echo(f"Built {out_file}")


@cli.command("replay")
@click.argument("manifest_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--out", "out_file", default="REPLAY_RESULTS.json", show_default=True)
def replay(manifest_file: str, out_file: str) -> None:
    """Run real baseline/candidate commands and record replay evidence."""
    executed = run_replay_manifest(Path(manifest_file))
    payload = serialize_replays(executed)
    Path(out_file).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    passed = sum(case["verdict"] == "pass" for case in payload["cases"])
    click.echo(f"Executed {len(payload['cases'])} replay cases; {passed} candidate passes.")
    click.echo(f"Wrote {out_file}")


@cli.command("bind-probe-adapter")
@click.argument("scaffold_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--adapter",
    "adapter_parts",
    multiple=True,
    required=True,
    help="Adapter argv part. Repeat for each argument, e.g. --adapter python --adapter my_adapter.py",
)
@click.option("--reviewed-by", required=True, help="Reviewer identity or label.")
@click.option("--review-note", required=True, help="Why this scaffold is safe to execute.")
@click.option("--out", "out_file", default="READY_EXPERIMENT.json", show_default=True)
def bind_probe_adapter_cmd(
    scaffold_file: str,
    adapter_parts: tuple[str, ...],
    reviewed_by: str,
    review_note: str,
    out_file: str,
) -> None:
    """Approve a draft probe scaffold and bind it to one executable adapter."""
    raw = json.loads(Path(scaffold_file).read_text(encoding="utf-8"))
    try:
        bound = bind_probe_adapter(
            raw,
            adapter=adapter_parts,
            reviewed_by=reviewed_by,
            review_note=review_note,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    Path(out_file).write_text(
        json.dumps(bound, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    click.echo(
        "Bound reviewed scaffold to adapter; status=ready. "
        "Runtime evidence is still required before any mutation can be selected."
    )
    click.echo(f"Wrote {out_file}")


@cli.command("verify-receipt")
@click.argument("receipt_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--trace", "trace_file", default=None, type=click.Path(dir_okay=False))
@click.option(
    "--experiment-manifest",
    default=None,
    type=click.Path(dir_okay=False),
)
def verify_receipt(
    receipt_file: str,
    trace_file: str | None,
    experiment_manifest: str | None,
) -> None:
    """Verify that a Behavior Proof still points to unchanged source inputs."""
    receipt = json.loads(Path(receipt_file).read_text(encoding="utf-8"))
    errors = verify_proof_receipt(
        receipt,
        trace_path=Path(trace_file) if trace_file else None,
        experiment_path=(
            Path(experiment_manifest)
            if experiment_manifest
            else None
        ),
    )
    if errors:
        raise click.ClickException("; ".join(errors))
    click.echo(
        "VERIFIED: trace and experiment manifest match the stored Proof Receipt."
    )


@cli.command("doctor")
@click.option(
    "--json-output",
    is_flag=True,
    help="Emit machine-readable self-test results.",
)
def doctor(json_output: bool) -> None:
    """Run an install-level self-test using a temporary real Git repository."""
    report = run_doctor()
    click.echo(doctor_json(report) if json_output else render_doctor(report))
    if not report.ok:
        raise click.ClickException("Counterproof doctor failed")


@cli.command("init-github")
@click.option("--repo", "repo_dir", default=".", show_default=True, type=click.Path(file_okay=False))
@click.option(
    "--test-command",
    default=None,
    help="Override automatic test-runner detection. Use {tests} where changed test paths belong.",
)
@click.option("--force", is_flag=True, help="Replace an existing Counterproof workflow.")
@click.option(
    "--require-witness",
    is_flag=True,
    help="Generate a workflow that blocks unless a real regression witness is produced.",
)
@click.option(
    "--require-clean-integrity",
    is_flag=True,
    help="Generate a workflow that blocks on any test/CI evidence-surface change.",
)
def init_github_cmd(
    repo_dir: str,
    test_command: str | None,
    force: bool,
    require_witness: bool,
    require_clean_integrity: bool,
) -> None:
    """Detect the local test runner and install a Counterproof PR workflow."""
    try:
        destination, detection = init_github(
            Path(repo_dir),
            test_command=test_command,
            force=force,
            require_witness=require_witness,
            require_clean_integrity=require_clean_integrity,
        )
    except (ValueError, FileExistsError) as exc:
        raise click.ClickException(str(exc)) from exc

    if detection is not None:
        click.echo(
            f"Detected {detection.runner} ({detection.confidence} confidence): "
            f"{detection.command}"
        )
        if detection.evidence:
            click.echo("Evidence: " + ", ".join(detection.evidence))
    else:
        click.echo(f"Using explicit test command: {test_command}")

    click.echo(f"Wrote {destination}")
    click.echo(
        "Next: install your project dependencies in the generated workflow before "
        "the Counterproof step when the runner needs them."
    )


@cli.command("integrity")
@click.option(
    "--base",
    "base_ref",
    required=True,
    help="Git ref for the pre-change code, e.g. origin/main or a PR base SHA.",
)
@click.option("--head", "head_ref", default="HEAD", show_default=True)
@click.option("--repo", "repo_dir", default=".", show_default=True, type=click.Path(file_okay=False))
@click.option("--out", "out_file", default="PROOF_INTEGRITY.md", show_default=True)
@click.option("--json-out", default="PROOF_INTEGRITY.json", show_default=True)
@click.option(
    "--require-clean",
    is_flag=True,
    help="Exit non-zero when the PR changes evidence-producing surfaces.",
)
def integrity(
    base_ref: str,
    head_ref: str,
    repo_dir: str,
    out_file: str,
    json_out: str,
    require_clean: bool,
) -> None:
    """Detect whether a PR changes the tests/CI machinery judging its own evidence."""
    try:
        report = inspect_proof_integrity(
            Path(repo_dir),
            base_ref=base_ref,
            head_ref=head_ref,
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    Path(out_file).write_text(render_integrity_markdown(report), encoding="utf-8")
    write_integrity_json(Path(json_out), report)

    click.echo(f"Proof integrity: {report.status}")
    click.echo(f"Findings: {len(report.findings)}")
    click.echo(f"High risk: {report.high_risk_count}")
    click.echo(f"Wrote {out_file}")
    click.echo(f"Wrote {json_out}")

    if require_clean and report.status != "clean":
        raise click.ClickException(
            f"proof integrity review required: {len(report.findings)} finding(s)"
        )


@cli.command("witness")
@click.option(
    "--base",
    "base_ref",
    required=True,
    help="Git ref for the pre-change code, e.g. origin/main or a PR base SHA.",
)
@click.option("--head", "head_ref", default="HEAD", show_default=True)
@click.option(
    "--test-command",
    required=True,
    help="Command used for changed tests. Use {tests} where paths should be inserted.",
)
@click.option("--repo", "repo_dir", default=".", show_default=True, type=click.Path(file_okay=False))
@click.option("--timeout", "timeout_seconds", default=300.0, show_default=True, type=float)
@click.option("--out", "out_file", default="REGRESSION_WITNESS.md", show_default=True)
@click.option("--json-out", default="REGRESSION_WITNESS.json", show_default=True)
@click.option(
    "--require-witness",
    is_flag=True,
    help="Exit non-zero unless changed tests fail on base and pass on head.",
)
def witness(
    base_ref: str,
    head_ref: str,
    test_command: str,
    repo_dir: str,
    timeout_seconds: float,
    out_file: str,
    json_out: str,
    require_witness: bool,
) -> None:
    """Prove that changed PR tests fail before the fix and pass after it."""
    try:
        result = run_regression_witness(
            Path(repo_dir),
            base_ref=base_ref,
            head_ref=head_ref,
            test_command=test_command,
            timeout_seconds=timeout_seconds,
        )
    except (RuntimeError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    Path(out_file).write_text(render_witness_markdown(result), encoding="utf-8")
    write_witness_json(Path(json_out), result)

    click.echo(f"Regression witness: {result.status}")
    click.echo(f"Changed tests: {len(result.tests)}")
    click.echo(f"Wrote {out_file}")
    click.echo(f"Wrote {json_out}")

    if require_witness and not result.witnessed:
        raise click.ClickException(
            f"regression witness required, got status={result.status}"
        )


@cli.command("audit")
@click.option("--json-output", is_flag=True, help="Emit machine-readable JSON.")
def audit(json_output: bool) -> None:
    """Show what Counterproof can actually do today, with evidence and limitations."""
    report = capability_report()
    if json_output:
        click.echo(json.dumps(report, indent=2))
        return

    for item in report["capabilities"]:
        click.echo(f"[{item['status'].upper():7}] {item['name']}")
        click.echo(f"          {item['evidence']}")
        if item["limitation"]:
            click.echo(f"          limit: {item['limitation']}")


@cli.command("demo")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8765, type=int, show_default=True)
def demo(host: str, port: int) -> None:
    """Serve the interactive Counterproof playground from site/."""
    checkout_site = Path(__file__).resolve().parents[2] / "site"
    installed_site = Path(sys.prefix) / "share" / "counterproof" / "site"
    legacy_site = Path(sys.prefix) / "share" / "skill-factory" / "site"
    if (checkout_site / "index.html").exists():
        site_dir = checkout_site
    elif (installed_site / "index.html").exists():
        site_dir = installed_site
    else:
        site_dir = legacy_site
    if not (site_dir / "index.html").exists():
        raise click.ClickException(
            "Counterproof playground assets were not found in the checkout or installed wheel"
        )

    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer((host, port), handler)
    click.echo(f"Counterproof playground: http://{host}:{port}")
    click.echo("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        click.echo("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    cli()
