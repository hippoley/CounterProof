"""Opt-in Skill mode and upstream Skills Manager CLI bridge.

No Skill execution, installation or deployment occurs implicitly.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import click

from skill_factory.verifier.static_check import verify_skill


@click.group("skill")
def skill_mode() -> None:
    """Inspect, propose and manage Skills with explicit trust boundaries."""


@skill_mode.command("inspect")
@click.argument("skill_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--json-output", is_flag=True)
def inspect_skill(skill_dir: Path, json_output: bool) -> None:
    """Statically inspect SKILL.md without running code or installing a Skill."""
    root = skill_dir.resolve()
    if skill_dir.is_symlink():
        raise click.ClickException("skill directory must not be a symlink")
    skill_md = root / "SKILL.md"
    if skill_md.is_symlink():
        raise click.ClickException("SKILL.md must not be a symlink")
    if not skill_md.is_file():
        raise click.ClickException("SKILL.md not found")
    if (root / "scripts").is_symlink():
        raise click.ClickException("scripts directory must not be a symlink")
    verdict = verify_skill(root)
    receipt = {
        "schema_version": "counterproof.skill-inspection/v0.1",
        "skill_path": str(root),
        "skill_md_sha256": hashlib.sha256(skill_md.read_bytes()).hexdigest(),
        "static_verdict": "PASS" if verdict.passed else "FAIL",
        "errors": verdict.errors,
        "warnings": verdict.warnings,
        "evaluation_status": "NOT_RUN",
        "deployment_status": "NOT_PERFORMED",
        "security_scope": "HEURISTIC_STATIC_ONLY",
    }
    if json_output:
        click.echo(json.dumps(receipt, sort_keys=True, indent=2))
    else:
        click.echo("Skill static inspection: " + receipt["static_verdict"])
        click.echo("SKILL.md SHA-256: " + receipt["skill_md_sha256"])
        click.echo("No independent evaluation, execution or deployment performed.")
        for error in verdict.errors:
            click.echo("ERROR " + error)
        for warning in verdict.warnings:
            click.echo("WARN " + warning)
    if not verdict.passed:
        raise SystemExit(1)


@skill_mode.command("manager", context_settings={"ignore_unknown_options": True})
@click.option("--binary", type=str, default=None, help="Upstream CLI path override.")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def manager(binary: str | None, args: tuple[str, ...]) -> None:
    """Delegate to installed upstream CLI, e.g. -- skills list."""
    if not args:
        raise click.UsageError("pass arguments after --, e.g. -- skills list")
    executable = binary or os.environ.get("SKILLS_MANAGER_CLI") or "skills-manager-cli"
    found = shutil.which(executable)
    if found is None:
        raise click.ClickException(
            "Skills Manager CLI not found: " + executable +
            ". Install the pinned upstream CLI or pass --binary."
        )
    if Path(found).resolve() == Path(__file__).resolve():
        raise click.ClickException("recursive manager invocation is not allowed")
    try:
        result = subprocess.run([found, *args], check=False)
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc
    if result.returncode:
        raise SystemExit(result.returncode)


@skill_mode.command("evolve")
@click.argument("trace_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--out", type=click.Path(dir_okay=False, path_type=Path),
    default=Path("EVOLUTION_PACKET.json"),
)
def evolve_skill(trace_file: Path, out: Path) -> None:
    """Propose a Skill change from a trace; never promote automatically."""
    from skill_factory.evolution.trace import (
        compile_trace, load_trace, packet_to_dict, select_candidate,
    )

    try:
        packet = select_candidate(
            compile_trace(load_trace(trace_file)), surface="skill"
        )
    except (OSError, KeyError, ValueError, TypeError) as exc:
        raise click.ClickException(str(exc)) from exc
    out.write_text(
        json.dumps(packet_to_dict(packet), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    click.echo("Candidate: " + str(packet.selected_candidate_id or "NONE"))
    click.echo("PROPOSAL only; independent proof and deployment NOT performed.")
    click.echo("Wrote " + str(out))
