"""Independent verifier for SCITT Measurement Capsule draft semantics.

This module is intentionally implemented from the public draft text and RFC
primitives rather than importing the CSOAI prototype builder or verifier.

Scope:
- recompute capsule_id using RFC 8785/JCS with capsule_id excluded;
- validate stored JSONL lines are the exact JCS bytes for their capsule;
- recompute RFC 9162 Merkle Tree Hash over capsule_id bytes sorted ascending;
- preserve the draft's measurement-only / no-decision boundary.

It does not verify COSE, Transparency Service receipts, OpenTimestamps, or the
measurement instrument itself.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import rfc8785


CAPSULE_SCHEMA = "csoai.measurement-capsule/0.2"
AUTHORITY_NONE = (
    "NONE: measurement only; this capsule grants and records no execution authority"
)
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")

_FORBIDDEN_MEMBER_STEMS = {
    "decision",
    "allow",
    "allowed",
    "allowlist",
    "hold",
    "reject",
    "approve",
    "approved",
    "approval",
    "admit",
    "admission",
    "authority",
    "authorization",
    "authorisation",
    "permit",
    "permission",
    "grant",
    "enforce",
    "enforcement",
    "action",
    "recommended_action",
    "gate",
    "gate_result",
}

_FORBIDDEN_EXACT_VALUES = {
    "ALLOW",
    "HOLD",
    "REJECT",
    "DENY",
    "APPROVE",
    "APPROVED",
    "ADMIT",
    "ADMITTED",
    "BLOCK",
    "PERMIT",
    "GRANT",
}


class MeasurementCapsuleError(ValueError):
    """Raised when a capsule violates the draft-level verification boundary."""


@dataclass(frozen=True)
class CapsuleVerification:
    capsule_id: str
    canonical_bytes: bytes
    stored_line_matches_jcs: bool


@dataclass(frozen=True)
class BatchVerification:
    n_capsules: int
    merkle_root: str
    capsule_ids: tuple[str, ...]
    duplicate_ids: tuple[str, ...]


def _canonical_without_id(capsule: dict[str, Any]) -> bytes:
    payload = dict(capsule)
    payload.pop("capsule_id", None)
    try:
        return rfc8785.dumps(payload)
    except Exception as exc:  # library-specific canonicalization subclasses vary
        raise MeasurementCapsuleError(f"JCS canonicalization failed: {exc}") from exc


def recompute_capsule_id(capsule: dict[str, Any]) -> str:
    """Recompute draft Section 4 capsule_id from JCS bytes."""
    if not isinstance(capsule, dict):
        raise TypeError("capsule must be a JSON object")
    return hashlib.sha256(_canonical_without_id(capsule)).hexdigest()


def _walk_no_decision_surface(value: Any, *, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if key_text != "authority_state":
                normalized = key_text.lower().replace("-", "_")
                if normalized in _FORBIDDEN_MEMBER_STEMS:
                    where = ".".join((*path, key_text))
                    raise MeasurementCapsuleError(
                        f"forbidden decision/authority member at {where}"
                    )
            _walk_no_decision_surface(child, path=(*path, key_text))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_no_decision_surface(child, path=(*path, str(index)))
    elif isinstance(value, str) and value in _FORBIDDEN_EXACT_VALUES:
        where = ".".join(path)
        raise MeasurementCapsuleError(
            f"forbidden decision-like string value at {where or '<root>'}"
        )


def _validate_sources(value: Any, *, path: str = "sources") -> None:
    if value is None:
        return
    if isinstance(value, str):
        digest = value.removeprefix("sha256:")
        if not re.fullmatch(r"[0-9a-f]{40,128}", digest):
            raise MeasurementCapsuleError(
                f"{path} contains a non-digest string"
            )
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _validate_sources(child, path=f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, child in value.items():
            _validate_sources(child, path=f"{path}.{key}")
        return
    raise MeasurementCapsuleError(
        f"{path} contains evidence bytes/free-text instead of digests"
    )


def validate_capsule_shape(capsule: dict[str, Any]) -> None:
    if capsule.get("schema") != CAPSULE_SCHEMA:
        raise MeasurementCapsuleError(
            f"unsupported capsule schema: {capsule.get('schema')!r}"
        )
    kind = capsule.get("kind")
    if not isinstance(kind, str) or not re.fullmatch(r"measurement\.[a-z0-9_]+", kind):
        raise MeasurementCapsuleError("invalid measurement kind")
    if capsule.get("authority_state") != AUTHORITY_NONE:
        raise MeasurementCapsuleError("authority_state must be measurement-only NONE")
    capsule_id = capsule.get("capsule_id")
    if not isinstance(capsule_id, str) or not _SHA256_HEX.fullmatch(capsule_id):
        raise MeasurementCapsuleError("capsule_id must be 64 lowercase hex characters")
    state = capsule.get("measurement_state")
    if not isinstance(state, str) or not (1 <= len(state) <= 64):
        raise MeasurementCapsuleError("measurement_state must be a non-empty short string")
    limitations = capsule.get("limitations")
    if not isinstance(limitations, list):
        raise MeasurementCapsuleError("limitations must be a list")
    _validate_sources(capsule.get("sources"))
    _walk_no_decision_surface(capsule)


def verify_capsule(capsule: dict[str, Any], *, stored_line: bytes | None = None) -> CapsuleVerification:
    """Verify identifier, no-decision boundary, and optional canonical stored line."""
    validate_capsule_shape(capsule)
    expected = recompute_capsule_id(capsule)
    if capsule["capsule_id"] != expected:
        raise MeasurementCapsuleError(
            f"capsule_id mismatch: stored={capsule['capsule_id']} recomputed={expected}"
        )

    canonical_full = rfc8785.dumps(capsule)
    line_matches = True
    if stored_line is not None:
        candidate = stored_line[:-1] if stored_line.endswith(b"\n") else stored_line
        line_matches = candidate == canonical_full
        if not line_matches:
            raise MeasurementCapsuleError(
                "stored capsule line is not the exact JCS serialization"
            )

    return CapsuleVerification(
        capsule_id=expected,
        canonical_bytes=canonical_full,
        stored_line_matches_jcs=line_matches,
    )


def _leaf_hash(capsule_id_hex: str) -> bytes:
    if not _SHA256_HEX.fullmatch(capsule_id_hex):
        raise MeasurementCapsuleError(f"invalid capsule id leaf: {capsule_id_hex!r}")
    return hashlib.sha256(b"\x00" + bytes.fromhex(capsule_id_hex)).digest()


def _node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _largest_power_of_two_less_than(n: int) -> int:
    if n < 2:
        raise ValueError("n must be >= 2")
    return 1 << ((n - 1).bit_length() - 1)


def _mth_from_ids(sorted_ids: Sequence[str]) -> bytes:
    n = len(sorted_ids)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return _leaf_hash(sorted_ids[0])
    k = _largest_power_of_two_less_than(n)
    return _node_hash(
        _mth_from_ids(sorted_ids[:k]),
        _mth_from_ids(sorted_ids[k:]),
    )


def recompute_batch_merkle_root(capsule_ids: Iterable[str]) -> BatchVerification:
    """Recompute RFC 9162 Merkle Tree Hash over sorted capsule_id bytes."""
    ids = tuple(capsule_ids)
    counts: dict[str, int] = {}
    for item in ids:
        if not isinstance(item, str) or not _SHA256_HEX.fullmatch(item):
            raise MeasurementCapsuleError(f"invalid capsule_id: {item!r}")
        counts[item] = counts.get(item, 0) + 1
    duplicates = tuple(sorted(item for item, count in counts.items() if count > 1))
    if duplicates:
        raise MeasurementCapsuleError(
            "duplicate capsule_id values are not permitted in a batch: "
            + ", ".join(duplicates)
        )

    ordered = tuple(sorted(ids, key=lambda item: bytes.fromhex(item)))
    root = _mth_from_ids(ordered).hex()
    return BatchVerification(
        n_capsules=len(ordered),
        merkle_root=root,
        capsule_ids=ordered,
        duplicate_ids=(),
    )


def verify_jsonl_batch(
    lines: Iterable[bytes],
    *,
    expected_merkle_root: str | None = None,
    expected_n_capsules: int | None = None,
) -> BatchVerification:
    """Verify canonical capsule lines and recompute the published batch root."""
    ids: list[str] = []
    previous: str | None = None
    for line_number, raw in enumerate(lines, start=1):
        if not raw.strip():
            raise MeasurementCapsuleError(
                f"blank capsule line at {line_number}"
            )
        try:
            capsule = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MeasurementCapsuleError(
                f"invalid JSON at line {line_number}: {exc}"
            ) from exc
        result = verify_capsule(capsule, stored_line=raw)
        if previous is not None and result.capsule_id <= previous:
            raise MeasurementCapsuleError(
                "capsule file is not strictly sorted by capsule_id"
            )
        previous = result.capsule_id
        ids.append(result.capsule_id)

    batch = recompute_batch_merkle_root(ids)
    if expected_n_capsules is not None and batch.n_capsules != expected_n_capsules:
        raise MeasurementCapsuleError(
            f"capsule count mismatch: got={batch.n_capsules} expected={expected_n_capsules}"
        )
    if expected_merkle_root is not None and batch.merkle_root != expected_merkle_root:
        raise MeasurementCapsuleError(
            f"Merkle root mismatch: got={batch.merkle_root} expected={expected_merkle_root}"
        )
    return batch
