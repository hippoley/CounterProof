from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from pydantic import ValidationError
import pytest

from skill_factory.evolution.claim_matrix import (
    ClaimEvidence,
    ClaimMatrixManifest,
    OracleAlignment,
    OverallClaim,
    SubmittedTestEvidence,
    claim_matrix_to_dict,
    render_claim_matrix_markdown,
)
from skill_factory.evolution.cli import cli


def _claim(
    *,
    submitted: SubmittedTestEvidence,
    oracle: OracleAlignment,
    oracle_probe: str | None = None,
) -> ClaimEvidence:
    replayed = submitted in {
        SubmittedTestEvidence.WITNESSED,
        SubmittedTestEvidence.NOT_WITNESSED,
    }
    return ClaimEvidence(
        id="claim-1",
        claim="the reviewed behavior is correct",
        tests=["tests/test_behavior.py"] if replayed else [],
        base_result="FAIL" if replayed else None,
        head_result="PASS" if replayed else None,
        submitted_test_evidence=submitted,
        oracle_alignment=oracle,
        oracle_probe=oracle_probe,
    )


@pytest.mark.parametrize(
    ("submitted", "oracle", "oracle_probe", "expected"),
    [
        (
            SubmittedTestEvidence.WITNESSED,
            OracleAlignment.UNVERIFIED,
            None,
            OverallClaim.WITNESSED_SUBMITTED_JUDGE,
        ),
        (
            SubmittedTestEvidence.WITNESSED,
            OracleAlignment.ALIGNED,
            "product parser accepts the fixture",
            OverallClaim.PROVEN,
        ),
        (
            SubmittedTestEvidence.WITNESSED,
            OracleAlignment.CONTRADICTED,
            "product parser rejects the fixture",
            OverallClaim.CONTRADICTED,
        ),
        (
            SubmittedTestEvidence.NOT_WITNESSED,
            OracleAlignment.UNVERIFIED,
            None,
            OverallClaim.UNPROVEN,
        ),
        (
            SubmittedTestEvidence.UNPROVEN,
            OracleAlignment.ALIGNED,
            "product parser accepts the fixture",
            OverallClaim.UNPROVEN,
        ),
    ],
)
def test_overall_claim_is_mechanical(
    submitted: SubmittedTestEvidence,
    oracle: OracleAlignment,
    oracle_probe: str | None,
    expected: OverallClaim,
):
    claim = _claim(
        submitted=submitted,
        oracle=oracle,
        oracle_probe=oracle_probe,
    )

    assert claim.overall_claim is expected


def test_witnessed_claim_requires_exact_test_and_before_after_results():
    with pytest.raises(ValidationError, match="require at least one exact test"):
        ClaimEvidence(
            id="claim-1",
            claim="behavior",
            submitted_test_evidence=SubmittedTestEvidence.WITNESSED,
        )


def test_verified_or_contradicted_oracle_requires_probe():
    with pytest.raises(ValidationError, match="requires an explicit oracle_probe"):
        ClaimEvidence(
            id="claim-1",
            claim="behavior",
            submitted_test_evidence=SubmittedTestEvidence.UNPROVEN,
            oracle_alignment=OracleAlignment.CONTRADICTED,
        )


def test_render_keeps_submitted_judge_scope_explicit():
    manifest = ClaimMatrixManifest(
        title="Review matrix",
        source_pr="https://github.com/example/repo/pull/1",
        base_sha="base123",
        head_sha="head456",
        claims=[
            ClaimEvidence(
                id="authority-boundary",
                claim="authority boundary survives plugin-data changes",
                source_url="https://github.com/example/repo/pull/1#discussion_r1",
                tests=["tests/state.test.mjs"],
                base_result="FAIL",
                head_result="PASS",
                submitted_test_evidence=SubmittedTestEvidence.WITNESSED,
                oracle_alignment=OracleAlignment.UNVERIFIED,
                assertion_excerpt="expected false to be true",
            )
        ],
    )

    markdown = render_claim_matrix_markdown(manifest)
    payload = claim_matrix_to_dict(manifest)

    assert "**WITNESSED**" in markdown
    assert "**UNVERIFIED**" in markdown
    assert "**WITNESSED (submitted judge)**" in markdown
    assert "expected false to be true" in markdown
    assert "discussion_r1" in markdown
    assert payload["claims"][0]["overall_claim"] == "WITNESSED (submitted judge)"


def test_cli_renders_yaml_manifest_to_markdown_and_json(tmp_path: Path):
    manifest = tmp_path / "claims.yml"
    manifest.write_text(
        """
schema_version: 1
title: External review
source_pr: https://github.com/example/repo/pull/7
base_sha: abc
head_sha: def
claims:
  - id: fixture-validity
    claim: claimed-valid fixture matches product behavior
    tests:
      - tests/validate.sh
    base_result: FAIL
    head_result: PASS
    submitted_test_evidence: WITNESSED
    oracle_alignment: CONTRADICTED
    oracle_probe: product validator rejects the claimed-valid fixture
    oracle_source_url: https://github.com/example/repo/pull/7#issuecomment-1
    assertion_excerpt: submitted test accepts fixture
""".strip()
        + "\n",
        encoding="utf-8",
    )
    md_out = tmp_path / "matrix.md"
    json_out = tmp_path / "matrix.json"

    result = CliRunner().invoke(
        cli,
        [
            "claim-matrix",
            str(manifest),
            "--out",
            str(md_out),
            "--json-out",
            str(json_out),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Claims: 1" in result.output
    assert "**CONTRADICTED**" in md_out.read_text(encoding="utf-8")
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["claims"][0]["submitted_test_evidence"] == "WITNESSED"
    assert payload["claims"][0]["oracle_alignment"] == "CONTRADICTED"
    assert payload["claims"][0]["overall_claim"] == "CONTRADICTED"


def test_cli_rejects_soft_or_ambiguous_evidence_vocabulary(tmp_path: Path):
    manifest = tmp_path / "claims.yml"
    manifest.write_text(
        """
schema_version: 1
title: Bad vocabulary
claims:
  - id: ambiguous
    claim: behavior
    submitted_test_evidence: SUPPORTED
    oracle_alignment: UNVERIFIED
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["claim-matrix", str(manifest)])

    assert result.exit_code != 0
    assert "invalid claim matrix manifest" in result.output


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (
            Path("examples/claim_matrix/codex-plugin-cc-731.yml"),
            [
                "WITNESSED (submitted judge)",
                "UNPROVEN",
                "UNPROVEN",
            ],
        ),
        (
            Path("examples/claim_matrix/claude-code-89404.yml"),
            [
                "CONTRADICTED",
                "UNPROVEN",
            ],
        ),
    ],
)
def test_real_reviewer_cases_fit_mechanical_matrix(path: Path, expected: list[str]):
    from skill_factory.evolution.claim_matrix import load_claim_matrix

    manifest = load_claim_matrix(path)
    payload = claim_matrix_to_dict(manifest)
    markdown = render_claim_matrix_markdown(manifest)

    assert [item["overall_claim"] for item in payload["claims"]] == expected
    assert "SUPPORTED" not in markdown
