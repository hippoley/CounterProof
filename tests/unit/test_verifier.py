"""Tests for static verifier."""
from skill_factory.verifier.static_check import verify_skill

VALID_SKILL_MD = """---
name: test-skill
description: A test skill for unit testing purposes with enough detail.
version: "0.1.0"
license: apache-2.0
metadata:
  domain: testing
  tags: [test]
---

## Purpose
Test skill.

## When to use
In tests only.

## Procedure
1. Do the thing.
"""


def test_verify_valid_skill(tmp_path):
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(VALID_SKILL_MD)
    result = verify_skill(skill_dir)
    assert result.passed
    assert not result.errors


def test_verify_missing_skill_md(tmp_path):
    skill_dir = tmp_path / "empty"
    skill_dir.mkdir()
    result = verify_skill(skill_dir)
    assert not result.passed
    assert any("SKILL.md not found" in e for e in result.errors)


def test_verify_dangerous_pattern(tmp_path):
    skill_dir = tmp_path / "dangerous-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        VALID_SKILL_MD + "\nRun: rm -rf /tmp/data\n"
    )
    result = verify_skill(skill_dir)
    assert not result.passed
    assert any("rm -rf" in e for e in result.errors)


def test_verify_warns_missing_evals(tmp_path):
    skill_dir = tmp_path / "no-evals-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(VALID_SKILL_MD)
    result = verify_skill(skill_dir)
    assert result.passed  # warnings don't fail
    assert any("evals" in w.lower() for w in result.warnings)
