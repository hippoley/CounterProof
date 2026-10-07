"""Reviewer-facing claim/evidence matrices with mechanical proof semantics."""
from __future__ import annotations

import json
import unicodedata
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from pydantic import AnyHttpUrl, BaseModel, Field, TypeAdapter, ValidationError, model_validator


class SubmittedTestEvidence(str, Enum):
    WITNESSED = "WITNESSED"
    NOT_WITNESSED = "NOT_WITNESSED"
    UNPROVEN = "UNPROVEN"


class OracleAlignment(str, Enum):
    ALIGNED = "ALIGNED"
    CONTRADICTED = "CONTRADICTED"
    UNVERIFIED = "UNVERIFIED"


class OracleApplicability(str, Enum):
    APPLICABLE = "APPLICABLE"
    PRECONDITION_MISSING = "PRECONDITION_MISSING"


class EvidenceScope(str, Enum):
    IMPLEMENTATION = "IMPLEMENTATION"
    BEHAVIOR = "BEHAVIOR"
    SAFETY = "SAFETY"

    @property
    def rank(self) -> int:
        return {
            EvidenceScope.IMPLEMENTATION: 1,
            EvidenceScope.BEHAVIOR: 2,
            EvidenceScope.SAFETY: 3,
        }[self]


class OverallClaim(str, Enum):
    PROVEN = "PROVEN"
    CONTRADICTED = "CONTRADICTED"
    WITNESSED_SUBMITTED_JUDGE = "WITNESSED (submitted judge)"
    WITNESSED_SCOPE_INSUFFICIENT = "WITNESSED (scope insufficient)"
    WITNESSED_ORACLE_PRECONDITION_MISSING = (
        "WITNESSED (oracle precondition missing)"
    )
    UNPROVEN = "UNPROVEN"


_HTTP_SOURCE = TypeAdapter(AnyHttpUrl)


def _is_absolute_http_url(value: str | None) -> bool:
    """Validate an inspectable HTTP(S) provenance reference without fetching it."""
    if not value or any(
        char == "\\" or char.isspace() or unicodedata.category(char) in {"Cc", "Cf"}
        for char in value
    ):
        return False
    try:
        parts = urlsplit(value)
        if not parts.hostname:
            return False
        _HTTP_SOURCE.validate_python(value)
    except ValueError:
        return False
    return True


class ClaimEvidence(BaseModel):
    id: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    source_url: str | None = None
    tests: list[str] = Field(default_factory=list)
    base_result: str | None = None
    head_result: str | None = None
    submitted_test_evidence: SubmittedTestEvidence
    evidence_scope: EvidenceScope = EvidenceScope.BEHAVIOR
    required_scope: EvidenceScope = EvidenceScope.BEHAVIOR
    oracle_alignment: OracleAlignment = OracleAlignment.UNVERIFIED
    oracle_applicability: OracleApplicability = OracleApplicability.APPLICABLE
    oracle_precondition: str | None = None
    oracle_probe: str | None = None
    oracle_source_url: str | None = None
    receipt_file: str | None = None
    receipt_expected_verdicts: list[str] = Field(default_factory=list)
    receipt_expected_case: str | None = None
    receipt_observed_verdict: str | None = None
    receipt_case: str | None = None
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
        }:
            if not self.oracle_probe or not self.oracle_probe.strip():
                raise ValueError(
                    "ALIGNED / CONTRADICTED oracle status requires an explicit oracle_probe"
                )
            if not _is_absolute_http_url(self.oracle_source_url):
                raise ValueError(
                    "ALIGNED / CONTRADICTED oracle status requires oracle_source_url "
                    "as an absolute http(s) URL with a host"
                )

        if self.receipt_file:
            if not self.receipt_expected_verdicts:
                raise ValueError(
                    "receipt_file requires at least one receipt_expected_verdict"
                )
            if not self.receipt_expected_case or not self.receipt_expected_case.strip():
                raise ValueError(
                    "receipt_file requires a non-empty receipt_expected_case"
                )

        if self.oracle_applicability is OracleApplicability.PRECONDITION_MISSING:
            if self.oracle_alignment is not OracleAlignment.UNVERIFIED:
                raise ValueError(
                    "PRECONDITION_MISSING oracle applicability requires "
                    "oracle_alignment=UNVERIFIED"
                )
            if not self.oracle_precondition:
                raise ValueError(
                    "PRECONDITION_MISSING oracle applicability requires "
                    "an explicit oracle_precondition"
                )
        return self

    @property
    def scope_sufficient(self) -> bool:
        return self.evidence_scope.rank >= self.required_scope.rank

    @property
    def overall_claim(self) -> OverallClaim:
        # An applicable authoritative oracle outranks the submitted judge.
        if (
            self.oracle_applicability is OracleApplicability.APPLICABLE
            and self.oracle_alignment is OracleAlignment.CONTRADICTED
        ):
            return OverallClaim.CONTRADICTED
        if (
            self.submitted_test_evidence is SubmittedTestEvidence.WITNESSED
            and self.oracle_applicability is OracleApplicability.APPLICABLE
            and self.oracle_alignment is OracleAlignment.ALIGNED
        ):
            return OverallClaim.PROVEN

        # Without an authoritative resolution, preserve independent limits.
        if (
            self.submitted_test_evidence is SubmittedTestEvidence.WITNESSED
            and not self.scope_sufficient
        ):
            return OverallClaim.WITNESSED_SCOPE_INSUFFICIENT
        if (
            self.oracle_applicability
            is OracleApplicability.PRECONDITION_MISSING
            and self.submitted_test_evidence is SubmittedTestEvidence.WITNESSED
        ):
            return OverallClaim.WITNESSED_ORACLE_PRECONDITION_MISSING
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
    runner_url: str | None = None
    evidence_digest: str | None = None
    claims: list[ClaimEvidence] = Field(min_length=1)


