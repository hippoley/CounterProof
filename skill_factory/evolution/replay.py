"""Deterministic command-based replay for EvoPR.

The runner deliberately keeps the contract small: a project supplies two argv lists
for the same case (baseline and candidate). Exit code 0 means the case passed.
This makes the first real replay adapter usable with any language or agent harness.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import ReplayResult


@dataclass(frozen=True)
class CommandOutcome:
    argv: tuple[str, ...]
    returncode: int | None
    duration_ms: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def score(self) -> float:
        return 0.0 if self.timed_out or self.returncode != 0 else 1.0


@dataclass(frozen=True)
class ExecutedReplay:
    result: ReplayResult
    baseline: CommandOutcome
    candidate: CommandOutcome


def _safe_cwd(root: Path, relative: str) -> Path:
    root = root.resolve()
    cwd = (root / relative).resolve()
    if cwd != root and root not in cwd.parents:
        raise ValueError(f"replay cwd escapes root: {relative}")
    return cwd


def _run(
    argv: list[str],
    *,
    cwd: Path,
    timeout_seconds: float,
    env: dict[str, str] | None = None,
) -> CommandOutcome:
    if not argv or not all(isinstance(part, str) and part for part in argv):
        raise ValueError("replay command must be a non-empty argv list")

    started = time.perf_counter()
    merged_env = os.environ.copy()
    if env:
        merged_env.update({str(k): str(v) for k, v in env.items()})

    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=merged_env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        duration_ms = round((time.perf_counter() - started) * 1000)
        return CommandOutcome(
            argv=tuple(argv),
            returncode=proc.returncode,
            duration_ms=duration_ms,
            stdout=proc.stdout[-4000:],
            stderr=proc.stderr[-4000:],
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = round((time.perf_counter() - started) * 1000)
        return CommandOutcome(
            argv=tuple(argv),
            returncode=None,
            duration_ms=duration_ms,
            stdout=(exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            stderr=(exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            timed_out=True,
        )


def run_replay_manifest(path: Path) -> tuple[ExecutedReplay, ...]:
    """Execute all baseline/candidate command pairs in a replay manifest."""
    path = path.resolve()
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    root = _safe_cwd(path.parent, raw.get("root", "."))
    default_timeout = float(raw.get("timeout_seconds", 30))
    results: list[ExecutedReplay] = []

    for case in raw.get("cases", []):
        case_id = str(case["case_id"])
        suite = str(case.get("suite", "replay"))
        cwd = _safe_cwd(root, str(case.get("cwd", ".")))
        timeout = float(case.get("timeout_seconds", default_timeout))
        env = {"EVOPR_CASE_ID": case_id, **case.get("env", {})}

        baseline = _run(
            list(case["baseline"]),
            cwd=cwd,
            timeout_seconds=timeout,
            env=env,
        )
        candidate = _run(
            list(case["candidate"]),
            cwd=cwd,
            timeout_seconds=timeout,
            env=env,
        )

        verdict = "infra_error" if candidate.timed_out else (
            "pass" if candidate.returncode == 0 else "fail"
        )
        result = ReplayResult(
            case_id=case_id,
            suite=suite,
            verdict=verdict,
            baseline_score=baseline.score,
            candidate_score=candidate.score,
            note=(
                f"baseline rc={baseline.returncode}, candidate rc={candidate.returncode}; "
                f"{baseline.duration_ms}ms/{candidate.duration_ms}ms"
            ),
        )
        results.append(
            ExecutedReplay(
                result=result,
                baseline=baseline,
                candidate=candidate,
            )
        )

    if not results:
        raise ValueError("replay manifest contains no cases")
    return tuple(results)


def serialize_replays(executed: tuple[ExecutedReplay, ...]) -> dict[str, Any]:
    return {
        "cases": [
            {
                "case_id": item.result.case_id,
                "suite": item.result.suite,
                "verdict": item.result.verdict,
                "baseline_score": item.result.baseline_score,
                "candidate_score": item.result.candidate_score,
                "delta": item.result.delta,
                "note": item.result.note,
                "baseline": {
                    "argv": list(item.baseline.argv),
                    "returncode": item.baseline.returncode,
                    "duration_ms": item.baseline.duration_ms,
                    "stdout": item.baseline.stdout,
                    "stderr": item.baseline.stderr,
                    "timed_out": item.baseline.timed_out,
                },
                "candidate": {
                    "argv": list(item.candidate.argv),
                    "returncode": item.candidate.returncode,
                    "duration_ms": item.candidate.duration_ms,
                    "stdout": item.candidate.stdout,
                    "stderr": item.candidate.stderr,
                    "timed_out": item.candidate.timed_out,
                },
            }
            for item in executed
        ]
    }
