"""CLI for the EvoPR prototype."""
from __future__ import annotations

import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import click

from .capabilities import capability_report
from .models import CandidateMutation, Evidence, EvolutionPacket, Hypothesis, ReplayResult
from .replay import run_replay_manifest, serialize_replays
from .report import render_evolution_pr


def _packet_from_json(raw: dict) -> EvolutionPacket:
    evidence = tuple(Evidence(**item) for item in raw.get("evidence", []))
    hypotheses = tuple(Hypothesis(**item) for item in raw.get("hypotheses", []))

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
        candidates=tuple(candidates),
        selected_candidate_id=raw.get("selected_candidate_id"),
        metadata=raw.get("metadata", {}),
    )


@click.group()
def cli() -> None:
    """EvoPR: pull requests for agent behavior."""


@cli.command("build")
@click.argument("packet_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--out", "out_file", default="EVOLUTION_PR.md", show_default=True)
def build(packet_file: str, out_file: str) -> None:
    """Build a reviewable behavior PR from an evolution packet."""
    raw = json.loads(Path(packet_file).read_text(encoding="utf-8"))
    packet = _packet_from_json(raw)
    output = render_evolution_pr(packet)
    Path(out_file).write_text(output, encoding="utf-8")
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
