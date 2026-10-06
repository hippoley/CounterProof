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
