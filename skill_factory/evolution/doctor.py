"""Install-level self test for Counterproof."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .integrity import inspect_proof_integrity
from .replay import parse_structured_probe_result
from .witness import run_regression_witness


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    note: str

    @property
    def ok(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "status": self.status,
            "note": self.note,
        }


@dataclass(frozen=True)
class DoctorReport:
    checks: tuple[DoctorCheck, ...]

    @property
    def ok(self) -> bool:
        return all(item.ok for item in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [item.to_dict() for item in self.checks],
        }


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def run_doctor() -> DoctorReport:
    checks: list[DoctorCheck] = []

    try:
        version = subprocess.run(
            ["git", "--version"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        checks.append(DoctorCheck("git", "pass", version))
    except (OSError, subprocess.CalledProcessError) as exc:
        checks.append(DoctorCheck("git", "fail", str(exc)))
        return DoctorReport(tuple(checks))

    try:
        structured = parse_structured_probe_result(
            'COUNTERPROOF_RESULT={"verdict":"pass","score":0.82,'
            '"metrics":{"doctor":1},"observations":["ok"],"artifacts":[]}'
        )
        if structured is None or structured.verdict != "pass":
            raise RuntimeError("structured result parser returned no PASS result")
        checks.append(
            DoctorCheck(
                "structured-result",
                "pass",
                f"parsed verdict={structured.verdict} score={structured.score:.2f}",
            )
        )
    except Exception as exc:
        checks.append(DoctorCheck("structured-result", "fail", str(exc)))

    try:
        with tempfile.TemporaryDirectory(prefix="counterproof-doctor-") as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _git(repo, "init")
            _git(repo, "config", "user.email", "doctor@counterproof.local")
            _git(repo, "config", "user.name", "Counterproof Doctor")

            (repo / "value.txt").write_text("1\n", encoding="utf-8")
            base = _commit(repo, "base")

            tests = repo / "tests"
            tests.mkdir()
            (tests / "test_regression.py").write_text(
                "from pathlib import Path\n"
                "assert Path('value.txt').read_text(encoding='utf-8').strip() == '2'\n",
                encoding="utf-8",
            )
            (repo / "value.txt").write_text("2\n", encoding="utf-8")
            _commit(repo, "fix with regression test")

            witness = run_regression_witness(
                repo,
                base_ref=base,
                test_command=f"{sys.executable} {{tests}}",
                timeout_seconds=30,
            )
            if not witness.witnessed:
                raise RuntimeError(f"expected witnessed, got {witness.status}")
            checks.append(
                DoctorCheck(
                    "regression-witness",
                    "pass",
                    "changed test passes on head and fails on base",
                )
            )

            integrity_base = _git(repo, "rev-parse", "HEAD")
            workflow = repo / ".github" / "workflows"
            workflow.mkdir(parents=True)
            (workflow / "ci.yml").write_text(
                "name: CI\n"
                "on:\n"
                "  pull_request:\n"
                "jobs:\n"
                "  test:\n"
                "    runs-on: ubuntu-latest\n"
                "    continue-on-error: true\n",
                encoding="utf-8",
            )
            _commit(repo, "weaken proof machinery")

            integrity = inspect_proof_integrity(
                repo,
                base_ref=integrity_base,
            )
            if integrity.high_risk_count < 1:
                raise RuntimeError("expected high-risk integrity finding")
            checks.append(
                DoctorCheck(
                    "proof-integrity",
                    "pass",
                    f"detected {integrity.high_risk_count} high-risk finding(s)",
                )
            )
    except Exception as exc:
        if not any(item.name == "regression-witness" for item in checks):
            checks.append(DoctorCheck("regression-witness", "fail", str(exc)))
        if not any(item.name == "proof-integrity" for item in checks):
            checks.append(DoctorCheck("proof-integrity", "fail", str(exc)))

    return DoctorReport(tuple(checks))


def render_doctor(report: DoctorReport) -> str:
    lines = ["Counterproof doctor", ""]
    for item in report.checks:
        mark = "PASS" if item.ok else "FAIL"
        lines.append(f"[{mark}] {item.name}: {item.note}")
    lines.append("")
    lines.append("Counterproof is ready." if report.ok else "Counterproof self-test failed.")
    return "\n".join(lines)


def doctor_json(report: DoctorReport) -> str:
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
