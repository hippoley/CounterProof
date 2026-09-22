"""CLI for the EvoPR prototype."""
from __future__ import annotations

import json
from pathlib import Path

import click

from .models import CandidateMutation, Evidence, EvolutionPacket, Hypothesis, ReplayResult
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


if __name__ == "__main__":
    cli()
