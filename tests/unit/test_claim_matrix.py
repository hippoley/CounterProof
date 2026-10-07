from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from skill_factory.evolution.claim_matrix import (
    ClaimEvidence,
    ClaimMatrixManifest,
    EvidenceScope,
    OracleAlignment,
    OracleApplicability,
    OverallClaim,
    SubmittedTestEvidence,
    claim_matrix_to_dict,
    render_claim_matrix_markdown,
)
from skill_factory.evolution.cli import cli

TEST_ORACLE_SOURCE = "https://oracle-source.example.test/synthetic-test-input"
ASSERTED_ORACLES = {OracleAlignment.ALIGNED, OracleAlignment.CONTRADICTED}


def _claim(
    *,
    submitted: SubmittedTestEvidence,
    oracle: OracleAlignment,
    oracle_probe: str | None = None,
    oracle_source_url: str | None = None,
    evidence_scope: EvidenceScope = EvidenceScope.BEHAVIOR,
    required_scope: EvidenceScope = EvidenceScope.BEHAVIOR,
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
        evidence_scope=evidence_scope,
        required_scope=required_scope,
        oracle_alignment=oracle,
        oracle_probe=oracle_probe,
        oracle_source_url=(
            oracle_source_url
            if oracle_source_url is not None
            else TEST_ORACLE_SOURCE if oracle in ASSERTED_ORACLES else None
        ),
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


def test_witnessed_implementation_delta_cannot_prove_behavior_claim():
    claim = _claim(
        submitted=SubmittedTestEvidence.WITNESSED,
        oracle=OracleAlignment.UNVERIFIED,
        evidence_scope=EvidenceScope.IMPLEMENTATION,
        required_scope=EvidenceScope.BEHAVIOR,
    )

    assert claim.scope_sufficient is False
    assert claim.overall_claim is OverallClaim.WITNESSED_SCOPE_INSUFFICIENT


def test_behavior_evidence_is_insufficient_for_safety_claim_without_safety_oracle():
    claim = _claim(
        submitted=SubmittedTestEvidence.WITNESSED,
        oracle=OracleAlignment.UNVERIFIED,
        evidence_scope=EvidenceScope.BEHAVIOR,
        required_scope=EvidenceScope.SAFETY,
    )

    assert claim.scope_sufficient is False
    assert claim.overall_claim is OverallClaim.WITNESSED_SCOPE_INSUFFICIENT


def test_aligned_authoritative_oracle_can_close_scope_gap():
    claim = _claim(
        submitted=SubmittedTestEvidence.WITNESSED,
        oracle=OracleAlignment.ALIGNED,
        oracle_probe="real session proves safe startup and Secret portal availability",
        evidence_scope=EvidenceScope.IMPLEMENTATION,
        required_scope=EvidenceScope.SAFETY,
    )

    assert claim.scope_sufficient is False
    assert claim.overall_claim is OverallClaim.PROVEN


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
            oracle_source_url=TEST_ORACLE_SOURCE,
        )


@pytest.mark.parametrize("oracle", [OracleAlignment.ALIGNED, OracleAlignment.CONTRADICTED])
@pytest.mark.parametrize(
    "oracle_source_url",
    [
        None,
        "",
        "oracle-source.example.test/no-scheme",
        "/relative/evidence",
        "ftp://oracle-source.example.test/evidence",
        "https://",
        " https://oracle-source.example.test/leading-space",
        "https://oracle-source.example.test/inner space",
        r"https://example.test/evidence\other",
        "https://oracle-source.example.test:99999/invalid-port",
    ],
)
def test_asserted_oracle_requires_auditable_http_source(
    oracle: OracleAlignment,
    oracle_source_url: str | None,
):
    with pytest.raises(ValidationError, match="requires oracle_source_url"):
        ClaimEvidence(
            id="claim-1",
            claim="behavior",
            submitted_test_evidence=SubmittedTestEvidence.UNPROVEN,
            oracle_alignment=oracle,
            oracle_probe="authoritative product probe",
            oracle_source_url=oracle_source_url,
        )


