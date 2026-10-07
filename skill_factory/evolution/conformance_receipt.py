"""Consumer-side receipts for external conformance campaigns."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .receipt import file_sha256


def _load_object(path: Path, label: str) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"{label} must be a JSON object")
    return raw


def build_conformance_receipt(
    manifest_path: Path,
    observations_path: Path,
) -> dict[str, Any]:
    """Freeze an external verifier campaign against one exact conformance manifest."""
    manifest = _load_object(manifest_path, "conformance manifest")
    observations = _load_object(observations_path, "conformance observations")

    vectors = manifest.get("vectors")
    comparison = manifest.get("comparisonSurface")
    verifier = observations.get("verifier")
    results = observations.get("results")
    if not isinstance(vectors, list):
        raise TypeError("conformance manifest vectors must be a list")
    if not vectors:
        raise ValueError("conformance manifest must declare non-empty vectors")
    if not isinstance(comparison, dict):
        raise TypeError("conformance manifest comparisonSurface must be an object")
    if not isinstance(verifier, dict):
        raise TypeError("observations verifier must be an object")
    if not verifier.get("name"):
        raise ValueError("observations must declare verifier identity")
    if not isinstance(results, list):
        raise TypeError("observations results must be a list")

    observed_by_id: dict[str, dict[str, Any]] = {}
    for result in results:
        if not isinstance(result, dict):
            raise TypeError("every observed result must be an object")
        if not isinstance(result.get("id"), str):
            raise TypeError("every observed result id must be a string")
        vector_id = result["id"]
        if vector_id in observed_by_id:
            raise ValueError(f"duplicate observed vector id: {vector_id}")
        observed_by_id[vector_id] = result

    normative = comparison.get("normative", [])
    measured = comparison.get("measured", [])
    if not isinstance(normative, list) or not all(isinstance(x, str) for x in normative):
        raise ValueError("comparisonSurface.normative must be a string list")
    if not isinstance(measured, list) or not all(isinstance(x, str) for x in measured):
        raise ValueError("comparisonSurface.measured must be a string list")

    vector_receipts: list[dict[str, Any]] = []
    divergences = 0
    manifest_ids: set[str] = set()

    for vector in vectors:
        if not isinstance(vector, dict):
            raise TypeError("every conformance vector must be an object")
        if not isinstance(vector.get("id"), str):
            raise TypeError("every conformance vector id must be a string")
        vector_id = vector["id"]
        if vector_id in manifest_ids:
            raise ValueError(f"duplicate manifest vector id: {vector_id}")
        manifest_ids.add(vector_id)

        observed = observed_by_id.get(vector_id)
        if observed is None:
            raise ValueError(f"missing observed result for vector {vector_id}")

        expected = vector.get("expected", {})
        mismatches: list[str] = []
        for field in normative:
            expected_value = expected.get(field)
            observed_value = observed.get(field)
            if expected_value is not None and observed_value != expected_value:
                mismatches.append(field)

        if mismatches:
            divergences += 1

        measured_observed = {
            field: observed.get(field)
            for field in measured
            if field in observed
        }
        measured_expected = {
            field: expected.get(field)
            for field in measured
            if field in expected
        }
        vector_receipts.append(
            {
                "id": vector_id,
                "kind": vector.get("kind"),
                "conditions": vector.get("conditions", []),
                "expected_normative": {
                    field: expected.get(field)
                    for field in normative
                    if field in expected
                },
                "observed_normative": {
                    field: observed.get(field)
                    for field in normative
                    if field in observed
                },
                "measured_expected": measured_expected,
                "measured_observed": measured_observed,
                "normative_mismatches": mismatches,
            }
        )

    extra = sorted(set(observed_by_id) - manifest_ids)
    if extra:
        raise ValueError(
            "observations contain vector ids outside the manifest: " + ", ".join(extra)
        )

    return {
        "schema_version": 1,
        "receipt_type": "EXTERNAL_CONFORMANCE_CAMPAIGN",
        "predicate_type": manifest.get("predicateType"),
        "spec_path": manifest.get("specPath"),
        "manifest": {
            "path": str(manifest_path),
            "sha256": file_sha256(manifest_path),
        },
        "observations": {
            "path": str(observations_path),
            "sha256": file_sha256(observations_path),
        },
        "comparison_surface": {
            "normative": normative,
            "measured": measured,
        },
        "verifier": verifier,
        "vector_count": len(vector_receipts),
        "vectors": vector_receipts,
        "divergence_count": divergences,
        "verdict": "CONFORMING" if divergences == 0 else "DIVERGED",
    }


def verify_conformance_receipt(
    receipt: dict[str, Any],
    *,
    manifest_path: Path,
    observations_path: Path | None = None,
) -> tuple[str, ...]:
    """Verify identity and applicability of a stored conformance receipt."""
    failures: list[str] = []

    if receipt.get("receipt_type") != "EXTERNAL_CONFORMANCE_CAMPAIGN":
        failures.append("unexpected receipt_type")

    expected_manifest = receipt.get("manifest", {}).get("sha256")
    if not expected_manifest:
        failures.append("manifest hash missing from receipt")
    elif not manifest_path.exists():
        failures.append(f"manifest file not found: {manifest_path}")
    else:
        actual_manifest = file_sha256(manifest_path)
        if actual_manifest != expected_manifest:
            failures.append(
                "manifest lifecycle STALE: "
                f"expected {expected_manifest}, got {actual_manifest}"
            )

    if observations_path is not None:
        expected_observations = receipt.get("observations", {}).get("sha256")
        if not expected_observations:
            failures.append("observations hash missing from receipt")
        elif not observations_path.exists():
            failures.append(f"observations file not found: {observations_path}")
        else:
            actual_observations = file_sha256(observations_path)
            if actual_observations != expected_observations:
                failures.append(
                    "observations identity mismatch: "
                    f"expected {expected_observations}, got {actual_observations}"
                )

    return tuple(failures)

def validate_external_harness_report(report: dict[str, Any]) -> tuple[str, ...]:
    """Validate that a harness report proves the named external verifier actually ran.

    This validates execution identity/completeness only. A fully executed verifier may
    still disagree with the corpus; those conformance failures remain valid evidence.
    """
    failures: list[str] = []

    if report.get("rail") != "external":
        failures.append(
            f"report rail is {report.get('rail')!r}; external verifier execution not proven"
        )

    totals = report.get("totals")
    if not isinstance(totals, dict):
        return tuple(failures + ["report totals must be an object"])

    total_vectors = totals.get("vectors")
    if not isinstance(total_vectors, int) or total_vectors <= 0:
        failures.append("totals.vectors must be a positive integer")

    verifier = report.get("verifier")
    if not isinstance(verifier, dict):
        failures.append("report verifier identity is missing")
        return tuple(failures)

    command = verifier.get("command")
    if not isinstance(command, str) or not command.strip():
        failures.append("verifier.command is missing")

    executed = verifier.get("vectorsExecuted")
    if not isinstance(executed, int):
        failures.append("verifier.vectorsExecuted must be an integer")
    elif isinstance(total_vectors, int) and executed != total_vectors:
        failures.append(
            f"external verifier ran on {executed} of {total_vectors} vectors"
        )

    suite_refusals = totals.get("suiteRefusals")
    if not isinstance(suite_refusals, int):
        failures.append("totals.suiteRefusals must be an integer")
    elif suite_refusals != 0:
        failures.append(
            f"corpus harness reported {suite_refusals} suite refusal(s)"
        )

    rows = report.get("vectors")
    if isinstance(rows, list):
        not_run = [
            row.get("id", "<unknown>")
            for row in rows
            if isinstance(row, dict) and row.get("verifierRan") is False
        ]
        if not_run:
            preview = ", ".join(str(item) for item in not_run[:5])
            suffix = "" if len(not_run) <= 5 else f" (+{len(not_run) - 5} more)"
            failures.append(
                f"per-vector report says verifier did not run: {preview}{suffix}"
            )

    return tuple(failures)

