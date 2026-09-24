"""Reviewer-facing claim/evidence matrices with mechanical proof semantics."""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator


class SubmittedTestEvidence(str, Enum):
    WITNESSED = "WITNESSED"
    NOT_WITNESSED = "NOT_WITNESSED"
    UNPROVEN = "UNPROVEN"


class OracleAlignment(str, Enum):
    ALIGNED = "ALIGNED"
    CONTRADICTED = "CONTRADICTED"
    UNVERIFIED = "UNVERIFIED"


class OverallClaim(str, Enum):
    PROVEN = "PROVEN"
    CONTRADICTED = "CONTRADICTED"
    WITNESSED_SUBMITTED_JUDGE = "WITNESSED (submitted judge)"
    UNPROVEN = "UNPROVEN"


class ClaimEvidence(BaseModel):
    id: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    source_url: str | None = None
    tests: list[str] = Field(default_factory=list)
    base_result: str | None = None
    head_result: str | None = None
    submitted_test_evidence: SubmittedTestEvidence
    oracle_alignment: OracleAlignment = OracleAlignment.UNVERIFIED
    oracle_probe: str | None = None
    oracle_source_url: str | None = None
    assertion_excerpt: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_evidence_contract(self) -> ClaimEvidence:
        if self.submitted_test_evidence in {
            SubmittedTestEvidence.WITNESSED,
            SubmittedTestEvidence.NOT_WITNESSED,
        }:
            if not self.tests:
                raise ValueError(
                    "WITNESSED / NOT_WITNESSED claims require at least one exact test"
                )
            if not self.base_result or not self.head_result:
                raise ValueError(
                    "WITNESSED / NOT_WITNESSED claims require BASE and HEAD results"
                )

        if self.oracle_alignment in {
            OracleAlignment.ALIGNED,
            OracleAlignment.CONTRADICTED,
        } and not self.oracle_probe:
            raise ValueError(
                "ALIGNED / CONTRADICTED oracle status requires an explicit oracle_probe"
            )
        return self

    @property
    def overall_claim(self) -> OverallClaim:
        if self.oracle_alignment is OracleAlignment.CONTRADICTED:
            return OverallClaim.CONTRADICTED
        if (
            self.submitted_test_evidence is SubmittedTestEvidence.WITNESSED
            and self.oracle_alignment is OracleAlignment.ALIGNED
        ):
            return OverallClaim.PROVEN
        if (
            self.submitted_test_evidence is SubmittedTestEvidence.WITNESSED
            and self.oracle_alignment is OracleAlignment.UNVERIFIED
        ):
            return OverallClaim.WITNESSED_SUBMITTED_JUDGE
        return OverallClaim.UNPROVEN


class ClaimMatrixManifest(BaseModel):
    schema_version: int = 1
    title: str = Field(min_length=1)
    source_pr: str | None = None
    base_sha: str | None = None
    head_sha: str | None = None
    claims: list[ClaimEvidence] = Field(min_length=1)


def load_claim_matrix(path: Path) -> ClaimMatrixManifest:
    text = path.read_text(encoding="utf-8")
    try:
        if path.suffix.lower() == ".json":
            raw: Any = json.loads(text)
        else:
            raw = yaml.safe_load(text)
        return ClaimMatrixManifest.model_validate(raw)
    except (json.JSONDecodeError, yaml.YAMLError, ValidationError, TypeError) as exc:
        raise ValueError(f"invalid claim matrix manifest: {exc}") from exc


def claim_matrix_to_dict(manifest: ClaimMatrixManifest) -> dict[str, Any]:
    payload = manifest.model_dump(mode="json")
    for claim, raw in zip(manifest.claims, payload["claims"], strict=True):
        raw["overall_claim"] = claim.overall_claim.value
    return payload


def _cell(value: str | None) -> str:
    if not value:
        return "—"
    return value.replace("|", "\\|").replace("\n", " ")


def render_claim_matrix_markdown(manifest: ClaimMatrixManifest) -> str:
    lines = [
        f"# {manifest.title}",
        "",
        "> Evidence is scoped per claim. A green submitted test is not product-level proof",
        "> unless the relevant oracle is independently aligned.",
        "",
    ]

    if manifest.source_pr:
        lines.append(f"- Source PR: {manifest.source_pr}")
    if manifest.base_sha:
        lines.append(f"- BASE: `{manifest.base_sha}`")
    if manifest.head_sha:
        lines.append(f"- HEAD: `{manifest.head_sha}`")
    if manifest.source_pr or manifest.base_sha or manifest.head_sha:
        lines.append("")

    lines.extend(
        [
            "## Claim / evidence matrix",
            "",
            (
                "| Claim | Exact test(s) | BASE | HEAD | Submitted-test evidence | "
                "Oracle alignment | Overall claim |"
            ),
            "|---|---|---|---|---|---|---|",
        ]
    )

    for claim in manifest.claims:
        tests = "<br>".join(f"`{item}`" for item in claim.tests) if claim.tests else "—"
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(claim.claim),
                    tests,
                    _cell(claim.base_result),
                    _cell(claim.head_result),
                    f"**{claim.submitted_test_evidence.value}**",
                    f"**{claim.oracle_alignment.value}**",
                    f"**{claim.overall_claim.value}**",
                ]
            )
            + " |"
        )

    details = [
        claim
        for claim in manifest.claims
        if claim.assertion_excerpt
        or claim.oracle_probe
        or claim.note
        or claim.source_url
        or claim.oracle_source_url
    ]
    if details:
        lines.extend(["", "## Evidence details", ""])
        for claim in details:
            lines.append(f"### {claim.id}")
            lines.append("")
            if claim.source_url:
                lines.append(f"- Claim source: {claim.source_url}")
            if claim.oracle_probe:
                lines.append(f"- Oracle probe: {_cell(claim.oracle_probe)}")
            if claim.oracle_source_url:
                lines.append(f"- Oracle source: {claim.oracle_source_url}")
            if claim.note:
                lines.append(f"- Note: {_cell(claim.note)}")
            if claim.assertion_excerpt:
                lines.extend(
                    [
                        "",
                        "Assertion / failure excerpt:",
                        "",
                        "```text",
                        claim.assertion_excerpt.rstrip(),
                        "```",
                    ]
                )
            lines.append("")

    lines.extend(
        [
            "## Vocabulary",
            "",
            "- Submitted-test evidence: `WITNESSED / NOT_WITNESSED / UNPROVEN`",
            "- Oracle alignment: `ALIGNED / CONTRADICTED / UNVERIFIED`",
            (
                "- `WITNESSED (submitted judge)` means the submitted test distinguishes "
                "BASE from HEAD while product-oracle alignment remains unverified."
            ),
            (
                "- `PROVEN` requires both a witnessed submitted regression and an aligned "
                "authoritative oracle."
            ),
            "- `CONTRADICTED` wins whenever the authoritative oracle contradicts the claim.",
            "- Otherwise the overall claim remains `UNPROVEN`.",
            "",
        ]
    )
    return "\n".join(lines)
