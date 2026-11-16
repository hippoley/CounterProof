"""Run the independent third-party parity consumer in the repository CI suite."""

import subprocess
import sys
from pathlib import Path


def test_probityai_criterion_parity_replays_all_14_cases():
    fixture_dir = (
        Path(__file__).resolve().parents[2]
        / "examples"
        / "interop"
        / "probityai-criterion-parity"
    )
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_replay"],
        cwd=fixture_dir,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Ran 4 tests" in result.stderr
