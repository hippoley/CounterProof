"""Regression Witness: prove changed tests fail before a PR fix and pass after it."""
from __future__ import annotations

import fnmatch
import json
import os
import shlex
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_TEST_PATTERNS = (
    "tests/**",
    "test/**",
    "**/test_*.py",
    "**/*_test.py",
    "**/*.test.js",
    "**/*.test.ts",
    "**/*.spec.js",
    "**/*.spec.ts",
    "**/__tests__/**",
)


@dataclass(frozen=True)
class WitnessCommand:
    argv: tuple[str, ...]
    returncode: int | None
    duration_ms: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def passed(self) -> bool:
        return not self.timed_out and self.returncode == 0


@dataclass(frozen=True)
class RegressionWitness:
    base_ref: str
    head_ref: str
    tests: tuple[str, ...]
    head: WitnessCommand | None
    base_with_head_tests: WitnessCommand | None
    status: str
    note: str

    @property
    def witnessed(self) -> bool:
        return self.status == "witnessed"


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout.strip()


def _is_test_file(path: str, patterns: tuple[str, ...]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def changed_test_files(
    repo_root: Path,
    *,
    base_ref: str,
    head_ref: str = "HEAD",
    patterns: tuple[str, ...] = DEFAULT_TEST_PATTERNS,
) -> tuple[str, ...]:
    """Return changed/added test files between base and head."""
    raw = _git(
        repo_root,
        "diff",
        "--name-only",
        "--diff-filter=ACMR",
        f"{base_ref}...{head_ref}",
        "--",
    )
    files = []
    for line in raw.splitlines():
        path = line.strip()
        if path and _is_test_file(path, patterns):
            files.append(path)
    return tuple(dict.fromkeys(files))


def _build_test_argv(command: str, tests: tuple[str, ...]) -> tuple[str, ...]:
    parts = shlex.split(command)
    if not parts:
        raise ValueError("test command must not be empty")

    argv: list[str] = []
    expanded = False
    for part in parts:
        if part == "{tests}":
            argv.extend(tests)
            expanded = True
        else:
            argv.append(part)
    if not expanded:
        argv.extend(tests)
    return tuple(argv)


def _run(
    argv: tuple[str, ...],
    *,
    cwd: Path,
    timeout_seconds: float,
    env: dict[str, str] | None = None,
) -> WitnessCommand:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            list(argv),
            cwd=cwd,
            env={**os.environ, **(env or {})},
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return WitnessCommand(
            argv=argv,
            returncode=None,
            duration_ms=duration_ms,
            stdout=(exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            stderr=(exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            timed_out=True,
        )

    duration_ms = int((time.perf_counter() - started) * 1000)
    return WitnessCommand(
        argv=argv,
        returncode=proc.returncode,
        duration_ms=duration_ms,
        stdout=proc.stdout[-4000:],
        stderr=proc.stderr[-4000:],
    )


def _safe_relative_file(repo_root: Path, relative: str) -> Path:
    target = (repo_root / relative).resolve()
    root = repo_root.resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"test path escapes repository: {relative}") from exc
    if not target.is_file():
        raise ValueError(f"changed test file does not exist at head: {relative}")
    return target


def run_regression_witness(
    repo_root: Path,
    *,
    base_ref: str,
    head_ref: str = "HEAD",
    test_command: str,
    timeout_seconds: float = 300,
    patterns: tuple[str, ...] = DEFAULT_TEST_PATTERNS,
) -> RegressionWitness:
    """Run changed head tests on head and on base code with those tests overlaid."""
    repo_root = repo_root.resolve()
    tests = changed_test_files(
        repo_root,
        base_ref=base_ref,
        head_ref=head_ref,
        patterns=patterns,
    )
    if not tests:
        return RegressionWitness(
            base_ref=base_ref,
            head_ref=head_ref,
            tests=(),
            head=None,
            base_with_head_tests=None,
            status="no-changed-tests",
            note="No changed test files matched the configured patterns.",
        )

    argv = _build_test_argv(test_command, tests)
    head = _run(
        argv,
        cwd=repo_root,
        timeout_seconds=timeout_seconds,
        env={"COUNTERPROOF_WITNESS_SIDE": "head"},
    )
    if not head.passed:
        return RegressionWitness(
            base_ref=base_ref,
            head_ref=head_ref,
            tests=tests,
            head=head,
            base_with_head_tests=None,
            status="head-failing",
            note="Changed tests do not pass on the PR head; no proof-of-fix can be claimed.",
        )

    with tempfile.TemporaryDirectory(prefix="counterproof-witness-") as tmp:
        base_dir = Path(tmp) / "base"
        _git(repo_root, "worktree", "add", "--detach", str(base_dir), base_ref)
        try:
            for relative in tests:
                source = _safe_relative_file(repo_root, relative)
                destination = base_dir / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)

            baseline = _run(
                argv,
                cwd=base_dir,
                timeout_seconds=timeout_seconds,
                env={"COUNTERPROOF_WITNESS_SIDE": "base-with-head-tests"},
            )
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(base_dir)],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

    if baseline.timed_out:
        status = "inconclusive"
        note = "Base-with-head-tests timed out; witness is inconclusive."
    elif baseline.returncode == 0:
        status = "not-witnessed"
        note = (
            "Changed tests pass on both base and head. They do not demonstrate the claimed "
            "behavioral regression."
        )
    else:
        status = "witnessed"
        note = (
            "The PR's changed tests pass on head and fail when replayed against base code. "
            "This is a regression witness for the tested behavior."
        )

    return RegressionWitness(
        base_ref=base_ref,
        head_ref=head_ref,
        tests=tests,
        head=head,
        base_with_head_tests=baseline,
        status=status,
        note=note,
    )


