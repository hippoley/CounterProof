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

EXPECTED_SOURCE_COMMITS = {
    "BAD": "60e72be24878ce01b4849cfb4b8efc18932a133e",
    "REVERT": "bd12c2e29f6ecb2cabd5bfb53bc00281a7d9118f",
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
    base_rebuild_inputs: dict[str, str] | None = None,
) -> dict:
    versions = parse_image_versions(source_dir / "image-versions.yml")
    source_match = all(versions.get(k) == v for k, v in EXPECTED.items())
    expected_source_commit = EXPECTED_SOURCE_COMMITS[candidate]
    source_commit_match = source_commit == expected_source_commit

    dropin_exists = (source_dir / DROPIN).exists()
    expected_dropin = candidate == "BAD"
    intervention_match = dropin_exists == expected_dropin

    missing = sorted(k for k, status in availability.items() if status != "AVAILABLE")
    base_rebuild_inputs = base_rebuild_inputs or {}
    base_rebuild_missing = sorted(
        k for k, status in base_rebuild_inputs.items() if status != "AVAILABLE"
    )
    source_equivalent_base_ready = bool(base_rebuild_inputs) and not base_rebuild_missing

    if not source_commit_match:
        verdict = "INVALID_RECONSTRUCTION_SOURCE_IDENTITY"
    elif not source_match or not intervention_match:
        verdict = "INVALID_RECONSTRUCTION_SOURCE_CONTRACT"
    elif not missing:
        verdict = "READY_FOR_SOURCE_PINNED_REBUILD"
    elif missing == ["silverblue-main"] and source_equivalent_base_ready:
        verdict = "READY_FOR_SOURCE_EQUIVALENT_BASE_REBUILD"
    elif missing == ["silverblue-main"]:
        verdict = "BLOCKED_MISSING_HISTORICAL_BASE"
    else:
        verdict = "BLOCKED_MISSING_HISTORICAL_DEPENDENCIES"

    return {
        "schema_version": 1,
        "case": "ublue-os/bluefin#4539",
        "candidate": candidate,
        "source_commit": source_commit,
        "source_identity": {
            "expected_source_commit": expected_source_commit,
            "source_commit_match": source_commit_match,
        },
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
        "reconstruction_level": (
            "SOURCE_EQUIVALENT_BASE_READY"
            if source_equivalent_base_ready
            else "SOURCE_CONTRACT_ONLY"
        ),
        "base_rebuild": {
            "source_repository": "ublue-os/main",
            "source_commit": "0273c246618919cf48a3c71a67d1c68aed209b24",
            "historical_output_digest": "sha256:2ade0f897499dd488a4f59c4bbe50002228e3b683938333ce119be4e748fe1f5",
            "inputs": base_rebuild_inputs,
            "missing_inputs": base_rebuild_missing,
            "ready": source_equivalent_base_ready,
            "claim_boundary": (
                "source-equivalent rebuild only; not bit-for-bit original OCI"
            ),
            "remaining_unfrozen_inputs": [
                "Bluefin stable build historically resolved "
                "ghcr.io/ublue-os/akmods:coreos-stable-44 by mutable tag "
                "to derive KERNEL; its historical digest is not yet bound."
            ],
        },
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
    parser.add_argument("--upstream-silverblue-status")
    parser.add_argument("--akmods-status")
    parser.add_argument("--akmods-nvidia-status")
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
        base_rebuild_inputs={
            "fedora-silverblue-44": args.upstream_silverblue_status,
            "akmods-44": args.akmods_status,
            "akmods-nvidia-open-44": args.akmods_nvidia_status,
        }
        if all(
            value is not None
            for value in (
                args.upstream_silverblue_status,
                args.akmods_status,
                args.akmods_nvidia_status,
            )
        )
        else None,
    )
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))

    return (
        1
        if receipt["verdict"]
        in {
            "INVALID_RECONSTRUCTION_SOURCE_IDENTITY",
            "INVALID_RECONSTRUCTION_SOURCE_CONTRACT",
        }
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
