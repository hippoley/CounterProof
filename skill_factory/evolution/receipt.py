"""Reproducibility receipts for EvoPR behavior proofs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .discriminate import DiscriminationRun
from .models import EvolutionPacket
from .replay import structured_probe_result_to_dict


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.resolve().read_bytes()).hexdigest()


def build_proof_receipt(
    *,
    trace_path: Path,
    experiment_path: Path,
    packet: EvolutionPacket,
    run: DiscriminationRun,
) -> dict[str, Any]:
    """Build a deterministic receipt tying a proof to its exact source inputs."""
    return {
        "schema_version": 2,
        "packet_id": packet.packet_id,
        "source_trace_id": packet.metadata.get("source_trace_id", ""),
        "trace": {
            "path": str(trace_path),
            "sha256": file_sha256(trace_path),
        },
        "experiment": {
            "path": str(experiment_path),
            "sha256": file_sha256(experiment_path),
        },
        "tested_surfaces": [item.surface for item in run.variants],
        "runtime_signatures": {
            item.surface: list(item.signature) for item in run.variants
        },
        "expected_signatures": {
            item.surface: list(item.expected_signature) for item in run.variants
        },
        "prediction_status": {
            item.surface: item.prediction_status for item in run.variants
        },
        "runtime_status": {
            item.surface: item.status for item in run.variants
        },
        "behavior_scores": {
            item.surface: [replay.candidate_score for replay in item.replays]
            for item in run.variants
        },
        "case_roles": {
            item.surface: list(item.normalized_roles) for item in run.variants
        },
        "structured_probe_results": {
            item.surface: [
                (
                    structured_probe_result_to_dict(outcome.probe_result)
                    if outcome is not None
                    else None
                )
                for outcome in item.outcomes
            ]
            for item in run.variants
        },
        "eligible_survivors": [
            item.surface for item in run.eligible_survivors
        ],
        "discriminated_surface": run.discriminated_surface,
        "selected_candidate_id": packet.selected_candidate_id,
        "discrimination_result": packet.metadata.get(
            "discrimination_result",
            "",
        ),
        "diagnostic_cases": list(run.diagnostic_cases),
        "preregistered_diagnostic_cases": list(
            run.preregistered_diagnostic_cases
        ),
    }


def verify_proof_receipt(
    receipt: dict[str, Any],
    *,
    trace_path: Path | None = None,
    experiment_path: Path | None = None,
) -> tuple[str, ...]:
    """Return verification errors for current files against a stored proof receipt."""
    errors: list[str] = []

    trace = receipt.get("trace", {})
    experiment = receipt.get("experiment", {})
    resolved_trace = trace_path or Path(str(trace.get("path", "")))
    resolved_experiment = experiment_path or Path(str(experiment.get("path", "")))

    for label, path, expected in (
        ("trace", resolved_trace, trace.get("sha256")),
        ("experiment", resolved_experiment, experiment.get("sha256")),
    ):
        if not expected:
            errors.append(f"{label} hash missing from receipt")
            continue
        if not path.exists():
            errors.append(f"{label} file not found: {path}")
            continue
        actual = file_sha256(path)
        if actual != expected:
            errors.append(
                f"{label} hash mismatch: expected {expected}, got {actual}"
            )

    return tuple(errors)


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
