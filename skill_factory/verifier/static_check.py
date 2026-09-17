"""Static verifier: checks SKILL.md structure, safety, and completeness."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from skill_factory.loader import load_skill, parse_frontmatter

DANGEROUS_PATTERNS = [
    "rm -rf",
    "os.system",
    "subprocess.call",
    "eval(",
    "exec(",
    "__import__",
    "DROP TABLE",
    "DELETE FROM",
]

REQUIRED_SECTIONS = ["## Purpose", "## When to use", "## Procedure"]


@dataclass
class CheckResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.passed = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def verify_skill(skill_dir: Path | str) -> CheckResult:
    """Run all static checks on a skill directory."""
    skill_dir = Path(skill_dir)
    result = CheckResult(passed=True)

    # 1. SKILL.md exists and parses
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        result.add_error("SKILL.md not found")
        return result

    try:
        skill = load_skill(skill_dir)
    except (OSError, TypeError, ValueError) as e:
        result.add_error(f"Failed to parse SKILL.md: {e}")
        return result

    content = skill.content

    # 2. Required frontmatter fields
    try:
        data, _body = parse_frontmatter(content)
    except ValueError as e:
        result.add_error(str(e))
        return result

    for field_name in ("name", "description"):
        if not data.get(field_name):
            result.add_error(f"Missing required frontmatter field: {field_name}")

    # 3. Description quality
    desc = data.get("description", "")
    if len(desc) < 20:
        result.add_warning("description is very short (< 20 chars); be more specific")
    if len(desc) > 300:
        result.add_warning("description is very long (> 300 chars); consider trimming")

    # 4. Required sections
    for section in REQUIRED_SECTIONS:
        if section not in content:
            result.add_warning(f"Missing recommended section: {section}")

    # 5. Safety: dangerous patterns in SKILL.md
    for pattern in DANGEROUS_PATTERNS:
        if pattern in content:
            result.add_error(f"Dangerous pattern found in SKILL.md: {pattern!r}")

    # 6. Safety: dangerous patterns in scripts
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        for script in scripts_dir.glob("*.py"):
            script_text = script.read_text(encoding="utf-8", errors="ignore")
            for pattern in DANGEROUS_PATTERNS:
                if pattern in script_text:
                    result.add_warning(
                        f"Potentially dangerous pattern in {script.name}: {pattern!r}"
                    )

    # 7. Schema file exists if assets dir present
    assets_dir = skill_dir / "assets"
    if assets_dir.exists():
        schemas = list(assets_dir.glob("*.schema.json"))
        if not schemas:
            result.add_warning("assets/ directory exists but no *.schema.json found")

    # 8. Evals exist
    evals_dir = skill_dir / "evals"
    if not evals_dir.exists() or not list(evals_dir.glob("*.json")):
        result.add_warning("No evals/ directory or eval JSON files found")

    return result
