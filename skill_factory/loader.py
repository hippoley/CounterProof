"""Skill loader: reads SKILL.md and associated resources."""
from __future__ import annotations
import re
from pathlib import Path

import yaml

from skill_factory.models import Skill, SkillMeta


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from a markdown string."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("SKILL.md is missing YAML frontmatter (--- ... ---)")
    raw_yaml = match.group(1)
    body = text[match.end():]
    data = yaml.safe_load(raw_yaml) or {}
    return data, body


def load_skill(skill_dir: Path) -> Skill:
    """Load a skill from its directory. Raises if SKILL.md is missing or malformed."""
    skill_dir = Path(skill_dir)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found in {skill_dir}")

    content = skill_md.read_text(encoding="utf-8")
    data, _ = parse_frontmatter(content)

    if "name" not in data:
        raise ValueError(f"SKILL.md in {skill_dir} is missing required field: name")
    if "description" not in data:
        raise ValueError(f"SKILL.md in {skill_dir} is missing required field: description")

    meta = SkillMeta(
        name=data["name"],
        description=data["description"],
        version=str(data.get("version", "0.1.0")),
        license=data.get("license", "apache-2.0"),
        compatibility=data.get("compatibility", ""),
        metadata=data.get("metadata", {}),
    )
    return Skill(meta=meta, path=skill_dir, content=content)


def load_skill_index(skills_dir: Path) -> list[SkillMeta]:
    """Progressive disclosure: load only name+description for all skills."""
    skills_dir = Path(skills_dir)
    index = []
    for skill_dir in sorted(skills_dir.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            skill = load_skill(skill_dir)
            index.append(skill.meta)
        except Exception:
            pass  # skip malformed skills during index scan
    return index
