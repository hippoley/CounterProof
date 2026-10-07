from __future__ import annotations

import os
from collections.abc import Mapping
from hashlib import sha1
from pathlib import Path
from typing import Any

import yaml

from .claim_matrix import load_claim_matrix
from .effective_lifecycle import EffectiveLifecycleObservation
from .evidence_lifecycle import EvidenceLifecycle, resolve_effective_lifecycle
from .evidence_supersession import load_evidence_graph
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
        raise ValueError(
            f"{label} must stay within the Reality Contract suite directory"
        ) from exc
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


def _provenance_diff(
    expected: dict[str, Any],
    observed: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if expected.get("schema_version") != observed.get("schema_version"):
        failures.append(
            "recursive provenance schema_version "
            f"expected {expected.get('schema_version')!r}, "
            f"observed {observed.get('schema_version')!r}"
        )

    expected_contracts = expected.get("contracts")
    observed_contracts = observed.get("contracts")
    if not isinstance(expected_contracts, list) or not isinstance(
        observed_contracts, list
    ):
        return failures + ["recursive provenance contracts must be lists"]

    def by_contract(items: list[Any]) -> dict[str, dict[str, Any]]:
        indexed: dict[str, dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            contract_id = item.get("contract_id")
            if isinstance(contract_id, str):
                indexed[contract_id] = item
        return indexed

    expected_by_id = by_contract(expected_contracts)
    observed_by_id = by_contract(observed_contracts)
    for contract_id in sorted(set(expected_by_id) | set(observed_by_id)):
        expected_contract = expected_by_id.get(contract_id)
        observed_contract = observed_by_id.get(contract_id)
        if expected_contract is None:
            failures.append(
                f"recursive provenance added contract {contract_id!r}"
            )
            continue
        if observed_contract is None:
            failures.append(
                f"recursive provenance missing contract {contract_id!r}"
            )
            continue

        expected_matrix = expected_contract.get("claim_matrix")
        observed_matrix = observed_contract.get("claim_matrix")
        if not isinstance(expected_matrix, dict) or not isinstance(
            observed_matrix, dict
        ):
            failures.append(
                f"contract {contract_id!r} claim matrix provenance must be an object"
            )
        else:
            matrix_file = observed_matrix.get("file") or expected_matrix.get("file")
            for field in (
                "file",
                "git_blob_sha",
                "base_sha",
                "head_sha",
                "evidence_digest",
            ):
                if expected_matrix.get(field) != observed_matrix.get(field):
                    failures.append(
                        f"contract {contract_id!r} claim matrix {matrix_file!r} "
                        f"{field} expected {expected_matrix.get(field)!r}, "
                        f"observed {observed_matrix.get(field)!r}"
                    )

        expected_receipts = expected_contract.get("machine_receipts")
        observed_receipts = observed_contract.get("machine_receipts")
        if not isinstance(expected_receipts, list) or not isinstance(
            observed_receipts, list
        ):
            failures.append(
                f"contract {contract_id!r} machine receipt provenance must be a list"
            )
            continue

        def by_receipt(items: list[Any]) -> dict[tuple[str, str], dict[str, Any]]:
            indexed: dict[tuple[str, str], dict[str, Any]] = {}
            for item in items:
                if not isinstance(item, dict):
                    continue
                claim_id = item.get("claim_id")
                file_name = item.get("file")
                if isinstance(claim_id, str) and isinstance(file_name, str):
                    indexed[(claim_id, file_name)] = item
            return indexed

        expected_receipts_by_id = by_receipt(expected_receipts)
        observed_receipts_by_id = by_receipt(observed_receipts)
        keys = set(expected_receipts_by_id) | set(observed_receipts_by_id)
        for claim_id, file_name in sorted(keys):
            expected_receipt = expected_receipts_by_id.get((claim_id, file_name))
            observed_receipt = observed_receipts_by_id.get((claim_id, file_name))
            if expected_receipt is None:
                failures.append(
                    f"contract {contract_id!r} added machine receipt "
                    f"{file_name!r} for claim {claim_id!r}"
                )
                continue
            if observed_receipt is None:
                failures.append(
                    f"contract {contract_id!r} missing machine receipt "
                    f"{file_name!r} for claim {claim_id!r}"
                )
                continue
            for field in ("git_blob_sha", "verdict", "case"):
                if expected_receipt.get(field) != observed_receipt.get(field):
                    failures.append(
                        f"contract {contract_id!r} machine receipt {file_name!r} "
                        f"for claim {claim_id!r} {field} "
                        f"expected {expected_receipt.get(field)!r}, "
                        f"observed {observed_receipt.get(field)!r}"
                    )

    if not failures and expected != observed:
        failures.append(
            "recursive provenance manifest differs in an unrecognized field"
        )
    return failures



def _verify_observation_semantics(
    observations: list[Any],
    *,
    suite_file: Path,
    graph_file: Path | None,
) -> list[str]:
    """Re-derive lifecycle decisions from pinned inputs and recorded freshness."""
    failures: list[str] = []
    raw = yaml.safe_load(suite_file.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("contracts"), list):
        return ["invalid reality contract suite for lifecycle observation verification"]

    root = suite_file.parent.resolve()
    graph = load_evidence_graph(graph_file) if graph_file else None
    expected: dict[str, dict[str, Any]] = {}

    for contract in raw["contracts"]:
        if not isinstance(contract, dict):
            continue
        contract_id = contract.get("id")
        manifest_name = contract.get("manifest")
        if not isinstance(contract_id, str) or not contract_id:
            continue
        if not isinstance(manifest_name, str) or not manifest_name:
            continue

        manifest_path = _resolve_dependency(
            root,
            root / manifest_name,
            label=f"contract {contract_id!r} manifest",
        )
        manifest = load_claim_matrix(manifest_path)
        declared = EvidenceLifecycle(
            contract.get("lifecycle", EvidenceLifecycle.CURRENT.value)
        )
        evidence_id_raw = contract.get("evidence_id")
        evidence_id = (
            str(evidence_id_raw) if evidence_id_raw is not None else None
        )
        graph_signal: EvidenceLifecycle | None = None
        if graph is not None and evidence_id is not None:
            try:
                graph_signal = graph.lifecycle_suggestions[evidence_id]
            except KeyError as exc:
                raise ValueError(
                    f"contract {contract_id!r} evidence_id {evidence_id!r} "
                    "is missing from evidence graph"
                ) from exc

        expected[contract_id] = {
            "evidence_id": evidence_id,
            "declared": declared,
            "graph_signal": graph_signal,
            "source_pr": manifest.source_pr,
            "frozen_base_sha": contract.get("expected_base_sha") or manifest.base_sha,
            "frozen_head_sha": contract.get("expected_head_sha") or manifest.head_sha,
        }

    seen: set[str] = set()
    for item in observations:
        if not isinstance(item, dict):
            failures.append("lifecycle receipt observation must be an object")
            continue

        contract_id = item.get("contract_id")
        if not isinstance(contract_id, str) or not contract_id:
            failures.append("lifecycle receipt observation requires contract_id")
            continue
        if contract_id in seen:
            failures.append(f"duplicate lifecycle observation for contract {contract_id!r}")
            continue
        seen.add(contract_id)

        contract = expected.get(contract_id)
        if contract is None:
            failures.append(f"unexpected lifecycle observation for contract {contract_id!r}")
            continue

        if item.get("evidence_id") != contract["evidence_id"]:
            failures.append(
                f"observation {contract_id!r} evidence_id expected "
                f"{contract['evidence_id']!r}, observed {item.get('evidence_id')!r}"
            )

        declared = contract["declared"]
        if item.get("declared") != declared.value:
            failures.append(
                f"observation {contract_id!r} declared lifecycle expected "
                f"{declared.value!r}, observed {item.get('declared')!r}"
            )

        graph_signal = contract["graph_signal"]
        expected_graph_signal = graph_signal.value if graph_signal else None
        if item.get("graph_signal") != expected_graph_signal:
            failures.append(
                f"observation {contract_id!r} graph signal expected "
                f"{expected_graph_signal!r}, observed {item.get('graph_signal')!r}"
            )

        freshness = item.get("freshness")
        if not isinstance(freshness, dict):
            failures.append(
                f"observation {contract_id!r} freshness must be an object"
            )
            continue

        status = freshness.get("status")
        freshness_signal: EvidenceLifecycle | None = None

        if status is None:
            failures.append(
                f"observation {contract_id!r} requires a recorded freshness status"
            )
        elif status in {"FRESH", "DRIFTED", "UNRESOLVED"}:
            for field in ("source_pr", "frozen_base_sha", "frozen_head_sha"):
                if freshness.get(field) != contract[field]:
                    failures.append(
                        f"observation {contract_id!r} freshness {field} expected "
                        f"{contract[field]!r}, observed {freshness.get(field)!r}"
                    )

            live_base = freshness.get("live_base_sha")
            live_head = freshness.get("live_head_sha")
            frozen_base = contract["frozen_base_sha"]
            frozen_head = contract["frozen_head_sha"]

            if status in {"FRESH", "DRIFTED"}:
                if not isinstance(live_base, str) or not live_base:
                    failures.append(
                        f"observation {contract_id!r} {status} freshness requires live_base_sha"
                    )
                if not isinstance(live_head, str) or not live_head:
                    failures.append(
                        f"observation {contract_id!r} {status} freshness requires live_head_sha"
                    )

                drift: list[str] = []
                if frozen_base and live_base != frozen_base:
                    drift.append("base")
                if frozen_head and live_head != frozen_head:
                    drift.append("head")

                if status == "FRESH":
                    if drift:
                        failures.append(
                            f"observation {contract_id!r} freshness says FRESH "
                            f"but captured candidate drift is {'/'.join(drift)}"
                        )
                    if freshness.get("reason") is not None:
                        failures.append(
                            f"observation {contract_id!r} FRESH freshness must not carry a reason"
                        )
                else:
                    if not drift:
                        failures.append(
                            f"observation {contract_id!r} freshness says DRIFTED "
                            "but captured candidates match the frozen identities"
                        )
                    expected_reason = (
                        f"live PR {'/'.join(drift)} candidate drift" if drift else None
                    )
                    if freshness.get("reason") != expected_reason:
                        failures.append(
                            f"observation {contract_id!r} drift reason expected "
                            f"{expected_reason!r}, observed {freshness.get('reason')!r}"
                        )
                    promoted = resolve_effective_lifecycle(
                        declared,
                        freshness_signal=EvidenceLifecycle.STALE,
                    )
                    if promoted is not declared:
                        freshness_signal = EvidenceLifecycle.STALE
            else:
                if live_base is not None or live_head is not None:
                    failures.append(
                        f"observation {contract_id!r} UNRESOLVED freshness "
                        "must not carry live candidate identities"
                    )
                if not freshness.get("reason"):
                    failures.append(
                        f"observation {contract_id!r} UNRESOLVED freshness requires a reason"
                    )
        else:
            failures.append(
                f"observation {contract_id!r} has invalid freshness status {status!r}"
            )

        expected_freshness_signal = (
            freshness_signal.value if freshness_signal else None
        )
        if item.get("freshness_signal") != expected_freshness_signal:
            failures.append(
                f"observation {contract_id!r} freshness signal expected "
                f"{expected_freshness_signal!r}, observed {item.get('freshness_signal')!r}"
            )

        effective = resolve_effective_lifecycle(
            declared,
            freshness_signal=freshness_signal,
            graph_signal=graph_signal,
        )
        if item.get("effective") != effective.value:
            failures.append(
                f"observation {contract_id!r} effective lifecycle expected "
                f"{effective.value!r}, observed {item.get('effective')!r}"
            )

    for contract_id in sorted(set(expected) - seen):
        failures.append(f"missing lifecycle observation for contract {contract_id!r}")

    return failures


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
            failures.extend(_provenance_diff(expected_provenance, observed_provenance))

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

    try:
        failures.extend(
            _verify_observation_semantics(
                observations,
                suite_file=suite_file,
                graph_file=graph_file,
            )
        )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        failures.append(f"lifecycle observation semantics could not be rebuilt: {exc}")

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
        if freshness.get("status") not in {"FRESH", "DRIFTED", "UNRESOLVED"}:
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
