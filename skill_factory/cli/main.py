"""Skill Factory CLI entry point."""
from __future__ import annotations
import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from skill_factory.loader import load_skill
from skill_factory.registry.registry import SkillRegistry
from skill_factory.verifier.static_check import verify_skill

console = Console()


@click.group()
@click.version_option(package_name="skill-factory")
def cli() -> None:
    """Skill Factory: forge agent skills from real task failures."""


# ── validate ──────────────────────────────────────────────────────────────

@cli.command()
@click.argument("skill_dir", type=click.Path(exists=True))
def validate(skill_dir: str) -> None:
    """Run static checks on a skill directory."""
    result = verify_skill(Path(skill_dir))

    if result.errors:
        console.print("[bold red]FAILED[/bold red]")
        for err in result.errors:
            console.print(f"  [red]ERROR[/red] {err}")
    else:
        console.print("[bold green]PASSED[/bold green]")

    for warn in result.warnings:
        console.print(f"  [yellow]WARN[/yellow]  {warn}")

    raise SystemExit(0 if result.passed else 1)


# ── registry ──────────────────────────────────────────────────────────────

@cli.group()
def registry() -> None:
    """Manage the skill registry."""


@registry.command("list")
@click.option("--registry-dir", default="registry_data", show_default=True)
def registry_list(registry_dir: str) -> None:
    """List all skills in the registry."""
    reg = SkillRegistry(registry_dir)
    skills = reg.list()
    if not skills:
        console.print("[dim]Registry is empty.[/dim]")
        return

    table = Table(title="Skill Registry")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Domain")
    table.add_column("Description")

    for s in skills:
        table.add_row(s.name, s.version, s.domain, s.description[:60])

    console.print(table)


@registry.command("add")
@click.argument("skill_dir", type=click.Path(exists=True))
@click.option("--registry-dir", default="registry_data", show_default=True)
@click.option("--overwrite", is_flag=True, default=False)
@click.option("--skip-validation", is_flag=True, default=False)
def registry_add(skill_dir: str, registry_dir: str, overwrite: bool, skip_validation: bool) -> None:
    """Add a skill to the registry (runs validation first)."""
    if not skip_validation:
        result = verify_skill(Path(skill_dir))
        if not result.passed:
            console.print("[bold red]Validation failed. Fix errors before adding to registry.[/bold red]")
            for err in result.errors:
                console.print(f"  [red]ERROR[/red] {err}")
            raise SystemExit(1)

    reg = SkillRegistry(registry_dir)
    skill = reg.add(Path(skill_dir), overwrite=overwrite)
    console.print(f"[green]Added[/green] {skill.name} v{skill.meta.version}")


@registry.command("remove")
@click.argument("name")
@click.option("--registry-dir", default="registry_data", show_default=True)
def registry_remove(name: str, registry_dir: str) -> None:
    """Remove a skill from the registry."""
    reg = SkillRegistry(registry_dir)
    reg.remove(name)
    console.print(f"[yellow]Removed[/yellow] {name}")


@registry.command("search")
@click.argument("query")
@click.option("--registry-dir", default="registry_data", show_default=True)
def registry_search(query: str, registry_dir: str) -> None:
    """Search skills by keyword."""
    reg = SkillRegistry(registry_dir)
    results = reg.search(query)
    if not results:
        console.print(f"[dim]No skills found for: {query}[/dim]")
        return
    for s in results:
        console.print(f"[cyan]{s.name}[/cyan] v{s.version} — {s.description[:80]}")
