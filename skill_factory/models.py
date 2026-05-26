"""Core data models for Skill Factory."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SkillMeta:
    """Parsed frontmatter from SKILL.md."""
    name: str
    description: str
    version: str = "0.1.0"
    license: str = "apache-2.0"
    compatibility: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def domain(self) -> str:
        return self.metadata.get("domain", "general")

    @property
    def tags(self) -> list[str]:
        return self.metadata.get("tags", [])


@dataclass
class Skill:
    """A fully loaded skill with all resources."""
    meta: SkillMeta
    path: Path
    content: str  # full SKILL.md text

    @property
    def name(self) -> str:
        return self.meta.name

    @property
    def description(self) -> str:
        return self.meta.description

    def __repr__(self) -> str:
        return f"Skill(name={self.name!r}, version={self.meta.version!r})"


@dataclass
class EvalCase:
    """A single A/B evaluation test case."""
    id: str
    task: str
    expected_pass: bool
    verifier: str = "schema"  # schema | llm | human
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    """Result of running one eval case."""
    case_id: str
    with_skill: bool
    passed: bool
    score: float
    tokens_used: int = 0
    latency_ms: float = 0.0
    notes: str = ""


@dataclass
class EvalReport:
    """Aggregated A/B eval report for a skill."""
    skill_name: str
    skill_version: str
    baseline_pass_rate: float
    with_skill_pass_rate: float
    delta: float
    token_delta: float
    latency_delta_ms: float
    cases: list[EvalResult] = field(default_factory=list)

    @property
    def improved(self) -> bool:
        return self.delta > 0
