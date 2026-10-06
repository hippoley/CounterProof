from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any

import yaml

from skill_factory.evolution.claim_matrix import (
    claim_matrix_to_dict,
    load_claim_matrix,
)


@dataclass(frozen=True)
class ContractFailure:
    contract_id: str
    message: str


def _claims_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {claim["id"]: claim for claim in payload["claims"]}


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return sha1(header + content, usedforsecurity=False).hexdigest()


def _get_path(payload: Any, path: str) -> Any:
    current = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def validate_reality_contracts(path: Path) -> list[ContractFailure]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError("invalid reality contract suite")
    contracts = raw.get("contracts")
    if not isinstance(contracts, list):
        raise TypeError("reality contract suite requires contracts")

    failures: list[ContractFailure] = []
    for contract in contracts:
        contract_id = contract["id"]
        manifest_path = (path.parent / contract["manifest"]).resolve()
        manifest = load_claim_matrix(manifest_path)
        payload = claim_matrix_to_dict(manifest)

        expected_base = contract.get("expected_base_sha")
        if expected_base is not None and manifest.base_sha != expected_base:
            failures.append(
                ContractFailure(
                    contract_id,
                    f"base_sha expected {expected_base!r}, observed {manifest.base_sha!r}",
                )
            )

        expected_head = contract.get("expected_head_sha")
        if expected_head is not None and manifest.head_sha != expected_head:
            failures.append(
                ContractFailure(
                    contract_id,
                    f"head_sha expected {expected_head!r}, observed {manifest.head_sha!r}",
                )
            )

        claims = _claims_by_id(payload)
        for expected in contract.get("expectations", []):
            claim_id = expected["claim_id"]
            claim = claims.get(claim_id)
            if claim is None:
                failures.append(
                    ContractFailure(contract_id, f"missing claim {claim_id!r}")
                )
                continue

            field_map = {
                "overall_claim": "overall_claim",
                "evidence_scope": "evidence_scope",
                "oracle_applicability": "oracle_applicability",
                "oracle_alignment": "oracle_alignment",
                "receipt_verdict": "receipt_observed_verdict",
                "receipt_case": "receipt_case",
            }
            receipt_expectations = expected.get("receipt_expectations", {})
            expected_blob_sha = expected.get("receipt_git_blob_sha")
            needs_receipt_inspection = bool(receipt_expectations) or expected_blob_sha is not None
            if needs_receipt_inspection:
                receipt_file = claim.get("receipt_file")
                if not receipt_file:
                    failures.append(
                        ContractFailure(
                            contract_id,
                            f"claim {claim_id!r} has receipt expectations but no receipt_file",
                        )
                    )
                    continue
                receipt_path = (manifest_path.parent / receipt_file).resolve()
                try:
                    receipt_path.relative_to(manifest_path.parent.resolve())
                    receipt = yaml.safe_load(receipt_path.read_text(encoding="utf-8"))
                except (OSError, ValueError, yaml.YAMLError) as exc:
                    failures.append(
                        ContractFailure(
                            contract_id,
                            f"claim {claim_id!r} receipt could not be inspected: {exc}",
                        )
                    )
                    continue

                if expected_blob_sha is not None:
                    observed_blob_sha = _git_blob_sha(receipt_path)
                    if observed_blob_sha != expected_blob_sha:
                        failures.append(
                            ContractFailure(
                                contract_id,
                                (
                                    f"claim {claim_id!r} receipt git blob sha "
                                    f"expected {expected_blob_sha!r}, "
                                    f"observed {observed_blob_sha!r}"
                                ),
                            )
                        )

                for receipt_path_key, wanted in receipt_expectations.items():
                    try:
                        observed = _get_path(receipt, receipt_path_key)
                    except KeyError:
                        failures.append(
                            ContractFailure(
                                contract_id,
                                (
                                    f"claim {claim_id!r} receipt path "
                                    f"{receipt_path_key!r} is missing"
                                ),
                            )
                        )
                        continue
                    if observed != wanted:
                        failures.append(
                            ContractFailure(
                                contract_id,
                                (
                                    f"claim {claim_id!r} receipt path "
                                    f"{receipt_path_key!r} expected {wanted!r}, "
                                    f"observed {observed!r}"
                                ),
                            )
                        )

            for expected_key, payload_key in field_map.items():
                if expected_key not in expected:
                    continue
                observed = claim.get(payload_key)
                wanted = expected[expected_key]
                if observed != wanted:
                    failures.append(
                        ContractFailure(
                            contract_id,
                            (
                                f"claim {claim_id!r} field {payload_key!r} "
                                f"expected {wanted!r}, observed {observed!r}"
                            ),
                        )
                    )

    return failures
