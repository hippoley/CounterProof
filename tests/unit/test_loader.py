"""Tests for skill loader."""

import pytest

from skill_factory.loader import load_skill, load_skill_index, parse_frontmatter

VALID_SKILL_MD = """---
name: test-skill
description: A test skill for unit testing purposes.
version: "0.1.0"
license: apache-2.0
metadata:
  domain: testing
  tags: [test]
---

## Purpose
Test skill.

## When to use
In tests.

## Procedure
1. Do the thing.
"""


def test_parse_frontmatter_valid():
    data, body = parse_frontmatter(VALID_SKILL_MD)
    assert data["name"] == "test-skill"
    assert data["description"] == "A test skill for unit testing purposes."
    assert "## Purpose" in body


def test_parse_frontmatter_missing():
    with pytest.raises(ValueError, match="missing YAML frontmatter"):
        parse_frontmatter("# No frontmatter here")


def test_load_skill_valid(tmp_path):
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(VALID_SKILL_MD)
    skill = load_skill(skill_dir)
    assert skill.name == "test-skill"
    assert skill.meta.version == "0.1.0"
    assert skill.meta.domain == "testing"
    assert "test" in skill.meta.tags


def test_load_skill_missing_skill_md(tmp_path):
    skill_dir = tmp_path / "empty-skill"
    skill_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        load_skill(skill_dir)


def test_load_skill_missing_name(tmp_path):
    skill_dir = tmp_path / "bad-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\ndescription: No name here.\n---\n# Body"
    )
    with pytest.raises(ValueError, match="missing required field: name"):
        load_skill(skill_dir)


def test_load_skill_index(tmp_path):
    for i in range(3):
        d = tmp_path / f"skill-{i}"
        d.mkdir()
        (d / "SKILL.md").write_text(
            f"---\nname: skill-{i}\ndescription: Skill number {i}.\n---\n# Body"
        )
    index = load_skill_index(tmp_path)
    assert len(index) == 3
    assert index[0].name == "skill-0"
