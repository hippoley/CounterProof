"""Tests for skill registry."""
import pytest
from pathlib import Path
from skill_factory.registry.registry import SkillRegistry


SKILL_MD = """---
name: my-skill
description: A skill for registry testing with sufficient description length.
version: "0.2.0"
license: apache-2.0
metadata:
  domain: testing
  tags: [registry, test]
---

## Purpose
Registry test skill.
"""


@pytest.fixture
def skill_dir(tmp_path):
    d = tmp_path / "my-skill"
    d.mkdir()
    (d / "SKILL.md").write_text(SKILL_MD)
    return d


@pytest.fixture
def registry(tmp_path):
    return SkillRegistry(tmp_path / "registry")


def test_add_and_list(registry, skill_dir):
    registry.add(skill_dir)
    skills = registry.list()
    assert len(skills) == 1
    assert skills[0].name == "my-skill"
    assert skills[0].version == "0.2.0"


def test_get(registry, skill_dir):
    registry.add(skill_dir)
    skill = registry.get("my-skill")
    assert skill.name == "my-skill"


def test_remove(registry, skill_dir):
    registry.add(skill_dir)
    registry.remove("my-skill")
    assert registry.list() == []


def test_overwrite(registry, skill_dir):
    registry.add(skill_dir)
    with pytest.raises(FileExistsError):
        registry.add(skill_dir)
    registry.add(skill_dir, overwrite=True)  # should not raise


def test_search(registry, skill_dir):
    registry.add(skill_dir)
    results = registry.search("registry")
    assert len(results) == 1
    results_none = registry.search("nonexistent-xyz")
    assert results_none == []