@pytest.mark.parametrize("oracle", [OracleAlignment.ALIGNED, OracleAlignment.CONTRADICTED])
def test_asserted_oracle_accepts_absolute_http_source(oracle: OracleAlignment):
    claim = ClaimEvidence(
        id="claim-1",
        claim="behavior",
        submitted_test_evidence=SubmittedTestEvidence.UNPROVEN,
        oracle_alignment=oracle,
        oracle_probe="authoritative product probe",
        oracle_source_url=TEST_ORACLE_SOURCE,
    )

    assert claim.oracle_source_url == TEST_ORACLE_SOURCE


def test_cli_rejects_unsourced_asserted_oracle_without_writing_outputs(tmp_path: Path):
    manifest = tmp_path / "claims.json"
    manifest.write_text(
        json.dumps(
            {
                "title": "Known-bad provenance control",
                "claims": [
                    {
                        "id": "unsourced-oracle",
                        "claim": "asserted oracle states need inspectable provenance",
                        "submitted_test_evidence": "UNPROVEN",
                        "oracle_alignment": "CONTRADICTED",
                        "oracle_probe": "product parser rejects the fixture",
                    }
                ],
            }
        ),
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

    assert result.exit_code != 0
    assert "requires oracle_source_url" in result.output
    assert not md_out.exists()
    assert not json_out.exists()


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
    assert "**BEHAVIOR**" in markdown
    assert "**UNVERIFIED**" in markdown
    assert "**WITNESSED (submitted judge)**" in markdown
    assert "expected false to be true" in markdown
    assert "discussion_r1" in markdown
    assert "actions/runs/9" in markdown
    assert "sha256:abc123" in markdown
    assert payload["runner_url"] == "https://github.com/example/proof/actions/runs/9"
    assert payload["evidence_digest"] == "sha256:abc123"
    assert payload["claims"][0]["scope_sufficient"] is True
    assert payload["claims"][0]["overall_claim"] == "WITNESSED (submitted judge)"


def test_render_calls_out_insufficient_scope():
    manifest = ClaimMatrixManifest(
        title="Bluefin historical lab check",
        claims=[
            ClaimEvidence(
                id="safe-login-path",
                claim="keyring startup remains safe during login",
                tests=["lab/systemd-ordering.sh"],
                base_result="ABSENT",
                head_result="PASS",
                submitted_test_evidence=SubmittedTestEvidence.WITNESSED,
                evidence_scope=EvidenceScope.IMPLEMENTATION,
                required_scope=EvidenceScope.SAFETY,
            )
        ],
    )

    markdown = render_claim_matrix_markdown(manifest)
    payload = claim_matrix_to_dict(manifest)

    assert "**IMPLEMENTATION**" in markdown
    assert "**SAFETY**" in markdown
    assert "**WITNESSED (scope insufficient)**" in markdown
    assert "INSUFFICIENT" in markdown
    assert payload["claims"][0]["scope_sufficient"] is False


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
    evidence_scope: IMPLEMENTATION
    required_scope: BEHAVIOR
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
    assert payload["claims"][0]["evidence_scope"] == "IMPLEMENTATION"
    assert payload["claims"][0]["required_scope"] == "BEHAVIOR"
    assert payload["claims"][0]["scope_sufficient"] is False
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


def test_bluefin_example_preserves_green_but_wrong_oracle_boundary():
    from skill_factory.evolution.claim_matrix import load_claim_matrix

    manifest = load_claim_matrix(Path("examples/claim_matrix/bluefin-4539.yml"))
    payload = claim_matrix_to_dict(manifest)

    assert [item["overall_claim"] for item in payload["claims"]] == [
        "WITNESSED (scope insufficient)",
        "WITNESSED (scope insufficient)",
        "WITNESSED (oracle precondition missing)",
    ]
    assert [item["required_scope"] for item in payload["claims"]] == [
        "BEHAVIOR",
        "SAFETY",
        "BEHAVIOR",
    ]
    assert payload["claims"][2]["oracle_applicability"] == "PRECONDITION_MISSING"
    assert payload["claims"][1]["receipt_observed_verdict"] == "WITNESSED_CONTROLLED_CAUSAL"
    assert payload["claims"][1]["receipt_case"] == "ublue-os/bluefin#4539"


def test_missing_oracle_precondition_cannot_contradict_claim():
    claim = ClaimEvidence(
        id="bluefin-login-keyring",
        claim="login keyring is unlocked after automatic login",
        tests=["tests/common/features/bluefin_keyring.feature"],
        base_result="PASS",
        head_result="FAIL",
        submitted_test_evidence=SubmittedTestEvidence.WITNESSED,
        evidence_scope=EvidenceScope.BEHAVIOR,
        required_scope=EvidenceScope.BEHAVIOR,
        oracle_applicability=OracleApplicability.PRECONDITION_MISSING,
        oracle_precondition="synthetic CI user must have a Secret Service login alias",
        oracle_alignment=OracleAlignment.UNVERIFIED,
    )

    assert (
        claim.overall_claim
        is OverallClaim.WITNESSED_ORACLE_PRECONDITION_MISSING
    )


def test_missing_oracle_precondition_requires_description():
    with pytest.raises(ValidationError, match="requires an explicit oracle_precondition"):
        ClaimEvidence(
            id="missing-fixture",
            claim="behavior",
            tests=["tests/test_behavior.py"],
            base_result="FAIL",
            head_result="PASS",
            submitted_test_evidence=SubmittedTestEvidence.WITNESSED,
            oracle_applicability=OracleApplicability.PRECONDITION_MISSING,
            oracle_alignment=OracleAlignment.UNVERIFIED,
        )


def test_missing_oracle_precondition_cannot_be_marked_contradicted():
    with pytest.raises(
        ValidationError,
        match="requires oracle_alignment=UNVERIFIED",
    ):
        ClaimEvidence(
            id="invalid-interpretation",
            claim="behavior",
            tests=["tests/test_behavior.py"],
            base_result="FAIL",
            head_result="PASS",
            submitted_test_evidence=SubmittedTestEvidence.WITNESSED,
            oracle_applicability=OracleApplicability.PRECONDITION_MISSING,
            oracle_precondition="login alias must exist",
            oracle_alignment=OracleAlignment.CONTRADICTED,
            oracle_probe="read login collection Locked property",
            oracle_source_url=TEST_ORACLE_SOURCE,
        )


def test_render_exposes_oracle_applicability_boundary():
    manifest = ClaimMatrixManifest(
        title="Bluefin oracle applicability",
        claims=[
            ClaimEvidence(
                id="login-keyring",
                claim="login collection is unlocked after automatic login",
                tests=["bluefin_keyring.feature"],
                base_result="PASS",
                head_result="FAIL",
                submitted_test_evidence=SubmittedTestEvidence.WITNESSED,
                oracle_applicability=OracleApplicability.PRECONDITION_MISSING,
                oracle_precondition="synthetic CI user has a login collection alias",
                oracle_alignment=OracleAlignment.UNVERIFIED,
            )
        ],
    )

    markdown = render_claim_matrix_markdown(manifest)
    payload = claim_matrix_to_dict(manifest)

    assert "**PRECONDITION_MISSING**" in markdown
    assert "synthetic CI user has a login collection alias" in markdown
    assert (
        payload["claims"][0]["overall_claim"]
        == "WITNESSED (oracle precondition missing)"
    )


def test_claim_matrix_binds_machine_receipt(tmp_path: Path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "case": "ublue-os/bluefin#4539",
                "verdict": "WITNESSED_CONTROLLED_CAUSAL",
            }
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "claims.yml"
    manifest_path.write_text(
        """
schema_version: 1
title: Receipt binding
claims:
  - id: causal-witness
    claim: intervention changes activation path
    tests:
      - reality replay
    base_result: CONTROL
    head_result: BAD
    submitted_test_evidence: WITNESSED
    oracle_alignment: UNVERIFIED
    receipt_file: receipt.json
    receipt_expected_verdicts:
      - WITNESSED_CONTROLLED_CAUSAL
""".strip()
        + "\n",
        encoding="utf-8",
    )

    from skill_factory.evolution.claim_matrix import load_claim_matrix

    manifest = load_claim_matrix(manifest_path)
    payload = claim_matrix_to_dict(manifest)
    markdown = render_claim_matrix_markdown(manifest)

    assert payload["claims"][0]["receipt_observed_verdict"] == "WITNESSED_CONTROLLED_CAUSAL"
    assert payload["claims"][0]["receipt_case"] == "ublue-os/bluefin#4539"
    assert "Receipt verdict: `WITNESSED_CONTROLLED_CAUSAL`" in markdown


def test_claim_matrix_rejects_receipt_verdict_mismatch(tmp_path: Path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps({"verdict": "INCONCLUSIVE_CONTROLLED_CAUSAL"}),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "claims.yml"
    manifest_path.write_text(
        """
schema_version: 1
title: Receipt mismatch
claims:
  - id: causal-witness
    claim: intervention changes activation path
    tests:
      - reality replay
    base_result: CONTROL
    head_result: BAD
    submitted_test_evidence: WITNESSED
    oracle_alignment: UNVERIFIED
    receipt_file: receipt.json
    receipt_expected_verdicts:
      - WITNESSED_CONTROLLED_CAUSAL
""".strip()
        + "\n",
        encoding="utf-8",
    )

    from skill_factory.evolution.claim_matrix import load_claim_matrix

    with pytest.raises(ValueError, match="does not match expected verdict"):
        load_claim_matrix(manifest_path)


def test_claim_matrix_rejects_receipt_without_verdict(tmp_path: Path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({"case": "example"}), encoding="utf-8")
    manifest_path = tmp_path / "claims.yml"
    manifest_path.write_text(
        """
schema_version: 1
title: Missing verdict
claims:
  - id: receipt
    claim: evidence
    submitted_test_evidence: UNPROVEN
    receipt_file: receipt.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    from skill_factory.evolution.claim_matrix import load_claim_matrix

    with pytest.raises(ValueError, match="non-empty string verdict"):
        load_claim_matrix(manifest_path)


def test_claim_matrix_rejects_receipt_path_escape(tmp_path: Path):
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"verdict": "WITNESSED"}), encoding="utf-8")
    matrix_dir = tmp_path / "matrix"
    matrix_dir.mkdir()
    manifest_path = matrix_dir / "claims.yml"
    manifest_path.write_text(
        """
schema_version: 1
title: Receipt path escape
claims:
  - id: escaped
    claim: evidence
    submitted_test_evidence: UNPROVEN
    receipt_file: ../outside.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    from skill_factory.evolution.claim_matrix import load_claim_matrix

    with pytest.raises(ValueError, match="must stay within the claim-matrix directory"):
        load_claim_matrix(manifest_path)


def test_clash_example_binds_behavior_receipt_without_live_base_drift():
    from skill_factory.evolution.claim_matrix import load_claim_matrix

    manifest = load_claim_matrix(Path("examples/claim_matrix/clash-8017.yml"))
    payload = claim_matrix_to_dict(manifest)

    assert manifest.base_sha == "b057bd964ccd156f68bc43a3a8ed66cf3cb1cd7b"
    assert manifest.head_sha == "2cb071998e2f14d76a5fbc3f4add5973e79cf138"
    assert payload["claims"][0]["receipt_observed_verdict"] == "WITNESSED_BEHAVIOR"
    assert (
        payload["claims"][0]["receipt_case"]
        == "clash-verge-rev/clash-verge-rev#8017"
    )
    assert payload["claims"][0]["evidence_scope"] == "BEHAVIOR"
    assert payload["claims"][0]["oracle_applicability"] == "APPLICABLE"
    assert payload["claims"][0]["oracle_alignment"] == "ALIGNED"
    assert payload["claims"][0]["overall_claim"] == "PROVEN"


def test_scancode_example_binds_db_backed_behavior_receipt():
    from skill_factory.evolution.claim_matrix import load_claim_matrix

    manifest = load_claim_matrix(Path("examples/claim_matrix/scancode-2207.yml"))
    payload = claim_matrix_to_dict(manifest)

    assert manifest.base_sha == "41868632dcaba1ad9b6402d114b169564c08d121"
    assert manifest.head_sha == "f71185995aee043e2e9acfd31028501f23992aea"
    assert (
        payload["claims"][0]["receipt_observed_verdict"]
        == "WITNESSED_BEHAVIOR_DELTA"
    )
    assert (
        payload["claims"][0]["receipt_case"]
        == "aboutcode-org/scancode.io#2207"
    )
    assert payload["claims"][0]["evidence_scope"] == "BEHAVIOR"
    assert payload["claims"][0]["oracle_applicability"] == "APPLICABLE"
    assert payload["claims"][0]["oracle_alignment"] == "ALIGNED"
    assert payload["claims"][0]["overall_claim"] == "PROVEN"


def test_claude_oracle_disagreement_binds_external_oracle_receipt():
    from skill_factory.evolution.claim_matrix import load_claim_matrix

    manifest = load_claim_matrix(Path("examples/claim_matrix/claude-code-89404.yml"))
    payload = claim_matrix_to_dict(manifest)

    first = payload["claims"][0]
    assert first["overall_claim"] == "CONTRADICTED"
    assert first["oracle_alignment"] == "CONTRADICTED"
    assert first["receipt_observed_verdict"] == "ORACLE_CONTRADICTED_BY_PRODUCT"
    assert first["receipt_case"] == "anthropics/claude-code#89404"

    receipt_path = Path(
        "examples/claim_matrix/receipts/claude-code-89404-oracle.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["evidence_kind"] == "REVIEWER_SUPPLIED_EXTERNAL_ORACLE"
    assert receipt["candidate"]["head_sha"] == (
        "0989f29b0bca412edc58018c462cae7344bb1a2f"
    )
    assert receipt["authoritative_oracle"]["command"] == (
        "claude plugin validate --json"
    )
    assert receipt["authoritative_oracle"]["result"] == "REJECT"
    assert receipt["does_not_claim"]


def test_gramps_executed_triad_receipt_is_bound_without_revert_semantic_drift():
    from skill_factory.evolution.claim_matrix import load_claim_matrix

    manifest = load_claim_matrix(Path("examples/claim_matrix/gramps-2484.yml"))
    payload = claim_matrix_to_dict(manifest)

    assert manifest.base_sha == "48e067ced96ad83b7498587ea1562c2d327b41aa"
    assert manifest.head_sha == "faee7435ebb7ddcc5522b83028eddae5a5ef39e3"
    claim = payload["claims"][0]
    assert claim["overall_claim"] == "PROVEN"
    assert claim["receipt_observed_verdict"] == "WITNESSED_CHALLENGE_REPAIR"
    assert claim["receipt_case"] == "gramps-project/gramps#2484"

    receipt = json.loads(
        Path("examples/claim_matrix/receipts/gramps-2484-triad.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["receipt_type"] == "EXECUTED_CHALLENGE_REPAIR_TRIAD"
    assert receipt["states"]["CONTROL"]["result"] == "PASS"
    assert receipt["states"]["CHALLENGE"]["result"] == "FAIL"
    assert receipt["states"]["REPAIR"]["result"] == "PASS"
    assert "REVERT" in receipt["does_not_claim"][0]
