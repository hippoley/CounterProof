from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "behavior_witness"
VERIFY = EXPERIMENT / "verify.py"
REFERENCE = EXPERIMENT / "examples" / "reference-contract.json"
PASSING = EXPERIMENT / "examples" / "candidate-pass.json"
FAILING = EXPERIMENT / "examples" / "candidate-fail.json"


def run(candidate: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFY), str(REFERENCE), str(candidate)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_behavior_witness_pass_fixture() -> None:
    result = run(PASSING)
    assert result.returncode == 0
    assert result.stdout.startswith("PASS:")


def test_behavior_witness_fail_fixture() -> None:
    result = run(FAILING)
    assert result.returncode == 1
    assert result.stdout.startswith("FAIL:")


def test_behavior_witness_probe_mismatch_fails_closed(tmp_path: Path) -> None:
    candidate = json.loads(PASSING.read_text(encoding="utf-8"))
    candidate["probe_id"] = "different-probe"
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(candidate), encoding="utf-8")

    result = run(path)
    assert result.returncode == 2
    assert result.stdout.startswith("UNKNOWN:")
