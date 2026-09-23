"""Deterministic command-based replay for Counterproof.

The legacy contract treats exit code 0 as behavioral PASS. The optional json-v1
protocol separates adapter execution from behavioral outcome and supports continuous
scores plus structured evidence.
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

RESULT_PREFIXES = ("COUNTERPROOF_RESULT=", "EVOPR_RESULT=")


@dataclass(frozen=True)
class StructuredProbeResult:
    verdict: str
    score: float
    metrics: dict[str, Any]
    observations: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()


@dataclass(frozen=True)
class BehavioralOutcome:
    verdict: str
    score: float
    note: str = ""


@dataclass(frozen=True)
class CommandOutcome:
    argv: tuple[str, ...]
    returncode: int | None
    duration_ms: int
    stdout: str
    stderr: str
    timed_out: bool = False
    probe_result: StructuredProbeResult | None = None
    probe_result_error: str | None = None

    @property
    def score(self) -> float:
        return 0.0 if self.timed_out or self.returncode != 0 else 1.0


def parse_structured_probe_result(stdout: str) -> StructuredProbeResult | None:
    """Parse the last Counterproof structured-result line from adapter stdout."""
    payload_text: str | None = None
    for line in reversed(stdout.splitlines()):
        stripped = line.strip()
        for prefix in RESULT_PREFIXES:
            if stripped.startswith(prefix):
                payload_text = stripped[len(prefix) :].strip()
                break
        if payload_text is not None:
            break

    if payload_text is None:
        return None

    try:
        raw = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid COUNTERPROOF_RESULT JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise TypeError("COUNTERPROOF_RESULT must be a JSON object")

    verdict = raw.get("verdict")
    if verdict not in {"pass", "fail"}:
        raise ValueError("COUNTERPROOF_RESULT verdict must be 'pass' or 'fail'")

    default_score = 1.0 if verdict == "pass" else 0.0
    try:
        score = float(raw.get("score", default_score))
    except (TypeError, ValueError) as exc:
        raise ValueError("COUNTERPROOF_RESULT score must be numeric") from exc
    if not 0.0 <= score <= 1.0:
        raise ValueError("COUNTERPROOF_RESULT score must be between 0 and 1")

    metrics = raw.get("metrics", {})
    if not isinstance(metrics, dict):
        raise TypeError("COUNTERPROOF_RESULT metrics must be an object")

    observations = raw.get("observations", [])
    if (
        not isinstance(observations, list)
        or not all(isinstance(item, str) for item in observations)
    ):
        raise ValueError("COUNTERPROOF_RESULT observations must be a list of strings")

    artifacts = raw.get("artifacts", [])
    if (
        not isinstance(artifacts, list)
        or not all(isinstance(item, str) for item in artifacts)
    ):
        raise ValueError("COUNTERPROOF_RESULT artifacts must be a list of strings")

    return StructuredProbeResult(
        verdict=verdict,
        score=score,
        metrics=metrics,
        observations=tuple(observations),
        artifacts=tuple(artifacts),
    )


def interpret_command_outcome(
    outcome: CommandOutcome,
    *,
    protocol: str,
) -> BehavioralOutcome:
    """Convert process execution into behavioral evidence under the selected protocol."""
    if protocol not in {"exit-code", "json-v1"}:
        raise ValueError(f"unknown result protocol: {protocol}")

    if outcome.timed_out:
        return BehavioralOutcome("infra_error", 0.0, "command timed out")

    if protocol == "exit-code":
        verdict = "pass" if outcome.returncode == 0 else "fail"
        score = 1.0 if verdict == "pass" else 0.0
        return BehavioralOutcome(
            verdict,
            score,
            f"exit-code protocol rc={outcome.returncode}",
        )

    if outcome.returncode != 0:
        return BehavioralOutcome(
            "infra_error",
            0.0,
            f"json-v1 adapter exited non-zero rc={outcome.returncode}",
        )
    if outcome.probe_result_error:
        return BehavioralOutcome(
            "infra_error",
            0.0,
            outcome.probe_result_error,
        )
    if outcome.probe_result is None:
        return BehavioralOutcome(
            "infra_error",
            0.0,
            "json-v1 adapter did not emit COUNTERPROOF_RESULT",
        )

    return BehavioralOutcome(
        outcome.probe_result.verdict,
        outcome.probe_result.score,
        "json-v1 structured probe result",
    )


def structured_probe_result_to_dict(
    result: StructuredProbeResult | None,
) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "verdict": result.verdict,
        "score": result.score,
        "metrics": result.metrics,
        "observations": list(result.observations),
        "artifacts": list(result.artifacts),
    }


@dataclass(frozen=True)
class ExecutedReplay:
    result: ReplayResult
    baseline: CommandOutcome
    candidate: CommandOutcome


def resolve_declared_root(manifest_dir: Path, relative: str) -> Path:
    """Resolve the user-declared replay root relative to the manifest."""
    return (manifest_dir.resolve() / relative).resolve()


def safe_cwd(root: Path, relative: str) -> Path:
    """Resolve a case cwd while preventing escape from the declared replay root."""
    root = root.resolve()
    cwd = (root / relative).resolve()
    if cwd != root and root not in cwd.parents:
        raise ValueError(f"replay cwd escapes declared root: {relative}")
    return cwd


def run_command(
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
        stdout = proc.stdout[-4000:]
        probe_result = None
        probe_result_error = None
        try:
            probe_result = parse_structured_probe_result(stdout)
        except (TypeError, ValueError) as exc:
            probe_result_error = str(exc)

        return CommandOutcome(
            argv=tuple(argv),
            returncode=proc.returncode,
            duration_ms=duration_ms,
            stdout=stdout,
            stderr=proc.stderr[-4000:],
            probe_result=probe_result,
            probe_result_error=probe_result_error,
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
    root = resolve_declared_root(path.parent, str(raw.get("root", ".")))
    default_timeout = float(raw.get("timeout_seconds", 30))
    default_protocol = str(raw.get("result_protocol", "exit-code"))
    if default_protocol not in {"exit-code", "json-v1"}:
        raise ValueError(f"unknown result protocol: {default_protocol}")
    results: list[ExecutedReplay] = []

    for case in raw.get("cases", []):
        case_id = str(case["case_id"])
        suite = str(case.get("suite", "replay"))
        cwd = safe_cwd(root, str(case.get("cwd", ".")))
        timeout = float(case.get("timeout_seconds", default_timeout))
        protocol = str(case.get("result_protocol", default_protocol))
        if protocol not in {"exit-code", "json-v1"}:
            raise ValueError(f"unknown result protocol: {protocol}")
        env = {
            "COUNTERPROOF_CASE_ID": case_id,
            "EVOPR_CASE_ID": case_id,
            **case.get("env", {}),
        }

        baseline = run_command(
            list(case["baseline"]),
            cwd=cwd,
            timeout_seconds=timeout,
            env=env,
        )
        candidate = run_command(
            list(case["candidate"]),
            cwd=cwd,
            timeout_seconds=timeout,
            env=env,
        )

        baseline_behavior = interpret_command_outcome(
            baseline,
            protocol=protocol,
        )
        candidate_behavior = interpret_command_outcome(
            candidate,
            protocol=protocol,
        )
        result = ReplayResult(
            case_id=case_id,
            suite=suite,
            verdict=candidate_behavior.verdict,
            baseline_score=baseline_behavior.score,
            candidate_score=candidate_behavior.score,
            note=(
                f"protocol={protocol}; baseline rc={baseline.returncode}, "
                f"candidate rc={candidate.returncode}; "
                f"{baseline.duration_ms}ms/{candidate.duration_ms}ms; "
                f"candidate={candidate_behavior.note}"
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
                    "probe_result": structured_probe_result_to_dict(
                        item.baseline.probe_result
                    ),
                    "probe_result_error": item.baseline.probe_result_error,
                },
                "candidate": {
                    "argv": list(item.candidate.argv),
                    "returncode": item.candidate.returncode,
                    "duration_ms": item.candidate.duration_ms,
                    "stdout": item.candidate.stdout,
                    "stderr": item.candidate.stderr,
                    "timed_out": item.candidate.timed_out,
                    "probe_result": structured_probe_result_to_dict(
                        item.candidate.probe_result
                    ),
                    "probe_result_error": item.candidate.probe_result_error,
                },
            }
            for item in executed
        ]
    }
