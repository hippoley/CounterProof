"""Regression Witness: prove changed tests fail before a PR fix and pass after it."""
from __future__ import annotations

import fnmatch
import hashlib
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
    "**/test_*.py",
    "**/*_test.py",
    "**/*_test.go",
    "**/*_spec.rb",
    "**/*Test.java",
    "**/*Tests.java",
    "**/*Test.kt",
    "**/*Tests.kt",
    "**/*Spec.kt",
    "**/*Test.cs",
    "**/*Tests.cs",
    "**/*_test.cc",
    "**/*_test.cpp",
    "**/test_*.cc",
    "**/test_*.cpp",
    "**/*.test.js",
    "**/*.test.ts",
    "**/*.test.jsx",
    "**/*.test.tsx",
    "**/*.spec.js",
    "**/*.spec.ts",
    "**/*.spec.jsx",
    "**/*.spec.tsx",
    "**/__tests__/**",
)

DEFAULT_SUPPORT_PATTERNS = (
    "tests/**",
    "test/**",
    "spec/**",
    "src/test/**",
    "**/__tests__/**",
    "**/testdata/**",
    "**/fixtures/**",
    "**/__fixtures__/**",
    "conftest.py",
    "**/conftest.py",
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
    mode: str = "precise"
    support_files: tuple[str, ...] = ()
    base_sha: str | None = None
    head_sha: str | None = None

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


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def _changed_files(
    repo_root: Path,
    *,
    base_ref: str,
    head_ref: str,
) -> tuple[str, ...]:
    raw = _git(
        repo_root,
        "diff",
        "--name-only",
        "--diff-filter=ACMR",
        f"{base_ref}..{head_ref}",
        "--",
    )
    return tuple(line.strip() for line in raw.splitlines() if line.strip())


def changed_test_files(
    repo_root: Path,
    *,
    base_ref: str,
    head_ref: str = "HEAD",
    patterns: tuple[str, ...] = DEFAULT_TEST_PATTERNS,
) -> tuple[str, ...]:
    """Return changed/added test files between base and head."""
    return tuple(
        path
        for path in _changed_files(
            repo_root,
            base_ref=base_ref,
            head_ref=head_ref,
        )
        if _matches(path, patterns)
    )


def changed_test_support_files(
    repo_root: Path,
    *,
    base_ref: str,
    head_ref: str = "HEAD",
    patterns: tuple[str, ...] = DEFAULT_SUPPORT_PATTERNS,
) -> tuple[str, ...]:
    """Return changed support files needed to replay changed tests on base."""
    return tuple(
        path
        for path in _changed_files(
            repo_root,
            base_ref=base_ref,
            head_ref=head_ref,
        )
        if _matches(path, patterns)
    )


def _build_test_argv(
    command: str,
    tests: tuple[str, ...],
) -> tuple[tuple[str, ...], str]:
    parts = shlex.split(command)
    if not parts:
        raise ValueError("test command must not be empty")

    precise = "{tests}" in parts
    argv: list[str] = []
    for part in parts:
        if part == "{tests}":
            argv.extend(tests)
        else:
            argv.append(part)
    return tuple(argv), ("precise" if precise else "suite")


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
        raise ValueError(f"overlay path escapes repository: {relative}") from exc
    if not target.is_file():
        raise ValueError(f"overlay file does not exist at head: {relative}")
    return target


def _witness_env(cwd: Path, side: str) -> dict[str, str]:
    python_paths: list[str] = []
    src = cwd / "src"
    if src.is_dir():
        python_paths.append(str(src))
    python_paths.append(str(cwd))
    existing = os.environ.get("PYTHONPATH")
    if existing:
        python_paths.append(existing)
    return {
        "COUNTERPROOF_WITNESS_SIDE": side,
        "PYTHONPATH": os.pathsep.join(python_paths),
    }


def _link_dependency_dirs(head_root: Path, base_root: Path) -> None:
    """Reuse heavy dependency directories without overlaying HEAD source files."""
    for name in ("node_modules", ".venv", "venv"):
        source = head_root / name
        destination = base_root / name
        if not source.exists() or destination.exists():
            continue
        try:
            destination.symlink_to(source, target_is_directory=True)
        except OSError:
            pass


def _is_pytest_command(argv: tuple[str, ...]) -> bool:
    for index, part in enumerate(argv):
        if Path(part).name == "pytest":
            return True
        if part == "-m" and index + 1 < len(argv) and argv[index + 1] == "pytest":
            return True
    return False


def _classify_base_result(
    baseline: WitnessCommand,
    *,
    argv: tuple[str, ...],
    mode: str,
) -> tuple[str, str]:
    if baseline.timed_out:
        return (
            "inconclusive",
            "Base-with-head-tests timed out; witness is inconclusive.",
        )
    if baseline.returncode == 0:
        return (
            "not-witnessed",
            (
                "The configured test command passes on both base and head. "
                "It does not distinguish the pre-change code from the PR."
            ),
        )
    if _is_pytest_command(argv) and baseline.returncode != 1:
        return (
            "inconclusive",
            (
                f"Base pytest exited with code {baseline.returncode}. "
                "Only pytest exit 1 is accepted as an actual test-failure witness; "
                "collection, usage, internal, interruption, and no-tests exits are inconclusive."
            ),
        )
    if mode == "suite":
        return (
            "suite-delta",
            (
                "The configured full suite passes on head and fails on base with the PR's "
                "changed test support overlaid. This proves a suite-level before/after delta, "
                "but not that the changed test itself caused the base failure."
            ),
        )
    return (
        "witnessed",
        (
            "The PR's changed tests pass on head and fail when replayed against base code. "
            "This is a regression witness for the tested behavior."
        ),
    )


def run_regression_witness(
    repo_root: Path,
    *,
    base_ref: str,
    head_ref: str = "HEAD",
    test_command: str,
    timeout_seconds: float = 300,
    patterns: tuple[str, ...] = DEFAULT_TEST_PATTERNS,
) -> RegressionWitness:
    """Replay changed tests against HEAD and base with changed test support overlaid."""
    repo_root = repo_root.resolve()
    resolved_base_sha = _git(repo_root, "rev-parse", f"{base_ref}^{{commit}}")
    resolved_head_sha = _git(repo_root, "rev-parse", f"{head_ref}^{{commit}}")
    tests = changed_test_files(
        repo_root,
        base_ref=base_ref,
        head_ref=head_ref,
        patterns=patterns,
    )
    support_files = tuple(
        dict.fromkeys(
            (
                *tests,
                *changed_test_support_files(
                    repo_root,
                    base_ref=base_ref,
                    head_ref=head_ref,
                ),
            )
        )
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
            mode="precise" if "{tests}" in shlex.split(test_command) else "suite",
            support_files=(),
            base_sha=resolved_base_sha,
            head_sha=resolved_head_sha,
        )

    argv, mode = _build_test_argv(test_command, tests)
    head = _run(
        argv,
        cwd=repo_root,
        timeout_seconds=timeout_seconds,
        env=_witness_env(repo_root, "head"),
    )
    if not head.passed:
        return RegressionWitness(
            base_ref=base_ref,
            head_ref=head_ref,
            tests=tests,
            head=head,
            base_with_head_tests=None,
            status="head-failing",
            note="Configured tests do not pass on the PR head; no proof-of-fix can be claimed.",
            mode=mode,
            support_files=support_files,
            base_sha=resolved_base_sha,
            head_sha=resolved_head_sha,
        )

    with tempfile.TemporaryDirectory(prefix="counterproof-witness-") as tmp:
        base_dir = Path(tmp) / "base"
        _git(repo_root, "worktree", "add", "--detach", str(base_dir), resolved_base_sha)
        try:
            _link_dependency_dirs(repo_root, base_dir)
            for relative in support_files:
                source = _safe_relative_file(repo_root, relative)
                destination = base_dir / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)

            baseline = _run(
                argv,
                cwd=base_dir,
                timeout_seconds=timeout_seconds,
                env=_witness_env(base_dir, "base-with-head-tests"),
            )
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(base_dir)],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

    status, note = _classify_base_result(
        baseline,
        argv=argv,
        mode=mode,
    )
    return RegressionWitness(
        base_ref=base_ref,
        head_ref=head_ref,
        tests=tests,
        head=head,
        base_with_head_tests=baseline,
        status=status,
        note=note,
        mode=mode,
        support_files=support_files,
        base_sha=resolved_base_sha,
        head_sha=resolved_head_sha,
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
    payload: dict[str, Any] = {
        "schema_version": 3,
        "base_ref": witness.base_ref,
        "head_ref": witness.head_ref,
        "base_sha": witness.base_sha,
        "head_sha": witness.head_sha,
        "tests": list(witness.tests),
        "support_files": list(witness.support_files),
        "status": witness.status,
        "mode": witness.mode,
        "witnessed": witness.witnessed,
        "note": witness.note,
        "head": _command_to_dict(witness.head),
        "base_with_head_tests": _command_to_dict(witness.base_with_head_tests),
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    payload["evidence_digest_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def render_witness_markdown(witness: RegressionWitness) -> str:
    badge = {
        "witnessed": "WITNESSED",
        "not-witnessed": "NOT WITNESSED",
        "head-failing": "HEAD FAILING",
        "no-changed-tests": "NO CHANGED TESTS",
        "inconclusive": "INCONCLUSIVE",
        "suite-delta": "SUITE DELTA",
    }.get(witness.status, witness.status.upper())

    lines = [
        "# Counterproof · Regression Witness",
        "",
        f"## {badge}",
        "",
        witness.note,
        "",
        f"- Base: {witness.base_ref}",
        f"- Head: {witness.head_ref}",
        f"- Changed tests: {len(witness.tests)}",
        f"- Mode: {witness.mode}",
        f"- Test-support files overlaid: {len(witness.support_files)}",
    ]

    receipt = witness_to_dict(witness)
    lines.extend(
        [
            "",
            "### Execution receipt",
            "",
            f"- Head commit: `{witness.head_sha or witness.head_ref}`",
            f"- Base commit: `{witness.base_sha or witness.base_ref}`",
        ]
    )
    if witness.head is not None:
        lines.append(f"- Command: `{shlex.join(witness.head.argv)}`")
        lines.append(f"- HEAD exit: `{witness.head.returncode}`")
    if witness.base_with_head_tests is not None:
        lines.append(
            f"- BASE exit: `{witness.base_with_head_tests.returncode}`"
        )
    lines.append(
        f"- Evidence digest: `sha256:{receipt['evidence_digest_sha256']}`"
    )
    lines.append("- Raw stdout/stderr tails are preserved in the JSON artifact.")

    if witness.tests:
        lines.extend(["", "### Tests replayed", ""])
        lines.extend(f"- {path}" for path in witness.tests)

    extra_support = tuple(
        path for path in witness.support_files if path not in witness.tests
    )
    if extra_support:
        lines.extend(["", "### Test-support closure", ""])
        lines.extend(f"- {path}" for path in extra_support)

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
    elif witness.status == "suite-delta":
        lines.extend(
            [
                "",
                "> The full configured suite distinguishes base from head.",
                "> Because the runner did not target changed tests directly, this is not labeled a Regression Witness.",
            ]
        )
    return "\n".join(lines) + "\n"


def render_witness_review_note(
    payload: dict[str, Any],
    *,
    source_url: str | None = None,
    runner_url: str | None = None,
) -> str:
    """Render a concise reviewer-facing note from a stored witness payload."""
    status = str(payload.get("status", "unknown"))
    tests = [str(item) for item in payload.get("tests", [])]
    head = payload.get("head") or {}
    base = payload.get("base_with_head_tests") or {}
    head_sha = str(payload.get("head_sha") or payload.get("head_ref") or "unknown")
    base_sha = str(payload.get("base_sha") or payload.get("base_ref") or "unknown")
    digest = str(payload.get("evidence_digest_sha256") or "")
    argv = tuple(str(item) for item in head.get("argv", []))

    labels = {
        "witnessed": "WITNESSED",
        "suite-delta": "SUITE DELTA",
        "not-witnessed": "NOT WITNESSED",
        "head-failing": "HEAD FAILING",
        "no-changed-tests": "NO CHANGED TESTS",
        "inconclusive": "INCONCLUSIVE",
    }
    title = labels.get(status, status.upper())

    lines = [
        f"### Counterproof replay: {title}",
        "",
    ]
    if status == "witnessed":
        lines.append(
            "The same changed regression test(s) pass on the PR head and fail "
            "when replayed against the pre-change base."
        )
    else:
        note = str(payload.get("note") or "").strip()
        lines.append(note or "The replay did not produce an exact regression witness.")

    lines.extend(
        [
            "",
            f"- HEAD: `{head_sha}` — exit `{head.get('returncode')}`",
            f"- BASE: `{base_sha}` — exit `{base.get('returncode')}`",
            f"- Changed tests: {len(tests)}",
        ]
    )
    if argv:
        lines.append(f"- Command: `{shlex.join(argv)}`")
    if tests:
        lines.append("- Tests: " + ", ".join(f"`{item}`" for item in tests))
    if digest:
        lines.append(f"- Evidence digest: `sha256:{digest}`")

    links = []
    if source_url:
        links.append(f"[source PR]({source_url})")
    if runner_url:
        links.append(f"[runner]({runner_url})")
    if links:
        lines.extend(["", " · ".join(links)])

    lines.extend(
        [
            "",
            "> Scope: this proves the tested before/after regression delta. "
            "It does not independently prove every claimed root cause or production incident.",
            "",
            "Would this evidence materially help review this change? "
            "If not, what evidence is still missing?",
        ]
    )
    return "\n".join(lines) + "\n"


def write_witness_json(path: Path, witness: RegressionWitness) -> None:
    path.write_text(
        json.dumps(witness_to_dict(witness), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
