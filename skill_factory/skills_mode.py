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
    # Keep the general bridge observational: deployments and mutations must
    # never bypass the explicit, signed Skill promotion path.
    read_only = {
        ("skills", "list"), ("skills", "show"), ("skills", "status"),
        ("agents", "list"), ("tools", "list"), ("repo", "status"),
        ("presets", "list"), ("presets", "status"), ("git", "versions"),
    }
    if tuple(args[:2]) not in read_only:
        raise click.ClickException(
            "direct mutation blocked; use 'counterproof skill promote' "
            "for evaluated deployments, or use upstream app independently"
        )
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


@skill_mode.command("keygen")
@click.argument("key_file", type=click.Path(dir_okay=False, path_type=Path))
def keygen(key_file: Path) -> None:
    """Create a 0600 local gate-attestation key; never store it in Git."""
    from skill_factory.skill_gate import GateError, create_key

    try:
        new_path = create_key(key_file)
    except (GateError, OSError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Created local attestation key: {new_path}")
    click.echo("Keep this secret out of Git and outside the Skill directory.")


@skill_mode.command("evaluate")
@click.argument("reference")
@click.option("--suite", "suite_path", required=True, type=click.Path(
    exists=True, dir_okay=False, path_type=Path,
))
@click.option("--runner-binary", required=True)
@click.option("--manager-binary", default="skills-manager-cli", show_default=True)
@click.option("--key", "key_file", required=True, type=click.Path(
    exists=True, dir_okay=False, path_type=Path,
))
@click.option("--min-gain", default=1, type=click.IntRange(min=1), show_default=True)
@click.option("--out", "out_path", type=click.Path(dir_okay=False, path_type=Path),
              default=Path("SKILL_GATE_RECEIPT.json"))
def evaluate_skill(
    reference: str, suite_path: Path, runner_binary: str, manager_binary: str,
    key_file: Path, min_gain: int, out_path: Path,
) -> None:
    """Paired external-suite evaluation of the Skill installed by Skills Manager."""
    from skill_factory.skill_gate import GateError, evaluate

    if out_path.exists():
        raise click.ClickException("receipt already exists; choose a new --out path")
    try:
        receipt = evaluate(
            manager_binary, reference, suite_path, runner_binary,
            key_file=key_file, min_gain=min_gain,
        )
        with out_path.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except (GateError, OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        f"Skill evidence: {receipt['verdict']} "
        f"gains={receipt['gain_cases']} regressions={receipt['regression_cases']}"
    )
    click.echo(f"Receipt: {out_path} (HMAC-bound to your external key)")
    if receipt["verdict"] != "PASS_SCOPED":
        raise click.ClickException("evaluation gate failed; promotion blocked")


@skill_mode.command("promote")
@click.argument("reference")
@click.option("--receipt", "receipt_path", required=True, type=click.Path(
    exists=True, dir_okay=False, path_type=Path,
))
@click.option("--suite", "suite_path", required=True, type=click.Path(
    exists=True, dir_okay=False, path_type=Path,
))
@click.option("--key", "key_file", required=True, type=click.Path(
    exists=True, dir_okay=False, path_type=Path,
))
@click.option("--manager-binary", default="skills-manager-cli", show_default=True)
@click.option("--agent", "agents", required=True, multiple=True)
@click.option("--apply", is_flag=True, help="Actually deploy, never default.")
@click.option("--confirm-sha256", default=None, help="Required for --apply.")
def promote_skill(
    reference: str, receipt_path: Path, suite_path: Path, key_file: Path,
    manager_binary: str, agents: tuple[str, ...], apply: bool,
    confirm_sha256: str | None,
) -> None:
    """Fail closed unless signed scope, content, suite and runner still match."""
    from skill_factory.skill_gate import GateError, promote

    try:
        result = promote(
            manager_binary, reference, receipt_path, agents,
            key_file=key_file, suite_path=suite_path,
            apply=apply, confirm_sha256=confirm_sha256,
        )
    except (GateError, OSError, ValueError, TypeError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, indent=2, sort_keys=True))
    if not apply:
        click.echo("Preflight only: nothing was deployed.")
