"""CLI for the EvoPR prototype."""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import click

from .capabilities import capability_report
from .discriminate import (
    discrimination_to_dict,
    render_discrimination_markdown,
    run_discrimination_manifest,
)
from .models import (
    CandidateMutation,
    Evidence,
    EvolutionPacket,
    Hypothesis,
    ProbeSpec,
    ReplayResult,
)
from .probe_planner import plan_next_probes, render_probe_plan
from .receipt import build_proof_receipt, file_sha256, verify_proof_receipt, write_receipt
from .replay import run_replay_manifest, serialize_replays
from .report import render_evolution_pr
from .trace import compile_trace, load_trace, packet_to_dict, select_candidate


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
    """EvoPR: pull requests for agent behavior."""


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
@click.option("--receipt-out", default=None, type=click.Path(dir_okay=False))
def evolve(
    trace_file: str,
    experiment_manifest: str,
    surfaces: tuple[str, ...],
    out_file: str,
    matrix_out: str | None,
    packet_out: str | None,
    probe_plan_out: str | None,
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
        result = "ambiguous" if run.survivors else "no-survivor"
        packet = replace(
            packet,
            metadata={
                **metadata,
                "discrimination_result": result,
                "survivors": ",".join(item.surface for item in run.survivors),
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
    elif run.survivors:
        click.echo(
            "No automatic selection: multiple interventions survived — "
            + ", ".join(item.surface for item in run.survivors)
        )
        if suggestions:
            click.echo(
                "Next discriminating probe planned for: "
                + "; ".join(
                    f"{item.left_surface} vs {item.right_surface}"
                    for item in suggestions
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
    elif len(run.survivors) > 1:
        click.echo(
            "Probe matrix is ambiguous; survivors: "
            + ", ".join(item.surface for item in run.survivors)
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


@cli.command("audit")
@click.option("--json-output", is_flag=True, help="Emit machine-readable JSON.")
def audit(json_output: bool) -> None:
    """Show what EvoPR can actually do today, with evidence and limitations."""
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
    """Serve the interactive EvoPR playground from site/."""
    checkout_site = Path(__file__).resolve().parents[2] / "site"
    installed_site = Path(sys.prefix) / "share" / "skill-factory" / "site"
    site_dir = checkout_site if (checkout_site / "index.html").exists() else installed_site
    if not (site_dir / "index.html").exists():
        raise click.ClickException(
            "EvoPR playground assets were not found in the checkout or installed wheel"
        )

    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer((host, port), handler)
    click.echo(f"EvoPR playground: http://{host}:{port}")
    click.echo("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        click.echo("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    cli()
