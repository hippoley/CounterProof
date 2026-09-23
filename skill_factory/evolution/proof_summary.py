"""Aggregate Counterproof evidence into one conservative machine-readable verdict."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProofSummary:
    witness_status: str
    evidence_mode: str
    integrity_status: str
    proof_status: str
    proof_ready: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "witness_status": self.witness_status,
            "evidence_mode": self.evidence_mode,
            "integrity_status": self.integrity_status,
            "proof_status": self.proof_status,
            "proof_ready": self.proof_ready,
            "reasons": list(self.reasons),
        }


def build_proof_summary(
    witness: dict[str, Any],
    integrity: dict[str, Any],
) -> ProofSummary:
    """Combine witness + integrity evidence without overstating merge safety."""
    witness_status = str(witness.get("status", "unknown"))
    evidence_mode = str(witness.get("mode", "unknown"))
    integrity_status = str(integrity.get("status", "unknown"))
    reasons: list[str] = []

    if integrity_status == "review-required":
        proof_status = "review-required"
        reasons.append(
            "The PR changes one or more test/CI evidence surfaces, so proof is not independent."
        )
    elif integrity_status != "clean":
        proof_status = "integrity-unknown"
        reasons.append("Proof Integrity did not produce a clean, known result.")
    elif witness_status == "witnessed":
        if evidence_mode != "precise":
            proof_status = "inconclusive"
            reasons.append(
                "WITNESSED is only valid for precise changed-test replay."
            )
        else:
            proof_status = "verified"
            reasons.append(
                "The exact changed tests pass on PR head, fail on base, and the evidence surface is clean."
            )
    elif witness_status == "suite-delta":
        proof_status = "suite-delta"
        reasons.append(
            "The configured suite distinguishes head from base, but the changed test itself was not isolated."
        )
    elif witness_status == "not-witnessed":
        proof_status = "unproven"
        reasons.append(
            "The configured evidence also passes on base, so it does not witness the regression."
        )
    elif witness_status == "head-failing":
        proof_status = "head-failing"
        reasons.append("The configured test evidence does not pass on the PR head.")
    elif witness_status == "no-changed-tests":
        proof_status = "no-changed-tests"
        reasons.append("No changed regression test was detected.")
    elif witness_status == "inconclusive":
        proof_status = "inconclusive"
        reasons.append("Replay did not produce a trustworthy behavioral verdict.")
    else:
        proof_status = "unknown"
        reasons.append(f"Unknown witness status: {witness_status}")

    proof_ready = proof_status == "verified"
    return ProofSummary(
        witness_status=witness_status,
        evidence_mode=evidence_mode,
        integrity_status=integrity_status,
        proof_status=proof_status,
        proof_ready=proof_ready,
        reasons=tuple(reasons),
    )


def load_and_build_proof_summary(
    witness_path: Path,
    integrity_path: Path,
) -> ProofSummary:
    witness = json.loads(witness_path.read_text(encoding="utf-8"))
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    if not isinstance(witness, dict) or not isinstance(integrity, dict):
        raise ValueError("proof inputs must be JSON objects")
    return build_proof_summary(witness, integrity)


def write_proof_summary(path: Path, summary: ProofSummary) -> None:
    path.write_text(
        json.dumps(summary.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def render_proof_summary(summary: ProofSummary) -> str:
    ready = "true" if summary.proof_ready else "false"
    lines = [
        "# Counterproof · Proof Summary",
        "",
        f"- Proof status: **{summary.proof_status.upper().replace('-', ' ')}**",
        f"- Proof ready: **{ready}**",
        f"- Regression witness: **{summary.witness_status.upper().replace('-', ' ')}**",
        f"- Evidence mode: **{summary.evidence_mode.upper()}**",
        f"- Proof integrity: **{summary.integrity_status.upper().replace('-', ' ')}**",
        "",
        "> Proof-ready means Counterproof's configured evidence contract is satisfied.",
        "> It is not a general claim that the entire pull request is safe to merge.",
    ]
    if summary.reasons:
        lines.extend(["", "### Reason", ""])
        lines.extend(f"- {reason}" for reason in summary.reasons)
    return "\n".join(lines) + "\n"
