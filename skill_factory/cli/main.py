"""Skill Factory CLI entry point."""
from __future__ import annotations
import json
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
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



# ── generate ──────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("trajectory_file", type=click.Path(exists=True))
@click.option("--output", "-o", default="skills", show_default=True, help="Output directory for generated skill")
@click.option("--provider", default="openai", show_default=True, type=click.Choice(["openai", "anthropic", "mock"]), help="LLM provider")
@click.option("--model", default="", help="Model name (default: gpt-4o for openai, claude-3-5-sonnet-20241022 for anthropic)")
@click.option("--skill-name", default="", help="Override the generated skill name")
@click.option("--validate/--no-validate", default=True, show_default=True, help="Run static validation after generation")
@click.option("--api-key", default="", envvar=["OPENAI_API_KEY", "ANTHROPIC_API_KEY"], help="API key (or set OPENAI_API_KEY / ANTHROPIC_API_KEY env var)")
def generate(
    trajectory_file: str,
    output: str,
    provider: str,
    model: str,
    skill_name: str,
    validate: bool,
    api_key: str,
) -> None:
    """Generate a SKILL.md candidate from a task trajectory JSON file.

    TRAJECTORY_FILE should be a JSON file with a list of trajectory objects,
    or a single trajectory object. See docs/trajectory-format.md for the schema.

    Example:

        skill-factory generate trajectory.json --provider openai --output skills/

        skill-factory generate trajectory.json --provider mock --output skills/
    """
    from skill_factory.generator.skill_generator import GeneratorConfig, SkillGenerator
    from skill_factory.generator.trajectory import Trajectory

    # Load trajectory file
    try:
        raw = json.loads(Path(trajectory_file).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        console.print(f"[red]ERROR[/red] Invalid JSON in {trajectory_file}: {e}")
        raise SystemExit(1)

    # Accept single object or list
    if isinstance(raw, dict):
        raw = [raw]

    try:
        trajectories = [Trajectory.from_dict(t) for t in raw]
    except (KeyError, TypeError) as e:
        console.print(f"[red]ERROR[/red] Failed to parse trajectory: {e}")
        raise SystemExit(1)

    console.print(f"Loaded [cyan]{len(trajectories)}[/cyan] trajectory/trajectories from [dim]{trajectory_file}[/dim]")

    # Resolve model default
    resolved_model = model
    if not resolved_model:
        resolved_model = "gpt-4o" if provider == "openai" else "claude-3-5-sonnet-20241022" if provider == "anthropic" else "mock"

    config = GeneratorConfig(
        provider=provider,  # type: ignore[arg-type]
        model=resolved_model,
        api_key=api_key,
    )
    generator = SkillGenerator(config)

    console.print(f"Generating skill with [cyan]{provider}[/cyan] / [cyan]{resolved_model}[/cyan] ...")

    try:
        skill_dir = generator.generate_and_save(
            trajectories=trajectories,
            output_dir=Path(output),
            skill_name=skill_name or None,
        )
    except Exception as e:
        console.print(f"[red]ERROR[/red] Generation failed: {e}")
        raise SystemExit(1)

    skill_md_path = skill_dir / "SKILL.md"
    console.print(f"[green]Generated[/green] → {skill_dir}")

    # Show a preview
    skill_md_text = skill_md_path.read_text(encoding="utf-8")
    preview = "\n".join(skill_md_text.splitlines()[:20])
    console.print(Panel(Syntax(preview, "markdown", theme="monokai"), title="SKILL.md preview (first 20 lines)", expand=False))

    # Optionally validate
    if validate:
        console.print("\nRunning static validation ...")
        result = verify_skill(skill_dir)
        if result.errors:
            console.print("[bold red]Validation FAILED[/bold red] — fix before adding to registry:")
            for err in result.errors:
                console.print(f"  [red]ERROR[/red] {err}")
        else:
            console.print("[bold green]Validation PASSED[/bold green]")
        for warn in result.warnings:
            console.print(f"  [yellow]WARN[/yellow]  {warn}")

    console.print(f"\nNext steps:")
    console.print(f"  skill-factory validate {skill_dir}")
    console.print(f"  skill-factory registry add {skill_dir}")



# ── serve (Web UI) ────────────────────────────────────────────────────────────

@cli.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=7860, show_default=True)
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload (dev mode)")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the Skill Factory Web Review UI.

    Requires: pip install skill-factory[web]

    Then open: http://localhost:7860
    """
    try:
        import uvicorn  # type: ignore  # noqa: F401
    except ImportError:
        console.print("[red]ERROR[/red] uvicorn not installed. Run: pip install skill-factory[web]")
        raise SystemExit(1)

    console.print(f"Starting Skill Factory Web UI at [cyan]http://{host}:{port}[/cyan]")
    console.print("Press [bold]Ctrl+C[/bold] to stop.\n")

    import uvicorn  # type: ignore
    uvicorn.run("skill_factory.web.app:app", host=host, port=port, reload=reload)
