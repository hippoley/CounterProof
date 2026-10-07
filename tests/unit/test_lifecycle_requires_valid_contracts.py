from pathlib import Path

import pytest

from skill_factory.evolution.effective_lifecycle import (
    EffectiveLifecycleObservation,
    resolve_effective_contract_lifecycles,
)
from skill_factory.evolution.evidence_lifecycle import EvidenceLifecycle
from skill_factory.evolution.lifecycle_receipt import (
    build_lifecycle_receipt,
    verify_lifecycle_receipt,
)


def _write_invalid_contract_suite(tmp_path: Path) -> Path:
    (tmp_path / "claims.yml").write_text(
        """
schema_version: 1
title: Invalid reality contract
claims:
  - id: behavior
    claim: behavior
    submitted_test_evidence: UNPROVEN
""".strip()
        + "\n",
        encoding="utf-8",
    )
    suite = tmp_path / "contracts.yml"
    suite.write_text(
        """
schema_version: 1
contracts:
  - id: invalid-contract
    lifecycle: CURRENT
    manifest: claims.yml
    expectations:
      - claim_id: behavior
        overall_claim: PROVEN
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return suite


def test_effective_lifecycle_refuses_invalid_reality_contracts(tmp_path: Path):
    suite = _write_invalid_contract_suite(tmp_path)

    with pytest.raises(
        ValueError,
        match="Reality Contract validation failed before lifecycle resolution",
    ):
        resolve_effective_contract_lifecycles(
            suite,
            freshness_observations=[],
        )


def test_lifecycle_receipt_verifier_rejects_matching_but_invalid_suite(
    tmp_path: Path,
):
    suite = _write_invalid_contract_suite(tmp_path)
    observation = EffectiveLifecycleObservation(
        contract_id="invalid-contract",
        evidence_id=None,
        declared=EvidenceLifecycle.CURRENT,
        freshness_signal=None,
        graph_signal=None,
        effective=EvidenceLifecycle.CURRENT,
    )
    receipt = build_lifecycle_receipt(
        [observation],
        suite_file=suite,
        environment={},
    )

    failures = verify_lifecycle_receipt(
        receipt,
        suite_file=suite,
    )

    assert not any("suite git blob sha" in failure for failure in failures)
    assert any(
        "Reality Contract invalid: invalid-contract" in failure
        for failure in failures
    )