def _command_to_dict(command: WitnessCommand | None) -> dict[str, Any] | None:
    if command is None:
        return None
    return {
        "argv": list(command.argv),
        "returncode": command.returncode,
        "duration_ms": command.duration_ms,
        "timed_out": command.timed_out,
        "stdout": command.stdout,
        "stderr": command.stderr,
    }


def witness_to_dict(witness: RegressionWitness) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "base_ref": witness.base_ref,
        "head_ref": witness.head_ref,
        "tests": list(witness.tests),
        "status": witness.status,
        "witnessed": witness.witnessed,
        "note": witness.note,
        "head": _command_to_dict(witness.head),
        "base_with_head_tests": _command_to_dict(witness.base_with_head_tests),
    }


def render_witness_markdown(witness: RegressionWitness) -> str:
    badge = {
        "witnessed": "WITNESSED",
        "not-witnessed": "NOT WITNESSED",
        "head-failing": "HEAD FAILING",
        "no-changed-tests": "NO CHANGED TESTS",
        "inconclusive": "INCONCLUSIVE",
    }.get(witness.status, witness.status.upper())

    lines = [
        "# Counterproof · Regression Witness",
        "",
        f"## {badge}",
        "",
        witness.note,
        "",
        f"- **Base:** \`{witness.base_ref}\`",
        f"- **Head:** \`{witness.head_ref}\`",
        f"- **Changed tests:** {len(witness.tests)}",
    ]

    if witness.tests:
        lines.extend(["", "### Tests replayed", ""])
        lines.extend(f"- \`{path}\`" for path in witness.tests)

    lines.extend(["", "### Behavior", ""])
    if witness.head is not None:
        lines.append(
            f"- PR head: **{'PASS' if witness.head.passed else 'FAIL'}** "
            f"({witness.head.duration_ms} ms)"
        )
    if witness.base_with_head_tests is not None:
        lines.append(
            "- Base code + PR tests: "
            f"**{'PASS' if witness.base_with_head_tests.passed else 'FAIL'}** "
            f"({witness.base_with_head_tests.duration_ms} ms)"
        )

    if witness.witnessed:
        lines.extend(
            [
                "",
                "> The same changed tests fail before the fix and pass after it.",
                "> This proves the tested regression delta; it does not prove every claimed cause.",
            ]
        )
    return "\n".join(lines) + "\n"


def write_witness_json(path: Path, witness: RegressionWitness) -> None:
    path.write_text(
        json.dumps(witness_to_dict(witness), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
