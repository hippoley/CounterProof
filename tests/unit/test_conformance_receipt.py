import hashlib
import json
from pathlib import Path

import pytest

from skill_factory.evolution.conformance_receipt import (
    build_conformance_receipt,
    validate_external_harness_report,
    verify_conformance_receipt,
)

FIXTURE = Path("examples/interop/in-toto-597")


def test_in_toto_597_manifest_builds_pinned_conformance_receipt(tmp_path: Path):
    receipt = build_conformance_receipt(
        FIXTURE / "manifest.json",
        FIXTURE / "observations.json",
    )

    assert receipt["receipt_type"] == "EXTERNAL_CONFORMANCE_CAMPAIGN"
    assert receipt["predicate_type"].endswith("/adversarial-execution-evidence/v0.7")
    assert receipt["vector_count"] == 4
    assert receipt["divergence_count"] == 0
    assert receipt["verdict"] == "CONFORMING"
    assert receipt["comparison_surface"]["normative"] == ["verdict", "result"]
    assert receipt["comparison_surface"]["measured"] == ["codes"]

    failures = verify_conformance_receipt(
        receipt,
        manifest_path=FIXTURE / "manifest.json",
        observations_path=FIXTURE / "observations.json",
    )
    assert failures == ()


def test_conformance_receipt_marks_changed_corpus_stale(tmp_path: Path):
    receipt = build_conformance_receipt(
        FIXTURE / "manifest.json",
        FIXTURE / "observations.json",
    )
    changed = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
    changed["vectors"][0]["conditions"].append("future-condition")
    changed_path = tmp_path / "manifest-v2.json"
    changed_path.write_text(json.dumps(changed, indent=2) + "\n", encoding="utf-8")

    failures = verify_conformance_receipt(receipt, manifest_path=changed_path)

    assert len(failures) == 1
    assert failures[0].startswith("manifest lifecycle STALE:")


