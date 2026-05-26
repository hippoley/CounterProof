"""
LLM-powered Skill Generator.

Synthesizes SKILL.md candidates from task trajectories and human feedback.
Supports OpenAI and Anthropic providers.
"""
from __future__ import annotations

import json
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from skill_factory.generator.prompt_builder import build_skill_generation_prompt
from skill_factory.generator.trajectory import Trajectory


Provider = Literal["openai", "anthropic", "mock"]


@dataclass
class GeneratorConfig:
    """Configuration for the LLM skill generator."""

    provider: Provider = "openai"
    model: str = "gpt-4o"
    temperature: float = 0.3
    max_tokens: int = 4096
    api_key: str = ""  # falls back to env var if empty
    system_prompt_extra: str = ""  # append domain-specific instructions


@dataclass
class GeneratedSkill:
    """Raw output from the LLM generator, before validation."""

    skill_md: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw_response: str = ""


class SkillGenerator:
    """
    Generates SKILL.md candidates from task trajectories using an LLM.

    Usage::

        from skill_factory.generator import SkillGenerator, GeneratorConfig
        from skill_factory.generator.trajectory import Trajectory

        config = GeneratorConfig(provider="openai", model="gpt-4o")
        generator = SkillGenerator(config)

        trajectories = [Trajectory.from_dict({...})]
        result = generator.generate(trajectories)
        print(result.skill_md)
    """

    def __init__(self, config: GeneratorConfig | None = None) -> None:
        self.config = config or GeneratorConfig()

    # ── public API ─────────────────────────────────────────────────────────────

    def generate(self, trajectories: list[Trajectory]) -> GeneratedSkill:
        """Generate a SKILL.md candidate from one or more trajectories."""
        prompt = build_skill_generation_prompt(trajectories)

        if self.config.provider == "openai":
            return self._call_openai(prompt)
        elif self.config.provider == "anthropic":
            return self._call_anthropic(prompt)
        elif self.config.provider == "mock":
            return self._mock_generate(trajectories)
        else:
            raise ValueError(f"Unknown provider: {self.config.provider!r}")

    def generate_and_save(
        self,
        trajectories: list[Trajectory],
        output_dir: Path,
        skill_name: str | None = None,
    ) -> Path:
        """
        Generate a skill and save it to output_dir/<skill_name>/SKILL.md.

        Returns the path to the created skill directory.
        """
        result = self.generate(trajectories)
        name = skill_name or self._extract_name(result.skill_md) or "generated-skill"
        skill_dir = Path(output_dir) / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(result.skill_md, encoding="utf-8")

        # Write generation metadata
        meta = {
            "provider": result.provider,
            "model": result.model,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "trajectory_ids": [t.task_id for t in trajectories],
        }
        (skill_dir / "generation_meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        return skill_dir

    # ── LLM backends ───────────────────────────────────────────────────────────

    def _call_openai(self, prompt: str) -> GeneratedSkill:
        """Call OpenAI chat completions API."""
        try:
            import openai  # type: ignore
        except ImportError as e:
            raise ImportError(
                "openai package not installed. Run: pip install skill-factory[llm]"
            ) from e

        import os

        api_key = self.config.api_key or os.environ.get("OPENAI_API_KEY", "")
        client = openai.OpenAI(api_key=api_key)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a Skill Engineer. Output ONLY the raw SKILL.md content "
                    "with YAML frontmatter. No explanation, no markdown fences around it."
                    + (f"\n\n{self.config.system_prompt_extra}" if self.config.system_prompt_extra else "")
                ),
            },
            {"role": "user", "content": prompt},
        ]

        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        skill_md = response.choices[0].message.content or ""
        skill_md = self._strip_fences(skill_md)

        return GeneratedSkill(
            skill_md=skill_md,
            provider="openai",
            model=self.config.model,
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            raw_response=skill_md,
        )

    def _call_anthropic(self, prompt: str) -> GeneratedSkill:
        """Call Anthropic Messages API."""
        try:
            import anthropic  # type: ignore
        except ImportError as e:
            raise ImportError(
                "anthropic package not installed. Run: pip install skill-factory[llm]"
            ) from e

        import os

        api_key = self.config.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        client = anthropic.Anthropic(api_key=api_key)

        system = (
            "You are a Skill Engineer. Output ONLY the raw SKILL.md content "
            "with YAML frontmatter. No explanation, no markdown fences around it."
            + (f"\n\n{self.config.system_prompt_extra}" if self.config.system_prompt_extra else "")
        )

        response = client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        skill_md = response.content[0].text if response.content else ""
        skill_md = self._strip_fences(skill_md)

        return GeneratedSkill(
            skill_md=skill_md,
            provider="anthropic",
            model=self.config.model,
            prompt_tokens=response.usage.input_tokens if response.usage else 0,
            completion_tokens=response.usage.output_tokens if response.usage else 0,
            raw_response=skill_md,
        )

    def _mock_generate(self, trajectories: list[Trajectory]) -> GeneratedSkill:
        """Mock generator for testing without an LLM API key."""
        traj = trajectories[0] if trajectories else None
        domain = traj.domain if traj else "general"
        task_id = traj.task_id if traj else "mock-task"
        name = f"generated-{task_id.lower().replace('_', '-')}"

        skill_md = textwrap.dedent(f"""\
            ---
            name: {name}
            description: Use this skill when handling {domain} tasks similar to {task_id}.
            version: "0.1.0"
            license: apache-2.0
            metadata:
              owner: generated
              domain: {domain}
              tags: [generated, {domain}]
            ---

            # {name.replace('-', ' ').title()}

            ## Purpose

            Handle {domain} tasks of the type described in trajectory {task_id}.

            ## When to use

            Use this skill when:
            - The task involves {domain} domain operations
            - Existing templates do not cover the scenario

            ## Procedure

            1. Analyze the input request
            2. Extract key parameters
            3. Generate output matching the required schema
            4. Validate the output

            ## Gotchas

            - This skill was auto-generated from a mock provider
            - Review and refine before adding to the registry

            ## Validation

            Run the validator script if available.
        """)

        return GeneratedSkill(
            skill_md=skill_md,
            provider="mock",
            model="mock",
            prompt_tokens=0,
            completion_tokens=0,
        )

    # ── helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Remove markdown code fences if the LLM wrapped the output."""
        text = text.strip()
        # Remove ```markdown ... ``` or ``` ... ```
        text = re.sub(r"^```[a-z]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
        return text.strip()

    @staticmethod
    def _extract_name(skill_md: str) -> str | None:
        """Extract the name field from SKILL.md frontmatter."""
        match = re.search(r"^name:\s*(.+)$", skill_md, re.MULTILINE)
        if match:
            return match.group(1).strip().strip('"').strip("'")
        return None

