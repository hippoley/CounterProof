"""A/B evaluator: compares task performance with skill vs without skill."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Callable

from skill_factory.models import EvalCase, EvalReport, EvalResult, Skill


# Type alias for a task runner function
# Signature: (task: str, skill_content: str | None) -> (passed: bool, score: float, tokens: int)
TaskRunner = Callable[[str, str | None], tuple[bool, float, int]]


def load_eval_cases(evals_dir: Path) -> list[EvalCase]:
    """Load eval cases from evals/evals.json."""
    evals_file = evals_dir / "evals.json"
    if not evals_file.exists():
        raise FileNotFoundError(f"evals.json not found in {evals_dir}")
    raw = json.loads(evals_file.read_text())
    cases = []
    for item in raw.get("cases", []):
        cases.append(
            EvalCase(
                id=item["id"],
                task=item["task"],
                expected_pass=item.get("expected_pass", True),
                verifier=item.get("verifier", "schema"),
                metadata=item.get("metadata", {}),
            )
        )
    return cases


def run_ab_eval(
    skill: Skill,
    runner: TaskRunner,
    cases: list[EvalCase] | None = None,
) -> EvalReport:
    """
    Run A/B evaluation: each case is run twice (without skill, with skill).

    Args:
        skill: The skill to evaluate.
        runner: A callable that executes a task and returns (passed, score, tokens).
        cases: Optional list of EvalCase. If None, loads from skill's evals/ directory.

    Returns:
        EvalReport with baseline and with-skill metrics.
    """
    if cases is None:
        cases = load_eval_cases(skill.path / "evals")

    baseline_results: list[EvalResult] = []
    skill_results: list[EvalResult] = []

    for case in cases:
        # Baseline: no skill
        t0 = time.monotonic()
        passed_b, score_b, tokens_b = runner(case.task, None)
        latency_b = (time.monotonic() - t0) * 1000
        baseline_results.append(
            EvalResult(
                case_id=case.id,
                with_skill=False,
                passed=passed_b,
                score=score_b,
                tokens_used=tokens_b,
                latency_ms=latency_b,
            )
        )

        # With skill
        t0 = time.monotonic()
        passed_s, score_s, tokens_s = runner(case.task, skill.content)
        latency_s = (time.monotonic() - t0) * 1000
        skill_results.append(
            EvalResult(
                case_id=case.id,
                with_skill=True,
                passed=passed_s,
                score=score_s,
                tokens_used=tokens_s,
                latency_ms=latency_s,
            )
        )

    n = len(cases)
    baseline_pass_rate = sum(r.passed for r in baseline_results) / n if n else 0.0
    skill_pass_rate = sum(r.passed for r in skill_results) / n if n else 0.0
    avg_tokens_b = sum(r.tokens_used for r in baseline_results) / n if n else 0.0
    avg_tokens_s = sum(r.tokens_used for r in skill_results) / n if n else 0.0
    avg_latency_b = sum(r.latency_ms for r in baseline_results) / n if n else 0.0
    avg_latency_s = sum(r.latency_ms for r in skill_results) / n if n else 0.0

    return EvalReport(
        skill_name=skill.name,
        skill_version=skill.meta.version,
        baseline_pass_rate=baseline_pass_rate,
        with_skill_pass_rate=skill_pass_rate,
        delta=skill_pass_rate - baseline_pass_rate,
        token_delta=avg_tokens_s - avg_tokens_b,
        latency_delta_ms=avg_latency_s - avg_latency_b,
        cases=baseline_results + skill_results,
    )
