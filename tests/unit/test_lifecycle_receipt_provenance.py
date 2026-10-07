import copy
import json
from pathlib import Path

from skill_factory.evolution.effective_lifecycle import EffectiveLifecycleObservation
from skill_factory.evolution.evidence_lifecycle import EvidenceLifecycle
from skill_factory.evolution.lifecycle_receipt import (
    build_lifecycle_receipt,
    verify_lifecycle_receipt,
)


def _observation() -> EffectiveLifecycleObservation:
    return EffectiveLifecycleObservation(
        contract_id="example",
        evidence_id="evidence-1",
        declared=EvidenceLifecycle.CURRENT,
        freshness_signal=EvidenceLifecycle.STALE,
        graph_signal=EvidenceLifecycle.SUPERSEDED,
        effective=EvidenceLifecycle.SUPERSEDED,
        freshness_status="DRIFTED",
        source_pr="https://github.com/example/repo/pull/1",
        frozen_base_sha="base-old",
        frozen_head_sha="head",
        live_base_sha="base-new",
        live_head_sha="head",
        freshness_reason="live PR base candidate drift",
    )


def _write_recursive_suite(tmp_path: Path) -> tuple[Path, Path, Path]:
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "verdict": "WITNESSED_BEHAVIOR",
                "case": "example/repo#1",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "claims.yml"
    manifest.write_text(
        """
schema_version: 1
title: Recursive provenance fixture
source_pr: https://github.com/example/repo/pull/1
base_sha: base-sha
head_sha: head-sha
claims:
  - id: behavior
    claim: Behavior changed as expected
    tests:
      - test_example
    base_result: FAIL
    head_result: PASS
    submitted_test_evidence: WITNESSED
    evidence_scope: BEHAVIOR
    required_scope: BEHAVIOR
    oracle_alignment: UNVERIFIED
    receipt_file: receipt.json
    receipt_expected_verdicts:
      - WITNESSED_BEHAVIOR
""".strip()
        + "\n",
        encoding="utf-8",
    )
    suite = tmp_path / "suite.yml"
    suite.write_text(
        """
schema_version: 1
contracts:
  - id: recursive-example
    lifecycle: CURRENT
    manifest: claims.yml
    expectations:
      - claim_id: behavior
        overall_claim: "WITNESSED (submitted judge)"
        receipt_verdict: WITNESSED_BEHAVIOR
        receipt_case: example/repo#1
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return suite, manifest, receipt


def test_lifecycle_receipt_captures_input_and_execution_provenance(tmp_path: Path):
    suite = tmp_path / "suite.yml"
    suite.write_text("schema_version: 1\ncontracts: []\n", encoding="utf-8")
    graph = tmp_path / "graph.yml"
    graph.write_text("schema_version: 1\nevidence: []\n", encoding="utf-8")

    receipt = build_lifecycle_receipt(
        [_observation()],
        suite_file=suite,
        graph_file=graph,
        environment={
            "GITHUB_REPOSITORY": "hippoley/CounterProof",
            "GITHUB_WORKFLOW": "Reality — evidence freshness",
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "2",
            "GITHUB_SHA": "deadbeef",
            "GITHUB_REF": "refs/heads/main",
        },
    )

    assert receipt["schema_version"] == 2
    assert receipt["status"] == "UPDATE_REQUIRED"
    assert receipt["mismatch_count"] == 1
    assert receipt["inputs"]["suite_git_blob_sha"]
    assert receipt["inputs"]["graph_git_blob_sha"]
    assert receipt["provenance"] == {"schema_version": 1, "contracts": []}
    assert receipt["execution"]["run_id"] == "123"
    assert receipt["execution"]["git_sha"] == "deadbeef"
    freshness = receipt["observations"][0]["freshness"]
    assert freshness["status"] == "DRIFTED"
    assert freshness["frozen_base_sha"] == "base-old"
    assert freshness["live_base_sha"] == "base-new"


def test_lifecycle_receipt_exposes_recursive_claim_and_receipt_identities(
    tmp_path: Path,
):
    suite, _, _ = _write_recursive_suite(tmp_path)

    receipt = build_lifecycle_receipt(
        [],
        suite_file=suite,
        environment={},
    )

    closure = receipt["provenance"]
    assert closure["schema_version"] == 1
    assert len(closure["contracts"]) == 1
    contract = closure["contracts"][0]
    assert contract["contract_id"] == "recursive-example"
    assert contract["claim_matrix"]["file"] == "claims.yml"
    assert contract["claim_matrix"]["git_blob_sha"]
    assert contract["claim_matrix"]["base_sha"] == "base-sha"
    assert contract["claim_matrix"]["head_sha"] == "head-sha"
    assert contract["machine_receipts"] == [
        {
            "claim_id": "behavior",
            "file": "receipt.json",
            "git_blob_sha": contract["machine_receipts"][0]["git_blob_sha"],
            "verdict": "WITNESSED_BEHAVIOR",
            "case": "example/repo#1",
        }
    ]


def test_verify_lifecycle_receipt_accepts_matching_inputs(tmp_path: Path):
    suite = tmp_path / "suite.yml"
    suite.write_text("schema_version: 1\ncontracts: []\n", encoding="utf-8")
    graph = tmp_path / "graph.yml"
    graph.write_text("schema_version: 1\nevidence: []\n", encoding="utf-8")
    receipt = build_lifecycle_receipt(
        [_observation()],
        suite_file=suite,
        graph_file=graph,
        environment={},
    )

    assert verify_lifecycle_receipt(
        receipt,
        suite_file=suite,
        graph_file=graph,
    ) == []


def test_verify_lifecycle_receipt_rejects_suite_tamper(tmp_path: Path):
    suite = tmp_path / "suite.yml"
    suite.write_text("schema_version: 1\ncontracts: []\n", encoding="utf-8")
    receipt = build_lifecycle_receipt(
        [_observation()],
        suite_file=suite,
        environment={},
    )

    suite.write_text(
        "schema_version: 1\ncontracts:\n  - id: changed\n",
        encoding="utf-8",
    )

    failures = verify_lifecycle_receipt(receipt, suite_file=suite)

    assert any("suite git blob sha" in item for item in failures)


def test_verify_lifecycle_receipt_rejects_graph_tamper(tmp_path: Path):
    suite = tmp_path / "suite.yml"
    suite.write_text("schema_version: 1\ncontracts: []\n", encoding="utf-8")
    graph = tmp_path / "graph.yml"
    graph.write_text("schema_version: 1\nevidence: []\n", encoding="utf-8")
    receipt = build_lifecycle_receipt(
        [_observation()],
        suite_file=suite,
        graph_file=graph,
        environment={},
    )

    graph.write_text(
        "schema_version: 1\nevidence:\n  - id: changed\n",
        encoding="utf-8",
    )

    failures = verify_lifecycle_receipt(
        receipt,
        suite_file=suite,
        graph_file=graph,
    )

    assert any("graph git blob sha" in item for item in failures)


def test_verify_lifecycle_receipt_rejects_claim_matrix_tamper_inside_closure(
    tmp_path: Path,
):
    suite, manifest, _ = _write_recursive_suite(tmp_path)
    receipt = build_lifecycle_receipt([], suite_file=suite, environment={})

    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        .replace("claim: Behavior changed as expected", "claim: Behavior changed as expected\n    note: reviewer-only metadata changed"),
        encoding="utf-8",
    )

    failures = verify_lifecycle_receipt(receipt, suite_file=suite)

    assert not any("suite git blob sha" in item for item in failures)
    assert any(
        "claim matrix 'claims.yml' git_blob_sha expected" in item
        for item in failures
    )


def test_verify_lifecycle_receipt_rejects_machine_receipt_tamper_inside_closure(
    tmp_path: Path,
):
    suite, _, machine_receipt = _write_recursive_suite(tmp_path)
    receipt = build_lifecycle_receipt([], suite_file=suite, environment={})

    payload = json.loads(machine_receipt.read_text(encoding="utf-8"))
    payload["reviewer_note"] = "same verdict, different artifact"
    machine_receipt.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    failures = verify_lifecycle_receipt(receipt, suite_file=suite)

    assert not any("suite git blob sha" in item for item in failures)
    assert any(
        "machine receipt 'receipt.json'" in item and "git_blob_sha expected" in item
        for item in failures
    )


def test_verify_lifecycle_receipt_rejects_missing_recursive_provenance(
    tmp_path: Path,
):
    suite = tmp_path / "suite.yml"
    suite.write_text("schema_version: 1\ncontracts: []\n", encoding="utf-8")
    receipt = build_lifecycle_receipt([], suite_file=suite, environment={})
    receipt.pop("provenance")

    failures = verify_lifecycle_receipt(receipt, suite_file=suite)

    assert any("provenance manifest must be an object" in item for item in failures)


def test_verify_lifecycle_receipt_rejects_internal_status_tamper(tmp_path: Path):
    suite = tmp_path / "suite.yml"
    suite.write_text("schema_version: 1\ncontracts: []\n", encoding="utf-8")
    receipt = build_lifecycle_receipt(
        [_observation()],
        suite_file=suite,
        environment={},
    )
    tampered = copy.deepcopy(receipt)
    tampered["mismatch_count"] = 0
    tampered["status"] = "PASS"

    failures = verify_lifecycle_receipt(tampered, suite_file=suite)

    assert any("mismatch_count" in item for item in failures)
    assert any("status expected" in item for item in failures)
