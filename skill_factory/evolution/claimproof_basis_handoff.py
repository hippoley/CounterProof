from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX16 = re.compile(r"^[0-9a-f]{16}$")


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload).hexdigest()


def load_claimproof_basis_handoff(
    handoff_path: Path,
) -> dict[str, Any]:
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    if not isinstance(handoff, dict):
        raise TypeError("claimproof handoff must be an object")

    if handoff.get("schema_version") != "counterproof.claimproof-basis-handoff/v0":
        raise ValueError("unsupported claimproof handoff schema")

    producer = handoff.get("producer")
    if not isinstance(producer, dict):
        raise TypeError("producer must be an object")
    if producer.get("name") != "claimproof":
        raise ValueError("producer.name must be claimproof")
    source_blob = producer.get("basis_source_blob")
    if not isinstance(source_blob, str) or not _HEX40.fullmatch(source_blob):
        raise ValueError("producer basis_source_blob must be a 40-char git blob id")

    candidate = handoff.get("candidate")
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be an object")
    for field in ("repository", "identity"):
        value = candidate.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"candidate.{field} is required")

    basis_name = handoff.get("claim_basis_file")
    if not isinstance(basis_name, str) or not basis_name.strip():
        raise ValueError("claim_basis_file is required")

    basis_path = handoff_path.parent / basis_name
    if not basis_path.is_file():
        raise ValueError(f"claim basis file not found: {basis_name}")

    expected_blob = handoff.get("claim_basis_git_blob")
    if not isinstance(expected_blob, str) or not _HEX40.fullmatch(expected_blob):
        raise ValueError("claim_basis_git_blob must be a 40-char git blob id")
    observed_blob = _git_blob_sha(basis_path)
    if observed_blob != expected_blob:
        raise ValueError(
            "claim basis identity mismatch: "
            f"expected {expected_blob}, got {observed_blob}"
        )

    basis = json.loads(basis_path.read_text(encoding="utf-8"))
    if not isinstance(basis, dict):
        raise TypeError("claimproof basis store must be an object")
    if basis.get("version") != 1:
        raise ValueError("claimproof basis store version must be 1")

    claims = basis.get("claims")
    if not isinstance(claims, dict) or not claims:
        raise ValueError("claimproof basis store must contain claims")

    normalized_claims: list[dict[str, Any]] = []
    for claim_id, claim in sorted(claims.items()):
        if not isinstance(claim_id, str) or not claim_id:
            raise ValueError("claim id must be a non-empty string")
        if not isinstance(claim, dict):
            raise TypeError(f"claim {claim_id} must be an object")

        claim_text = claim.get("claim")
        recorded = claim.get("recorded")
        evidence = claim.get("evidence")
        scope = claim.get("scope", [])

        if not isinstance(claim_text, str) or not claim_text.strip():
            raise ValueError(f"claim {claim_id} is missing claim text")
        if not isinstance(recorded, str) or not recorded.strip():
            raise ValueError(f"claim {claim_id} is missing recorded timestamp")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"claim {claim_id} must contain evidence")
        if not isinstance(scope, list):
            raise TypeError(f"claim {claim_id} scope must be a list")

        normalized_evidence: list[dict[str, str]] = []
        for item in evidence:
            if not isinstance(item, dict):
                raise TypeError(f"claim {claim_id} evidence entry must be an object")
            ref = item.get("ref")
            digest = item.get("digest")
            kind = item.get("kind", "file")
            if not isinstance(ref, str) or not ref:
                raise ValueError(f"claim {claim_id} evidence.ref is required")
            if not isinstance(digest, str) or not _HEX16.fullmatch(digest):
                raise ValueError(
                    f"claim {claim_id} evidence.digest must match claimproof's "
                    "16-hex content fingerprint shape"
                )
            if kind not in {"file", "value"}:
                raise ValueError(f"claim {claim_id} evidence.kind is unsupported")
            normalized_evidence.append(
                {"ref": ref, "digest": digest, "kind": kind}
            )

        normalized_claims.append(
            {
                "claim_id": claim_id,
                "claim": claim_text,
                "recorded": recorded,
                "evidence": normalized_evidence,
                "scope": [str(item) for item in scope],
            }
        )

    return {
        "receipt_type": "CLAIMPROOF_DURABLE_BASIS_INPUT",
        "producer": producer,
        "candidate": candidate,
        "claim_basis": {
            "path": basis_name,
            "git_blob": observed_blob,
            "version": 1,
        },
        "claims": normalized_claims,
        "claim_count": len(normalized_claims),
        "admission": "BOUND_INPUT",
        "semantic_boundary": (
            "claimproof owns durable basis semantics; CounterProof only admits "
            "the candidate-bound input for later claim-scope evaluation"
        ),
    }
