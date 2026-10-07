import json
from pathlib import Path

import pytest

from skill_factory.evolution.conformance_receipt import (
    build_conformance_receipt,
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