def _bind_receipt(path: Path, claim: ClaimEvidence) -> None:
    if not claim.receipt_file:
        return

    manifest_dir = path.parent.resolve()
    receipt_path = (manifest_dir / claim.receipt_file).resolve()
    try:
        receipt_path.relative_to(manifest_dir)
    except ValueError as exc:
        raise ValueError(
            f"claim {claim.id!r} receipt_file must stay within the "
            "claim-matrix directory"
        ) from exc

    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"claim {claim.id!r} receipt could not be loaded: "
            f"{claim.receipt_file}: {exc}"
        ) from exc

    verdict = receipt.get("verdict")
    if not isinstance(verdict, str) or not verdict:
        raise ValueError(
            f"claim {claim.id!r} receipt must contain a non-empty string verdict"
        )

    claim.receipt_observed_verdict = verdict
    case = receipt.get("case")
    claim.receipt_case = case if isinstance(case, str) and case else None

    if not isinstance(case, str) or not case:
        raise ValueError(
            f"claim {claim.id!r} receipt must contain a non-empty string case"
        )
    if case != claim.receipt_expected_case:
        raise ValueError(
            f"claim {claim.id!r} receipt case {case!r} does not match "
            f"expected case {claim.receipt_expected_case!r}"
        )

    if (
        claim.receipt_expected_verdicts
        and verdict not in claim.receipt_expected_verdicts
    ):
        expected = ", ".join(claim.receipt_expected_verdicts)
        raise ValueError(
            f"claim {claim.id!r} receipt verdict {verdict!r} does not match "
            f"expected verdict(s): {expected}"
        )


def load_claim_matrix(path: Path) -> ClaimMatrixManifest:
    text = path.read_text(encoding="utf-8")
    try:
        if path.suffix.lower() == ".json":
            raw: Any = json.loads(text)
        else:
            raw = yaml.safe_load(text)
        manifest = ClaimMatrixManifest.model_validate(raw)
        for claim in manifest.claims:
            _bind_receipt(path, claim)
        return manifest
    except (json.JSONDecodeError, yaml.YAMLError, ValidationError, TypeError) as exc:
        raise ValueError(f"invalid claim matrix manifest: {exc}") from exc


