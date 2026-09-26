"""Local one-command Counterproof check for the current Git branch."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .integrity import ProofIntegrityReport, inspect_proof_integrity
from .onboarding import TestRunnerDetection, detect_test_runner
from .witness import RegressionWitness, run_regression_witness


@dataclass(frozen=True)
class LocalCheckResult:
    repo_root: Path
    base_ref: str
    base_commit: str
    detection: TestRunnerDetection
    witness: RegressionWitness
    integrity: ProofIntegrityReport

    @property
    def ready(self) -> bool:
        return self.witness.witnessed and self.integrity.status == "clean"

    @property
    def status(self) -> str:
        if self.integrity.status != "clean":
            return "review-required"
        if self.witness.witnessed:
            return "verified"
        return self.witness.status


def _git(repo_root: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _ref_exists(repo_root: Path, ref: str) -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.returncode == 0


def _remote_default_ref(repo_root: Path) -> str | None:
    symbolic = _git(
        repo_root,
        "symbolic-ref",
        "--quiet",
        "--short",
        "refs/remotes/origin/HEAD",
        check=False,
    )
    return symbolic or None


def resolve_base_ref(repo_root: Path, explicit: str | None = None) -> tuple[str, str]:
    """Resolve a comparison ref and its merge-base with HEAD.

    Preference order:
    1. explicit --base
    2. origin/HEAD symbolic default
    3. origin/main, origin/master
    4. main, master
    """
    repo_root = repo_root.resolve()
    if not (repo_root / ".git").exists():
        raise ValueError(f"not a Git repository: {repo_root}")

    if explicit is not None:
        candidates = [explicit]
    else:
        candidates: list[str] = []
        remote_default = _remote_default_ref(repo_root)
        if remote_default:
            candidates.append(remote_default)
        candidates.extend(["origin/main", "origin/master", "main", "master"])

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if not _ref_exists(repo_root, candidate):
            continue
        merge_base = _git(repo_root, "merge-base", "HEAD", candidate, check=False)
        if merge_base:
            return candidate, merge_base

    if explicit is not None:
        raise ValueError(f"could not resolve base ref: {explicit}")
    raise ValueError(
        "could not infer a base branch; pass --base explicitly "
        "(for example origin/main)"
    )


def run_local_check(
    repo_root: Path,
    *,
    base_ref: str | None = None,
    test_command: str | None = None,
    timeout_seconds: float = 300,
    result_protocol: str = "exit-code",
) -> LocalCheckResult:
    """Run Regression Witness + Proof Integrity with local auto-detection."""
    repo_root = repo_root.resolve()
    resolved_ref, base_commit = resolve_base_ref(repo_root, base_ref)
    detection = (
        TestRunnerDetection(
            command=test_command,
            runner="custom",
            confidence="explicit",
            evidence=("--test-command",),
        )
        if test_command is not None
        else detect_test_runner(repo_root)
    )

    witness = run_regression_witness(
        repo_root,
        base_ref=base_commit,
        head_ref="HEAD",
        test_command=detection.command,
        timeout_seconds=timeout_seconds,
        result_protocol=result_protocol,
    )
    integrity = inspect_proof_integrity(
        repo_root,
        base_ref=base_commit,
        head_ref="HEAD",
    )
    return LocalCheckResult(
        repo_root=repo_root,
        base_ref=resolved_ref,
        base_commit=base_commit,
        detection=detection,
        witness=witness,
        integrity=integrity,
    )


def local_check_to_dict(result: LocalCheckResult) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": result.status,
        "ready": result.ready,
        "base_ref": result.base_ref,
        "base_commit": result.base_commit,
        "runner": {
            "name": result.detection.runner,
            "command": result.detection.command,
            "confidence": result.detection.confidence,
            "evidence": list(result.detection.evidence),
        },
        "witness": {
            "status": result.witness.status,
            "mode": result.witness.mode,
            "witnessed": result.witness.witnessed,
            "changed_tests": list(result.witness.tests),
        },
        "integrity": {
            "status": result.integrity.status,
            "findings": len(result.integrity.findings),
            "high_risk": result.integrity.high_risk_count,
        },
    }


def render_local_check(result: LocalCheckResult) -> str:
    status = result.status.upper().replace("-", " ")
    ready = "YES" if result.ready else "NO"
    lines = [
        "Counterproof local check",
        "",
        f"Status           {status}",
        f"Proof ready      {ready}",
        f"Base             {result.base_ref}",
        f"Base commit      {result.base_commit[:12]}",
        f"Runner           {result.detection.runner}",
        f"Command          {result.detection.command}",
        "",
        f"Regression       {result.witness.status.upper().replace('-', ' ')}",
        f"Evidence mode    {result.witness.mode.upper()}",
        f"Changed tests    {len(result.witness.tests)}",
        f"Proof integrity  {result.integrity.status.upper().replace('-', ' ')}",
        f"Integrity risks  {len(result.integrity.findings)}",
    ]
    if result.ready:
        lines.extend(
            [
                "",
                "The exact changed-test evidence distinguishes HEAD from BASE",
                "and Counterproof did not detect a changed evidence surface.",
            ]
        )
    elif result.witness.status == "no-changed-tests":
        lines.extend(
            [
                "",
                "No changed regression test was detected.",
                "Add or modify a test that captures the fix, then run counterproof check again.",
            ]
        )
    elif result.integrity.status != "clean":
        lines.extend(
            [
                "",
                "The PR changes evidence-producing surfaces.",
                "Review those changes before treating the witness as independent proof.",
            ]
        )
    return "\n".join(lines) + "\n"


def local_check_json(result: LocalCheckResult) -> str:
    return json.dumps(local_check_to_dict(result), indent=2, ensure_ascii=False)