def test_conformance_receipt_rejects_cross_corpus_vector_substitution(tmp_path: Path):
    observed = json.loads((FIXTURE / "observations.json").read_text(encoding="utf-8"))
    observed["results"][0]["id"] = "some-other-corpus-vector"
    observed_path = tmp_path / "observations.json"
    observed_path.write_text(json.dumps(observed, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing observed result for vector"):
        build_conformance_receipt(FIXTURE / "manifest.json", observed_path)


def test_measured_codes_do_not_override_normative_conformance(tmp_path: Path):
    observed = json.loads((FIXTURE / "observations.json").read_text(encoding="utf-8"))
    reject = next(item for item in observed["results"] if item["verdict"] == "invalid")
    reject["codes"] = ["different-local-reason"]
    observed_path = tmp_path / "observations.json"
    observed_path.write_text(json.dumps(observed, indent=2) + "\n", encoding="utf-8")

    receipt = build_conformance_receipt(FIXTURE / "manifest.json", observed_path)

    assert receipt["verdict"] == "CONFORMING"
    row = next(item for item in receipt["vectors"] if item["id"] == reject["id"])
    assert row["measured_expected"] != row["measured_observed"]


def test_normative_divergence_is_not_hidden_by_matching_measured_code(tmp_path: Path):
    observed = json.loads((FIXTURE / "observations.json").read_text(encoding="utf-8"))
    observed["results"][0]["verdict"] = "invalid"
    observed_path = tmp_path / "observations.json"
    observed_path.write_text(json.dumps(observed, indent=2) + "\n", encoding="utf-8")

    receipt = build_conformance_receipt(FIXTURE / "manifest.json", observed_path)

    assert receipt["verdict"] == "DIVERGED"
    assert receipt["divergence_count"] == 1
    assert receipt["vectors"][0]["normative_mismatches"] == ["verdict"]


def test_independent_checker_preserves_normative_and_reason_parity_split():
    receipt = build_conformance_receipt(
        FIXTURE / "manifest.json",
        FIXTURE / "observations-rul1an-rev27.json",
    )

    assert receipt["verdict"] == "CONFORMING"
    assert receipt["divergence_count"] == 0
    assert receipt["vector_count"] == 4
    assert receipt["verifier"]["name"] == "Rul1an/aee-checker"
    assert "suite_revision" not in receipt["verifier"]
    assert receipt["verifier"]["checker_sequence_revision"] == 27
    assert receipt["verifier"]["corpus_suite_revision"] == 28
    assert receipt["verifier"]["vector_git_blobs"] == {
        "v48542b44ffd26237": "fe8b67cf6259446d04147753e0dcdbaee343a2eb",
        "v18bdbadef67b38f4": "862db2af4b99b4638a39fb05f4b21c6fbb3f03ce",
        "v2adb319fc7515885": "bf8106a749fb47b9e102f089c7625506e6905fa2",
        "v3418101227718535": "7d476005fd32af6172578970fe7dd3c9c3c23b2f",
    }
    assert receipt["verifier"]["checker_source_digest"] == (
        "sha256:5fbe879e9d6a7355d5af8c4ea6f7c055f9289753c69b9336b5ce0a213371b596"
    )

    rejects = [item for item in receipt["vectors"] if item["kind"] == "reject"]
    assert len(rejects) == 2
    assert all(item["normative_mismatches"] == [] for item in rejects)
    assert sum(
        item["measured_expected"] == item["measured_observed"]
        for item in rejects
    ) == 0


def test_independent_checker_observation_provenance_is_receipt_bound(tmp_path: Path):
    receipt = build_conformance_receipt(
        FIXTURE / "manifest.json",
        FIXTURE / "observations-rul1an-rev27.json",
    )

    changed = json.loads(
        (FIXTURE / "observations-rul1an-rev27.json").read_text(encoding="utf-8")
    )
    changed["verifier"]["checker_source_digest"] = "sha256:" + ("0" * 64)
    changed_path = tmp_path / "substituted-observations.json"
    changed_path.write_text(json.dumps(changed, indent=2) + "\n", encoding="utf-8")

    failures = verify_conformance_receipt(
        receipt,
        manifest_path=FIXTURE / "manifest.json",
        observations_path=changed_path,
    )

    assert len(failures) == 1
    assert failures[0].startswith("observations identity mismatch:")

def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload).hexdigest()


def test_frozen_in_toto_statements_match_pinned_git_blob_identities():
    observations = json.loads(
        (FIXTURE / "observations-rul1an-rev27.json").read_text(encoding="utf-8")
    )
    expected_blobs = observations["verifier"]["vector_git_blobs"]
    manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))

    manifest_ids = {item["id"]: item["file"] for item in manifest["vectors"]}
    assert set(manifest_ids) == set(expected_blobs)

    for vector_id, expected_blob in expected_blobs.items():
        statement_path = FIXTURE / manifest_ids[vector_id]
        assert statement_path.is_file(), vector_id
        assert _git_blob_sha(statement_path) == expected_blob

def _external_harness_report(
    *,
    vectors: int = 4,
    executed: int = 4,
    conform: int = 4,
    fail: int = 0,
) -> dict:
    return {
        "rail": "external",
        "railNote": "synthetic external verifier",
        "verifier": {
            "command": "./independent-verifier --json",
            "vectorsExecuted": executed,
        },
        "totals": {
            "vectors": vectors,
            "conform": conform,
            "fail": fail,
            "suiteRefusals": 0,
        },
        "vectors": [
            {"id": f"v{i}", "verifierRan": i < executed}
            for i in range(vectors)
        ],
    }


def test_external_harness_gate_accepts_complete_execution_even_when_verifier_fails():
    report = _external_harness_report(conform=1, fail=3)

    failures = validate_external_harness_report(report)

    assert failures == ()


def test_external_harness_gate_rejects_reference_rail_substitution():
    report = _external_harness_report()
    report["rail"] = "reference"
    report["verifier"] = None

    failures = validate_external_harness_report(report)

    assert "external verifier execution not proven" in failures[0]
    assert "report verifier identity is missing" in failures


def test_external_harness_gate_rejects_short_execution():
    report = _external_harness_report(executed=3)

    failures = validate_external_harness_report(report)

    assert "external verifier ran on 3 of 4 vectors" in failures
    assert any("verifier did not run: v3" in item for item in failures)


def test_external_harness_gate_rejects_suite_refusal_without_relabeling_verifier():
    report = _external_harness_report()
    report["totals"]["suiteRefusals"] = 1

    failures = validate_external_harness_report(report)

    assert failures == ("corpus harness reported 1 suite refusal(s)",)

