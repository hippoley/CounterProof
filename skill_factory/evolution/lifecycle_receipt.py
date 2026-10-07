from __future__ import annotations

import os
from collections.abc import Mapping
from hashlib import sha1
from pathlib import Path
from typing import Any

from .effective_lifecycle import EffectiveLifecycleObservation
from .reality_contracts import validate_reality_contracts


def git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return sha1(header + content, usedforsecurity=False).hexdigest()


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
