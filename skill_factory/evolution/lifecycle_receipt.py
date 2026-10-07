from __future__ import annotations

import os
from collections.abc import Mapping
from hashlib import sha1
from pathlib import Path
from typing import Any

import yaml

from .claim_matrix import load_claim_matrix
from .effective_lifecycle import EffectiveLifecycleObservation
from .reality_contracts import validate_reality_contracts


def git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return sha1(header + content, usedforsecurity=False).hexdigest()


def _resolve_dependency(root: Path, candidate: Path, *, label: str) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay within the Reality Contract suite directory") from exc
    return resolved


def build_recursive_provenance_manifest(suite_file: Path) -> dict[str, Any]:
    """Freeze every local file transitively consumed by Reality Contract validation.

    The suite is already pinned separately by the lifecycle receipt. This closure
    makes its indirect claim-matrix and machine-receipt dependencies explicit so
    reviewers do not have to follow YAML references by hand.
    """
    raw = yaml.safe_load(suite_file.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError("invalid reality contract suite")
    contracts = raw.get("contracts")
    if not isinstance(contracts, list):
        raise TypeError("reality contract suite requires contracts")

    root = suite_file.parent.resolve()
    entries: list[dict[str, Any]] = []
    for contract in contracts:
        if not isinstance(contract, dict):
            raise TypeError("reality contract must be an object")
        contract_id = contract.get("id")
        manifest_name = contract.get("manifest")
        if not isinstance(contract_id, str) or not contract_id:
            raise ValueError("reality contract requires a non-empty id")
        if not isinstance(manifest_name, str) or not manifest_name:
            raise ValueError(f"reality contract {contract_id!r} requires manifest")

        manifest_path = _resolve_dependency(
            root,
            root / manifest_name,
            label=f"contract {contract_id!r} manifest",
        )
        manifest = load_claim_matrix(manifest_path)

        machine_receipts: list[dict[str, Any]] = []
        for claim in manifest.claims:
            if not claim.receipt_file:
                continue
            receipt_path = _resolve_dependency(
                root,
                manifest_path.parent / claim.receipt_file,
                label=f"claim {claim.id!r} receipt",
            )
            machine_receipts.append(
                {
                    "claim_id": claim.id,
                    "file": receipt_path.relative_to(root).as_posix(),
                    "git_blob_sha": git_blob_sha(receipt_path),
                    "verdict": claim.receipt_observed_verdict,
                    "case": claim.receipt_case,
                }
            )

        machine_receipts.sort(key=lambda item: (item["claim_id"], item["file"]))
        entries.append(
            {
                "contract_id": contract_id,
                "claim_matrix": {
                    "file": manifest_path.relative_to(root).as_posix(),
                    "git_blob_sha": git_blob_sha(manifest_path),
                    "base_sha": manifest.base_sha,
                    "head_sha": manifest.head_sha,
                    "evidence_digest": manifest.evidence_digest,
                },
                "machine_receipts": machine_receipts,
            }
        )

    entries.sort(key=lambda item: item["contract_id"])
    return {
        "schema_version": 1,
        "contracts": entries,
    }


def build_lifecycle_receipt(
    observations: list[EffectiveLifecycleObservation],
    *,
    suite_file: Path,
    graph_file: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    env = environment if environment is not None else os.environ
    items: list[dict[str, Any]] = []
    mismatches = 0

    for observation in observations:
        if observation.declared is not observation.effective:
            mismatches += 1
        items.append(
            {
                "contract_id": observation.contract_id,
                "evidence_id": observation.evidence_id,
                "declared": observation.declared.value,
                "freshness_signal": (
                    observation.freshness_signal.value
                    if observation.freshness_signal
                    else None
                ),
                "graph_signal": (
                    observation.graph_signal.value
                    if observation.graph_signal
                    else None
                ),
                "effective": observation.effective.value,
                "freshness": {
                    "status": observation.freshness_status,
                    "source_pr": observation.source_pr,
                    "frozen_base_sha": observation.frozen_base_sha,
                    "frozen_head_sha": observation.frozen_head_sha,
                    "live_base_sha": observation.live_base_sha,
                    "live_head_sha": observation.live_head_sha,
                    "reason": observation.freshness_reason,
                },
            }
        )

    execution = {
        "repository": env.get("GITHUB_REPOSITORY"),
        "workflow": env.get("GITHUB_WORKFLOW"),
        "run_id": env.get("GITHUB_RUN_ID"),
        "run_attempt": env.get("GITHUB_RUN_ATTEMPT"),
        "git_sha": env.get("GITHUB_SHA"),
        "ref": env.get("GITHUB_REF"),
    }

    return {
        "schema_version": 2,
        "status": "PASS" if mismatches == 0 else "UPDATE_REQUIRED",
        "mismatch_count": mismatches,
        "inputs": {
            "suite_file": str(suite_file),
            "suite_git_blob_sha": git_blob_sha(suite_file),
            "graph_file": str(graph_file) if graph_file else None,
            "graph_git_blob_sha": git_blob_sha(graph_file) if graph_file else None,
        },
        "provenance": build_recursive_provenance_manifest(suite_file),
        "execution": execution,
        "observations": items,
    }


def verify_lifecycle_receipt(
    receipt: dict[str, Any],
    *,
    suite_file: Path,
    graph_file: Path | None = None,
) -> list[str]:
    failures: list[str] = []
    if receipt.get("schema_version") != 2:
        failures.append("unsupported lifecycle receipt schema_version")

    inputs = receipt.get("inputs")
    if not isinstance(inputs, dict):
        return failures + ["lifecycle receipt inputs must be an object"]

    suite_sha = inputs.get("suite_git_blob_sha")
    observed_suite_sha = git_blob_sha(suite_file)
    if suite_sha != observed_suite_sha:
        failures.append(
            f"suite git blob sha expected {suite_sha!r}, observed {observed_suite_sha!r}"
        )

    try:
        contract_failures = validate_reality_contracts(suite_file)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        failures.append(f"Reality Contract validation could not run: {exc}")
    else:
        for failure in contract_failures:
            failures.append(
                f"Reality Contract invalid: {failure.contract_id}: {failure.message}"
            )

    expected_provenance = receipt.get("provenance")
    if not isinstance(expected_provenance, dict):
        failures.append("lifecycle receipt provenance manifest must be an object")
    else:
        try:
            observed_provenance = build_recursive_provenance_manifest(suite_file)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            failures.append(f"recursive provenance closure could not be rebuilt: {exc}")
        else:
            if expected_provenance != observed_provenance:
                failures.append(
                    "recursive provenance manifest does not match current "
                    "claim-matrix / machine-receipt closure"
                )

    expected_graph = inputs.get("graph_git_blob_sha")
    if graph_file is None:
        if expected_graph is not None:
            failures.append("receipt expects an evidence graph but none was supplied")
    else:
        observed_graph_sha = git_blob_sha(graph_file)
        if expected_graph != observed_graph_sha:
            failures.append(
                f"graph git blob sha expected {expected_graph!r}, "
                f"observed {observed_graph_sha!r}"
            )

    observations = receipt.get("observations")
    if not isinstance(observations, list):
        failures.append("lifecycle receipt observations must be a list")
        return failures

    mismatches = 0
    for item in observations:
        if not isinstance(item, dict):
            failures.append("lifecycle receipt observation must be an object")
            continue
        declared = item.get("declared")
        effective = item.get("effective")
        if declared != effective:
            mismatches += 1
        freshness = item.get("freshness")
        if not isinstance(freshness, dict):
            failures.append(
                f"observation {item.get('contract_id')!r} freshness must be an object"
            )
            continue
        if freshness.get("status") not in {"FRESH", "DRIFTED", "UNRESOLVED", None}:
            failures.append(
                f"observation {item.get('contract_id')!r} has invalid freshness status"
            )

    if receipt.get("mismatch_count") != mismatches:
        failures.append(
            f"mismatch_count expected {receipt.get('mismatch_count')!r}, "
            f"observed {mismatches!r}"
        )
    expected_status = "PASS" if mismatches == 0 else "UPDATE_REQUIRED"
    if receipt.get("status") != expected_status:
        failures.append(
            f"status expected {expected_status!r}, observed {receipt.get('status')!r}"
        )

    return failures
