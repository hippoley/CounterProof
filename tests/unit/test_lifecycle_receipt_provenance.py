import copy
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
    assert receipt["execution"]["run_id"] == "123"
    assert receipt["execution"]["git_sha"] == "deadbeef"
    freshness = receipt["observations"][0]["freshness"]
    assert freshness["status"] == "DRIFTED"
    assert freshness["frozen_base_sha"] == "base-old"
    assert freshness["live_base_sha"] == "base-new"


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
