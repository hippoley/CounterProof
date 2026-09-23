"""Deterministic integrity checks for the evidence machinery around agent PRs."""
from __future__ import annotations

import fnmatch
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TEST_PATTERNS = (
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

EVIDENCE_CONFIG_PATTERNS = (
    ".github/workflows/**",
    ".github/actions/**",
    "pytest.ini",
    "tox.ini",
    "noxfile.py",
    ".coveragerc",
    "coverage.ini",
    "codecov.yml",
    "codecov.yaml",
    "jest.config.*",
    "vitest.config.*",
    "playwright.config.*",
    "pyproject.toml",
    "setup.cfg",
)

ADDED_LINE_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "continue-on-error",
        re.compile(r"\bcontinue-on-error\s*:\s*true\b", re.I),
        "Workflow step was changed to continue after failure.",
    ),
    (
        "shell-ignore-failure",
        re.compile(r"\|\|\s*true\b"),
        "A shell command now converts failure into success with || true.",
    ),
    (
        "pytest-skip",
        re.compile(r"(pytest\.mark\.(?:skip|xfail)|@pytest\.mark\.(?:skip|xfail))"),
        "A pytest skip/xfail marker was added.",
    ),
    (
        "unittest-skip",
        re.compile(r"@(?:unittest\.)?skip\b"),
        "A unittest skip decorator was added.",
    ),
    (
        "js-test-skip",
        re.compile(r"\b(?:test|it|describe)\.skip\s*\("),
        "A JavaScript/TypeScript test skip was added.",
    ),
    (
        "pull-request-target",
        re.compile(r"\bpull_request_target\s*:"),
        "pull_request_target was added; review token/secrets exposure carefully.",
    ),
    (
        "write-all-permissions",
        re.compile(r"\bpermissions\s*:\s*write-all\b"),
        "Workflow permissions were widened to write-all.",
    ),
)


@dataclass(frozen=True)
class IntegrityFinding:
    code: str
    risk: str
    path: str
    evidence: str
    note: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "risk": self.risk,
            "path": self.path,
            "evidence": self.evidence,
            "note": self.note,
        }


@dataclass(frozen=True)
class ProofIntegrityReport:
    base_ref: str
    head_ref: str
    findings: tuple[IntegrityFinding, ...]

    @property
    def status(self) -> str:
        return "clean" if not self.findings else "review-required"

    @property
    def high_risk_count(self) -> int:
        return sum(item.risk == "high" for item in self.findings)


def _git(repo: Path, *args: str, allow_missing: bool = False) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        if allow_missing:
            return ""
        raise RuntimeError(
            f"git {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def _name_status(repo: Path, base_ref: str, head_ref: str) -> list[tuple[str, str]]:
    raw = _git(
        repo,
        "diff",
        "--name-status",
        f"{base_ref}...{head_ref}",
        "--",
    )
    rows: list[tuple[str, str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        rows.append((parts[0], parts[-1]))
    return rows


def _changed_added_lines(
    repo: Path,
    base_ref: str,
    head_ref: str,
) -> list[tuple[str, str]]:
    raw = _git(
        repo,
        "diff",
        "--unified=0",
        "--no-color",
        f"{base_ref}...{head_ref}",
        "--",
    )
    path = ""
    added: list[tuple[str, str]] = []
    for line in raw.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added.append((path, line[1:].strip()))
    return added


def _file_at_ref(repo: Path, ref: str, path: str) -> str:
    return _git(repo, "show", f"{ref}:{path}", allow_missing=True)


def inspect_proof_integrity(
    repo_root: Path,
    *,
    base_ref: str,
    head_ref: str = "HEAD",
) -> ProofIntegrityReport:
    """Inspect deterministic signs that the PR changed its own evidence machinery."""
    repo_root = repo_root.resolve()
    findings: list[IntegrityFinding] = []
    changed = _name_status(repo_root, base_ref, head_ref)

    for status, path in changed:
        if status.startswith("D") and _matches(path, TEST_PATTERNS):
            findings.append(
                IntegrityFinding(
                    code="test-deleted",
                    risk="high",
                    path=path,
                    evidence=f"{status} {path}",
                    note="A test file was deleted in the same change being evaluated.",
                )
            )

        if _matches(path, EVIDENCE_CONFIG_PATTERNS):
            findings.append(
                IntegrityFinding(
                    code="evidence-config-changed",
                    risk="medium",
                    path=path,
                    evidence=f"{status} {path}",
                    note=(
                        "A CI/test/coverage configuration surface changed. "
                        "This may be legitimate, but the proof machinery is no longer held fixed."
                    ),
                )
            )

        if path.startswith(".github/workflows/") and not status.startswith("D"):
            before = _file_at_ref(repo_root, base_ref, path)
            after = _file_at_ref(repo_root, head_ref, path)
            if "pull_request:" in before and "pull_request:" not in after:
                findings.append(
                    IntegrityFinding(
                        code="pull-request-trigger-removed",
                        risk="high",
                        path=path,
                        evidence="pull_request trigger present on base, absent on head",
                        note="The workflow no longer runs on pull requests.",
                    )
                )

    for path, line in _changed_added_lines(repo_root, base_ref, head_ref):
        for code, pattern, note in ADDED_LINE_RULES:
            if pattern.search(line):
                findings.append(
                    IntegrityFinding(
                        code=code,
                        risk="high",
                        path=path,
                        evidence=line[:300],
                        note=note,
                    )
                )

    unique: dict[tuple[str, str, str], IntegrityFinding] = {}
    for finding in findings:
        unique[(finding.code, finding.path, finding.evidence)] = finding

    ordered = tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                0 if item.risk == "high" else 1,
                item.path,
                item.code,
            ),
        )
    )
    return ProofIntegrityReport(
        base_ref=base_ref,
        head_ref=head_ref,
        findings=ordered,
    )


def integrity_to_dict(report: ProofIntegrityReport) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "base_ref": report.base_ref,
        "head_ref": report.head_ref,
        "status": report.status,
        "high_risk_count": report.high_risk_count,
        "findings": [item.to_dict() for item in report.findings],
    }


def render_integrity_markdown(report: ProofIntegrityReport) -> str:
    lines = [
        "# Counterproof · Proof Integrity",
        "",
        f"## {report.status.upper()}",
        "",
    ]

    if not report.findings:
        lines.extend(
            [
                "No deterministic evidence-integrity risks were detected in the diff.",
                "",
                "> This is a narrow guard, not a complete security or code-quality review.",
            ]
        )
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            (
                "The PR changed one or more surfaces that can affect how its own "
                "evidence is produced or interpreted."
            ),
            "",
            "| Risk | Finding | Path | Evidence |",
            "|---|---|---|---|",
        ]
    )
    for item in report.findings:
        evidence = item.evidence.replace("|", "\\|")
        lines.append(
            f"| {item.risk.upper()} | {item.code} | {item.path} | {evidence} |"
        )

    lines.extend(
        [
            "",
            "### What this means",
            "",
            (
                "A finding is not proof of malicious behavior. It means the test/CI "
                "judge changed in the same PR, so reviewers should not treat green "
                "evidence as independent without checking the change."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_integrity_json(path: Path, report: ProofIntegrityReport) -> None:
    path.write_text(
        json.dumps(integrity_to_dict(report), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
