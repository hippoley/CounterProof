from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from pydantic import ValidationError

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

# Synthetic test input under the reserved .test TLD; it is never fetched.
TEST_ORACLE_SOURCE = "https://oracle-source.example.test/synthetic-test-input"
ASSERTED_ORACLES = [OracleAlignment.ALIGNED, OracleAlignment.CONTRADICTED]


def _claim(
    *,
    submitted: SubmittedTestEvidence,
    oracle: OracleAlignment,
    oracle_probe: str | None = None,
    oracle_source_url: str | None = None,
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
        oracle_source_url=oracle_source_url,
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
        oracle_source_url=TEST_ORACLE_SOURCE if oracle in ASSERTED_ORACLES else None,
    )

    assert claim.overall_claim is expected


def test_witnessed_claim_requires_exact_test_and_before_after_results():
    with pytest.raises(ValidationError, match="require at least one exact test"):
        ClaimEvidence(
            id="claim-1",
            claim="behavior",
            submitted_test_evidence=SubmittedTestEvidence.WITNESSED,
        )


@pytest.mark.parametrize("oracle", list(OracleAlignment))
@pytest.mark.parametrize(
    ("base_result", "head_result"),
    [
        ("PASS", "FAIL"),
        ("PASS", "PASS"),
        ("FAIL", "FAIL"),
        ("ERROR", "PASS"),
        ("FAIL", "SKIP"),
        ("failed", "passed"),
        ("FAIL", "PASS (2 tests)"),
    ],
)
def test_witnessed_claim_rejects_inconsistent_or_ambiguous_results(
    oracle: OracleAlignment, base_result: str, head_result: str
):
    with pytest.raises(ValidationError, match="WITNESSED claims require BASE=FAIL and HEAD=PASS"):
        ClaimEvidence(
            id="inconsistent-witness",
            claim="the submitted regression distinguishes the fix",
            tests=["tests/test_behavior.py"],
            base_result=base_result,
            head_result=head_result,
            submitted_test_evidence=SubmittedTestEvidence.WITNESSED,
            oracle_alignment=oracle,
            oracle_probe="caller-declared probe; never executed by this renderer",
        )