def claim_matrix_to_dict(manifest: ClaimMatrixManifest) -> dict[str, Any]:
    payload = manifest.model_dump(mode="json")
    for claim, raw in zip(manifest.claims, payload["claims"], strict=True):
        raw["scope_sufficient"] = claim.scope_sufficient
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
        "> unless the relevant oracle is independently aligned and the evidence scope reaches",
        "> the scope required by the claim.",
        "",
    ]

    if manifest.source_pr:
        lines.append(f"- Source PR: {manifest.source_pr}")
    if manifest.base_sha:
        lines.append(f"- BASE: `{manifest.base_sha}`")
    if manifest.head_sha:
        lines.append(f"- HEAD: `{manifest.head_sha}`")
    if manifest.runner_url:
        lines.append(f"- Runner: {manifest.runner_url}")
    if manifest.evidence_digest:
        lines.append(f"- Evidence digest: `{manifest.evidence_digest}`")
    if (
        manifest.source_pr
        or manifest.base_sha
        or manifest.head_sha
        or manifest.runner_url
        or manifest.evidence_digest
    ):
        lines.append("")

    lines.extend(
        [
            "## Claim / evidence matrix",
            "",
            (
                "| Claim | Exact test(s) | BASE | HEAD | Submitted-test evidence | "
                "Evidence scope | Required scope | Oracle applicability | "
                "Oracle alignment | Overall claim |"
            ),
            "|---|---|---|---|---|---|---|---|---|---|",
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
                    f"**{claim.evidence_scope.value}**",
                    f"**{claim.required_scope.value}**",
                    f"**{claim.oracle_applicability.value}**",
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
        or claim.oracle_precondition
        or claim.receipt_file
        or not claim.scope_sufficient
    ]
    if details:
        lines.extend(["", "## Evidence details", ""])
        for claim in details:
            lines.append(f"### {claim.id}")
            lines.append("")
            if claim.source_url:
                lines.append(f"- Claim source: {claim.source_url}")
            lines.append(
                f"- Scope: evidence `{claim.evidence_scope.value}` -> "
                f"required `{claim.required_scope.value}` "
                f"({'sufficient' if claim.scope_sufficient else 'INSUFFICIENT'})"
            )
            lines.append(
                f"- Oracle applicability: `{claim.oracle_applicability.value}`"
            )
            if claim.oracle_precondition:
                lines.append(
                    f"- Oracle precondition: {_cell(claim.oracle_precondition)}"
                )
            if claim.oracle_probe:
                lines.append(f"- Oracle probe: {_cell(claim.oracle_probe)}")
            if claim.oracle_source_url:
                lines.append(f"- Oracle source: {claim.oracle_source_url}")
            if claim.receipt_file:
                lines.append(f"- Receipt file: `{claim.receipt_file}`")
                lines.append(
                    "- Receipt expected verdict(s): "
                    + ", ".join(
                        f"`{item}`" for item in claim.receipt_expected_verdicts
                    )
                )
                lines.append(
                    f"- Receipt observed verdict: "
                    f"`{claim.receipt_observed_verdict or 'UNBOUND'}`"
                )
                lines.append(
                    f"- Receipt expected case: {_cell(claim.receipt_expected_case)}"
                )
                if claim.receipt_case:
                    lines.append(
                        f"- Receipt observed case: {_cell(claim.receipt_case)}"
                    )
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
            "- Evidence scope: `IMPLEMENTATION < BEHAVIOR < SAFETY`",
            "- Oracle applicability: `APPLICABLE / PRECONDITION_MISSING`",
            "- Oracle alignment: `ALIGNED / CONTRADICTED / UNVERIFIED`",
            (
                "- `WITNESSED (scope insufficient)` means the candidate delta is real, "
                "but the evidence only reaches a shallower scope than the claim requires."
            ),
            (
                "- `WITNESSED (submitted judge)` means the submitted test distinguishes "
                "BASE from HEAD, reaches the declared claim scope, and product-oracle "
                "alignment remains unverified."
            ),
            (
                "- `WITNESSED (oracle precondition missing)` means the candidate delta "
                "is real, but the authoritative oracle cannot be interpreted on the "
                "current fixture because a declared prerequisite is absent."
            ),
            (
                "- `PROVEN` requires both a witnessed submitted regression and an "
                "applicable, aligned authoritative oracle."
            ),
            "- `CONTRADICTED` wins whenever the authoritative oracle contradicts the claim.",
            "- Otherwise the overall claim remains `UNPROVEN`.",
            "",
        ]
    )
    return "\n".join(lines)
