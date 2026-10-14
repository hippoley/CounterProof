#!/usr/bin/env python3
"""Cross-process fixture-only interop: producer and consumer share no Python imports."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "v0_1_vectors.json"
CONSUMER = ROOT / "consumer.py"


def main():
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        fixture = Path(tmp) / "producer-owned.json"
        output = Path(tmp) / "consumer-owned.json"
        fixture.write_text(json.dumps(payload), encoding="utf-8")
        subprocess.run([sys.executable, str(CONSUMER), str(fixture),
                        "--output", str(output)], check=True)
        result = json.loads(output.read_text(encoding="utf-8"))
        actual = {v["id"]: v["verdict"] for v in result["results"]}
        expected = {v["id"]: v["expected_verdict"] for v in payload["vectors"]}
        assert actual == expected, (actual, expected)
        assert result["trust_profile"] == "fixture_only"

        # Reject an attempt to re-label fixture evidence as real attestation.
        payload["status"] = "live_attestation"
        fixture.write_text(json.dumps(payload), encoding="utf-8")
        rejected = subprocess.run([sys.executable, str(CONSUMER), str(fixture)],
                                  capture_output=True, text=True)
        assert rejected.returncode != 0
    print(f"PASS cross-process fixture-only producer/consumer contract: {len(expected)} vectors")


if __name__ == "__main__":
    main()
