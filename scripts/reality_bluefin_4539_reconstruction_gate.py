#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED = {
    "silverblue-main": "sha256:2ade0f897499dd488a4f59c4bbe50002228e3b683938333ce119be4e748fe1f5",
    "common": "sha256:1e7f8c88b8efb67b3fc42ef29bf0d927e9b8366c26dcf71893169979b29a4418",
    "brew": "sha256:2369e2dc70dd8b12828604d22721d1812cd87611661d789e1a0ee2cb123cbe7e",
}

DROPIN = Path(
    "system_files/shared/usr/lib/systemd/user/"
    "xdg-desktop-portal.service.d/30-after-keyring.conf"
)


def parse_image_versions(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    current: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("- name:"):
            current = line.split(":", 1)[1].strip()
        elif line.startswith("digest:") and current:
            result[current] = line.split(":", 1)[1].strip()
    return result


def build_receipt(
    source_dir: Path,
    *,
    candidate: str,
    source_commit: str,
    availability: dict[str, str],
) -> dict:
    versions = parse_image_versions(source_dir / "image-versions.yml")
    source_match = all(versions.get(k) == v for k, v in EXPECTED.items())

    dropin_exists = (source_dir / DROPIN).exists()
    expected_dropin = candidate == "BAD"
    intervention_match = dropin_exists == expected_dropin

    missing = sorted(k for k, status in availability.items() if status != "AVAILABLE")

    if not source_match or not intervention_match:
        verdict = "INVALID_RECONSTRUCTION_SOURCE_CONTRACT"
    elif not missing:
        verdict = "READY_FOR_SOURCE_PINNED_REBUILD"
    elif missing == ["silverblue-main"]:
        verdict = "BLOCKED_MISSING_HISTORICAL_BASE"
    else:
        verdict = "BLOCKED_MISSING_HISTORICAL_DEPENDENCIES"

    return {
        "schema_version": 1,
        "case": "ublue-os/bluefin#4539",
        "candidate": candidate,
        "source_commit": source_commit,
        "source_contract": {
            "expected_dependencies": EXPECTED,
            "observed_dependencies": versions,
            "dependencies_match": source_match,
            "dropin_exists": dropin_exists,
            "expected_dropin_exists": expected_dropin,
            "intervention_match": intervention_match,
        },
        "dependency_availability": availability,
        "missing_dependencies": missing,
        "verdict": verdict,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("--candidate", choices=["BAD", "REVERT"], required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--silverblue-status", required=True)
    parser.add_argument("--common-status", required=True)
    parser.add_argument("--brew-status", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    receipt = build_receipt(
        args.source_dir,
        candidate=args.candidate,
        source_commit=args.source_commit,
        availability={
            "silverblue-main": args.silverblue_status,
            "common": args.common_status,
            "brew": args.brew_status,
        },
    )
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))

    return 1 if receipt["verdict"] == "INVALID_RECONSTRUCTION_SOURCE_CONTRACT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
