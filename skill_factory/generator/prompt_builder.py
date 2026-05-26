"""Builds LLM prompts for skill generation from trajectories."""
from __future__ import annotations
from skill_factory.generator.trajectory import Trajectory


SKILL_GENERATION_SYSTEM_PROMPT = """You are a Skill Engineer. Your job is to extract reusable,
generalizable agent skills from task execution trajectories and human feedback.

A skill is NOT a one-off solution. It must:
- Apply to a class of similar tasks, not just the specific example
- Include clear trigger conditions (when to use it)
- Include concrete procedures (how to execute it)
- Include gotchas (what to avoid)
- Include validation steps

Output a complete SKILL.md file with YAML frontmatter and Markdown body.
The frontmatter must include: name, description, version, license, metadata.
The body must include: Purpose, When to use, Procedure, Gotchas, Validation.
"""


def build_skill_generation_prompt(trajectories: list[Trajectory]) -> str:
    """Build a prompt for skill generation from one or more trajectories."""
    parts = [SKILL_GENERATION_SYSTEM_PROMPT, "\n\n## Task Trajectories\n"]

    for i, traj in enumerate(trajectories, 1):
        parts.append(f"\n### Trajectory {i}: {traj.task_id}\n")
        parts.append(f"**User Request:** {traj.user_request}\n")
        parts.append(f"**Domain:** {traj.domain}\n")
        parts.append(f"**Outcome:** {'PASSED' if traj.passed else 'FAILED'}\n")

        if traj.failure_reason:
            parts.append(f"**Failure Reason:** {traj.failure_reason}\n")

        if traj.schema_errors:
            parts.append("**Schema Errors:**\n")
            for err in traj.schema_errors:
                parts.append(f"  - {err}\n")

        if traj.human_correction:
            parts.append(f"**Human Correction:** {traj.human_correction}\n")

        if traj.correction_notes:
            parts.append(f"**Correction Notes:** {traj.correction_notes}\n")

        if traj.steps:
            parts.append("**Steps:**\n")
            for step in traj.steps:
                status = "OK" if step.success else "FAIL"
                parts.append(f"  {step.step}. [{status}] {step.action}: {step.notes}\n")

    parts.append("\n## Your Task\n")
    parts.append(
        "Based on the trajectories above, generate a SKILL.md that captures the "
        "generalizable knowledge needed to handle this class of tasks correctly. "
        "Focus on what went wrong, why, and how to prevent it in future runs."
    )

    return "".join(parts)