@pytest.mark.parametrize(
    ("head_result", "oracle"),
    [("FAIL", "ALIGNED"), ("PASS", "UNVERIFIED")],
)
def test_cli_rejects_inconsistent_witness_without_writing_outputs(
    tmp_path: Path, head_result: str, oracle: str
):
    manifest = tmp_path / "claims.json"
    manifest.write_text(
        json.dumps(
            {
                "title": "Known-bad evidence controls",
                "claims": [
                    {
                        "id": "inconsistent-witness",
                        "claim": "a regression witness requires a failing BASE and passing HEAD",
                        "tests": ["tests/nonexistent.py"],
                        "base_result": "PASS",
                        "head_result": head_result,
                        "submitted_test_evidence": "WITNESSED",
                        "oracle_alignment": oracle,
                        "oracle_probe": "unverified caller assertion",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    md_out = tmp_path / "matrix.md"
    json_out = tmp_path / "matrix.json"

    result = CliRunner().invoke(
        cli, ["claim-matrix", str(manifest), "--out", str(md_out), "--json-out", str(json_out)]
    )

    assert result.exit_code == 1, result.output
    assert "WITNESSED claims require BASE=FAIL and HEAD=PASS" in result.output
    assert not md_out.exists()
    assert not json_out.exists()


@pytest.mark.parametrize("oracle", ASSERTED_ORACLES)
@pytest.mark.parametrize("oracle_probe", [None, "", "   ", "\n\t"])
def test_asserted_oracle_rejects_blank_probe(oracle: OracleAlignment, oracle_probe: str | None):
    with pytest.raises(ValidationError, match="requires an explicit oracle_probe"):
        _claim(
            submitted=SubmittedTestEvidence.UNPROVEN,
            oracle=oracle,
            oracle_probe=oracle_probe,
            oracle_source_url=TEST_ORACLE_SOURCE,
        )


@pytest.mark.parametrize("oracle", ASSERTED_ORACLES)
@pytest.mark.parametrize(
    "oracle_source_url",
    [
        None,
        "",
        "   ",
        "oracle-source.example.test/no-scheme",
        "/relative/oracle/evidence",
        "//oracle-source.example.test/scheme-relative",
        "ftp://oracle-source.example.test/synthetic-test-input",
        "https://",
        "https:///path-without-host",
        "https://:443/port-without-host",
        "https:oracle-source.example.test/missing-slashes",
        " https://oracle-source.example.test/leading-space",
        "https://oracle-source.example.test/trailing-newline\n",
        "https://oracle-source.example.test/inner space",
        "https://oracle-source.example.test/inner\u00a0space",
        "https://oracle-source.example.test/control\x00char",
        "https://oracle-source.example.test/control\x7fchar",
        "https://oracle-source.example.test/control\x80char",
        "https://example.test/\u202evidence",
        "https://exam\u200bple.test/evidence",
        "https://example.test/byte\ufefforder-mark",
        "https://evil.example\\@github.com/hippoley/CounterProof/pull/50",
        "https://example.test/evidence\\other",
        "https://oracle-source.example.test:99999/port-out-of-range",
        "https://oracle-source.example.test:port/non-numeric-port",
        "https://[2001:db8::1/unclosed-ipv6",
        "https://exa<mple.test/run",
        "https://user@/missing-host-after-userinfo",
        "https://[not-an-ip]/bad-literal",
        "https://[2001:db8::1]suffix/bad-bracketed-host",
    ],
)
def test_asserted_oracle_rejects_missing_or_malformed_source(
    oracle: OracleAlignment,
    oracle_source_url: str | None,
):
    with pytest.raises(ValidationError, match="requires oracle_source_url"):
        _claim(
            submitted=SubmittedTestEvidence.UNPROVEN,
            oracle=oracle,
            oracle_probe="caller-declared probe; never executed by this renderer",
            oracle_source_url=oracle_source_url,
        )


@pytest.mark.parametrize(
    ("oracle", "expected"),
    [
        (OracleAlignment.ALIGNED, OverallClaim.PROVEN),
        (OracleAlignment.CONTRADICTED, OverallClaim.CONTRADICTED),
    ],
)
@pytest.mark.parametrize(
    "oracle_source_url",
    [
        TEST_ORACLE_SOURCE,
        "http://oracle-source.example.test/synthetic-test-input",
        "HTTPS://Oracle-Source.Example.Test/Synthetic?input=1#test",
        "https://oracle-source.example.test:8443/synthetic-test-input",
        "https://[2001:db8::1]/synthetic-test-input",
        "https://example.test/oracle%20run#result",
        "https://bücher.test/evidence",
    ],
)
def test_asserted_oracle_accepts_absolute_http_source_verbatim(
    oracle: OracleAlignment, expected: OverallClaim, oracle_source_url: str
):
    claim = _claim(
        submitted=SubmittedTestEvidence.WITNESSED,
        oracle=oracle,
        oracle_probe="caller-declared probe; never executed by this renderer",
        oracle_source_url=oracle_source_url,
    )

    assert claim.overall_claim is expected
    assert claim.oracle_source_url == oracle_source_url


@pytest.mark.parametrize(
    ("submitted", "oracle_probe", "expected"),
    [
        (SubmittedTestEvidence.WITNESSED, None, OverallClaim.WITNESSED_SUBMITTED_JUDGE),
        (SubmittedTestEvidence.UNPROVEN, None, OverallClaim.UNPROVEN),
        (
            SubmittedTestEvidence.WITNESSED,
            "probe text without a source",
            OverallClaim.WITNESSED_SUBMITTED_JUDGE,
        ),
    ],
)
def test_unverified_oracle_needs_neither_probe_nor_source(
    submitted: SubmittedTestEvidence, oracle_probe: str | None, expected: OverallClaim
):
    claim = _claim(
        submitted=submitted,
        oracle=OracleAlignment.UNVERIFIED,
        oracle_probe=oracle_probe,
    )

    assert claim.oracle_alignment is OracleAlignment.UNVERIFIED
    assert claim.overall_claim is expected


@pytest.mark.parametrize("oracle", ["ALIGNED", "CONTRADICTED"])
@pytest.mark.parametrize(
    "source_fields",
    [
        {},
        {"oracle_source_url": "   "},
        {"oracle_source_url": "oracle-source.example.test/no-scheme"},
        {"oracle_source_url": "https://example.test:99999/invalid-port"},
    ],
)
def test_cli_rejects_asserted_oracle_without_source_before_writing_outputs(
    tmp_path: Path, oracle: str, source_fields: dict[str, str]
):
    manifest = tmp_path / "claims.json"
    manifest.write_text(
        json.dumps(
            {
                "title": "Known-bad provenance controls",
                "claims": [
                    {
                        "id": "unsourced-oracle",
                        "claim": "an asserted oracle state needs an inspectable source",
                        "tests": ["tests/nonexistent.py"],
                        "base_result": "FAIL",
                        "head_result": "PASS",
                        "submitted_test_evidence": "WITNESSED",
                        "oracle_alignment": oracle,
                        "oracle_probe": "unverified caller assertion",
                        **source_fields,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    md_out = tmp_path / "matrix.md"
    json_out = tmp_path / "matrix.json"

    result = CliRunner().invoke(
        cli, ["claim-matrix", str(manifest), "--out", str(md_out), "--json-out", str(json_out)]
    )

    assert result.exit_code == 1, result.output
    assert "requires oracle_source_url" in result.output
    assert not md_out.exists()
    assert not json_out.exists()


@pytest.mark.parametrize("oracle", ASSERTED_ORACLES)
def test_render_keeps_oracle_provenance_in_markdown_and_json(oracle: OracleAlignment):
    probe = "caller-declared probe; never executed by this renderer"
    manifest = ClaimMatrixManifest(
        title="Provenance matrix",
        claims=[
            _claim(
                submitted=SubmittedTestEvidence.WITNESSED,
                oracle=oracle,
                oracle_probe=probe,
                oracle_source_url=TEST_ORACLE_SOURCE,
            )
        ],
    )

    markdown = render_claim_matrix_markdown(manifest)
    payload = claim_matrix_to_dict(manifest)

    assert f"- Oracle probe: {probe}" in markdown
    assert f"- Oracle source: {TEST_ORACLE_SOURCE}" in markdown
    assert payload["claims"][0]["oracle_probe"] == probe
    assert payload["claims"][0]["oracle_source_url"] == TEST_ORACLE_SOURCE


def test_render_keeps_submitted_judge_scope_explicit():
    manifest = ClaimMatrixManifest(
        title="Review matrix",
        source_pr="https://github.com/example/repo/pull/1",
        base_sha="base123",
        head_sha="head456",
        runner_url="https://github.com/example/proof/actions/runs/9",
        evidence_digest="sha256:abc123",
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
    assert "actions/runs/9" in markdown
    assert "sha256:abc123" in markdown
    assert payload["runner_url"] == "https://github.com/example/proof/actions/runs/9"
    assert payload["evidence_digest"] == "sha256:abc123"
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
        (
            Path("examples/claim_matrix/cognee-5161.yml"),
            ["UNPROVEN", "CONTRADICTED", "UNPROVEN"],
        ),
        (
            Path("examples/claim_matrix/crewai-7721.yml"),
            ["WITNESSED (submitted judge)", "CONTRADICTED", "UNPROVEN", "CONTRADICTED"],
        ),
        (
            Path("examples/claim_matrix/vercel-ai-17096.yml"),
            ["WITNESSED (submitted judge)", "UNPROVEN", "UNPROVEN"],
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
