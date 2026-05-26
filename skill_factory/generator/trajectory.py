"""Trajectory data model: captures a task run for skill extraction."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrajectoryStep:
    """One step in a task execution trajectory."""
    step: int
    action: str          # e.g. "retrieve_template", "generate", "validate"
    input: str
    output: str
    success: bool
    notes: str = ""


@dataclass
class Trajectory:
    """
    A complete task execution record used to extract skills.

    Fields:
        task_id:        Unique identifier for this task run.
        user_request:   The original user-facing request.
        steps:          Ordered list of execution steps.
        final_output:   The final output produced.
        passed:         Whether the task ultimately succeeded.
        failure_reason: Why it failed, if applicable.
        human_correction: The corrected output provided by a human reviewer.
        correction_notes: Explanation of what was wrong and why.
        schema_errors:  List of schema validation errors encountered.
        domain:         Domain label (e.g. "smart-home", "iot").
        metadata:       Arbitrary extra context.
    """
    task_id: str
    user_request: str
    steps: list[TrajectoryStep] = field(default_factory=list)
    final_output: str = ""
    passed: bool = False
    failure_reason: str = ""
    human_correction: str = ""
    correction_notes: str = ""
    schema_errors: list[str] = field(default_factory=list)
    domain: str = "general"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Trajectory":
        steps = [TrajectoryStep(**s) for s in data.get("steps", [])]
        return cls(
            task_id=data["task_id"],
            user_request=data["user_request"],
            steps=steps,
            final_output=data.get("final_output", ""),
            passed=data.get("passed", False),
            failure_reason=data.get("failure_reason", ""),
            human_correction=data.get("human_correction", ""),
            correction_notes=data.get("correction_notes", ""),
            schema_errors=data.get("schema_errors", []),
            domain=data.get("domain", "general"),
            metadata=data.get("metadata", {}),
        )
