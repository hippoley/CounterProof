from pathlib import Path

from click.testing import CliRunner

from skill_factory.evolution.cli import cli
from skill_factory.evolution.reality_contracts import validate_reality_contracts

SUITE = Path("examples/claim_matrix/reality-contracts.yml")


def test_real_reality_contract_suite_passes():
    failures = validate_reality_contracts(SUITE)

    assert failures == []


def test_reality_contract_cli_passes():
    result = CliRunner().invoke(cli, ["reality-contracts", str(SUITE)])

    assert result.exit_code == 0, result.output
    assert "Reality contracts: 3 passed" in result.output


def test_reality_contract_reports_semantic_regression(tmp_path: Path):
    suite = tmp_path / "contracts.yml"
    suite.write_text(
        """
schema_version: 1
contracts:
  - id: broken
    manifest: claims.yml
    expected_base_sha: expected-base
    expectations:
      - claim_id: behavior
        overall_claim: PROVEN
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "claims.yml").write_text(
        """
schema_version: 1
title: Broken contract
base_sha: observed-base
claims:
  - id: behavior
    claim: behavior
    submitted_test_evidence: UNPROVEN
""".strip()
        + "\n",
        encoding="utf-8",
    )

    failures = validate_reality_contracts(suite)

    assert len(failures) == 2
    assert failures[0].contract_id == "broken"
    assert "base_sha" in failures[0].message
    assert "overall_claim" in failures[1].message


def test_reality_contract_rejects_receipt_identity_drift(tmp_path: Path):
    matrix_dir = tmp_path / "matrix"
    receipts_dir = matrix_dir / "receipts"
    receipts_dir.mkdir(parents=True)

    (receipts_dir / "receipt.json").write_text(
        """
{
  "schema_version": 1,
  "case": "example/repo#1",
  "verdict": "WITNESSED_BEHAVIOR",
  "source_run": {
    "workflow_run": 999
  },
  "candidates": {
    "BASE": {
      "commit": "different-base"
    }
  }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (matrix_dir / "claims.yml").write_text(
        """
schema_version: 1
title: Receipt identity drift
claims:
  - id: behavior
    claim: behavior
    tests:
      - behavior probe
    base_result: FAIL
    head_result: PASS
    submitted_test_evidence: WITNESSED
    evidence_scope: BEHAVIOR
    required_scope: BEHAVIOR
    oracle_applicability: APPLICABLE
    oracle_alignment: ALIGNED
    oracle_probe: behavior oracle
    receipt_file: receipts/receipt.json
    receipt_expected_verdicts:
      - WITNESSED_BEHAVIOR
""".strip()
        + "\n",
        encoding="utf-8",
    )
    suite = matrix_dir / "contracts.yml"
    suite.write_text(
        """
schema_version: 1
contracts:
  - id: frozen-evidence
    manifest: claims.yml
    expectations:
      - claim_id: behavior
        receipt_verdict: WITNESSED_BEHAVIOR
        receipt_expectations:
          source_run.workflow_run: 123
          candidates.BASE.commit: expected-base
""".strip()
        + "\n",
        encoding="utf-8",
    )

    failures = validate_reality_contracts(suite)

    assert len(failures) == 2
    assert "source_run.workflow_run" in failures[0].message
    assert "candidates.BASE.commit" in failures[1].message


def test_reality_contract_rejects_receipt_blob_drift(tmp_path: Path):
    matrix_dir = tmp_path / "matrix"
    receipts_dir = matrix_dir / "receipts"
    receipts_dir.mkdir(parents=True)

    (receipts_dir / "receipt.json").write_text(
        """
{
  "schema_version": 1,
  "case": "example/repo#1",
  "verdict": "WITNESSED_BEHAVIOR",
  "note": "content changed while verdict stayed the same"
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (matrix_dir / "claims.yml").write_text(
        """
schema_version: 1
title: Receipt blob drift
claims:
  - id: behavior
    claim: behavior
    tests:
      - behavior probe
    base_result: FAIL
    head_result: PASS
    submitted_test_evidence: WITNESSED
    evidence_scope: BEHAVIOR
    required_scope: BEHAVIOR
    oracle_applicability: APPLICABLE
    oracle_alignment: ALIGNED
    oracle_probe: behavior oracle
    receipt_file: receipts/receipt.json
    receipt_expected_verdicts:
      - WITNESSED_BEHAVIOR
""".strip()
        + "\n",
        encoding="utf-8",
    )
    suite = matrix_dir / "contracts.yml"
    suite.write_text(
        """
schema_version: 1
contracts:
  - id: frozen-blob
    manifest: claims.yml
    expectations:
      - claim_id: behavior
        receipt_verdict: WITNESSED_BEHAVIOR
        receipt_git_blob_sha: 0000000000000000000000000000000000000000
""".strip()
        + "\n",
        encoding="utf-8",
    )

    failures = validate_reality_contracts(suite)

    assert len(failures) == 1
    assert "receipt git blob sha" in failures[0].message
