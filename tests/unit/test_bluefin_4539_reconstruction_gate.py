from pathlib import Path

from scripts.reality_bluefin_4539_reconstruction_gate import build_receipt, exit_code_for_verdict


def _write_source(root: Path, *, with_dropin: bool) -> None:
    (root / "image-versions.yml").write_text(
        """images:
  - name: silverblue-main
    digest: sha256:2ade0f897499dd488a4f59c4bbe50002228e3b683938333ce119be4e748fe1f5
  - name: common
    digest: sha256:1e7f8c88b8efb67b3fc42ef29bf0d927e9b8366c26dcf71893169979b29a4418
  - name: brew
    digest: sha256:2369e2dc70dd8b12828604d22721d1812cd87611661d789e1a0ee2cb123cbe7e
""",
        encoding="utf-8",
    )
    if with_dropin:
        path = root / (
            "system_files/shared/usr/lib/systemd/user/"
            "xdg-desktop-portal.service.d/30-after-keyring.conf"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[Unit]\nAfter=gnome-keyring-daemon.service\n", encoding="utf-8")


def test_bad_reconstruction_is_blocked_only_by_missing_historical_base(tmp_path: Path):
    _write_source(tmp_path, with_dropin=True)

    receipt = build_receipt(
        tmp_path,
        candidate="BAD",
        source_commit="60e72be24878ce01b4849cfb4b8efc18932a133e",
        availability={
            "silverblue-main": "UNAVAILABLE",
            "common": "AVAILABLE",
            "brew": "AVAILABLE",
        },
    )

    assert receipt["source_contract"]["dependencies_match"] is True
    assert receipt["source_contract"]["intervention_match"] is True
    assert receipt["missing_dependencies"] == ["silverblue-main"]
    assert receipt["verdict"] == "BLOCKED_MISSING_HISTORICAL_BASE"
    assert receipt["reconstruction_level"] == "PROVENANCE_ONLY"
    assert receipt["recovery_ladder"]["executable_rebuild"] is False


def test_revert_reconstruction_has_same_dependency_contract_without_dropin(tmp_path: Path):
    _write_source(tmp_path, with_dropin=False)

    receipt = build_receipt(
        tmp_path,
        candidate="REVERT",
        source_commit="bd12c2e29f6ecb2cabd5bfb53bc00281a7d9118f",
        availability={
            "silverblue-main": "UNAVAILABLE",
            "common": "AVAILABLE",
            "brew": "AVAILABLE",
        },
    )

    assert receipt["source_contract"]["dependencies_match"] is True
    assert receipt["source_contract"]["intervention_match"] is True
    assert receipt["verdict"] == "BLOCKED_MISSING_HISTORICAL_BASE"


def test_reconstruction_refuses_wrong_intervention_state(tmp_path: Path):
    _write_source(tmp_path, with_dropin=False)

    receipt = build_receipt(
        tmp_path,
        candidate="BAD",
        source_commit="60e72be24878ce01b4849cfb4b8efc18932a133e",
        availability={
            "silverblue-main": "AVAILABLE",
            "common": "AVAILABLE",
            "brew": "AVAILABLE",
        },
    )

    assert receipt["verdict"] == "INVALID_RECONSTRUCTION_SOURCE_CONTRACT"


def test_source_equivalent_base_can_unblock_historical_reconstruction(tmp_path: Path):
    _write_source(tmp_path, with_dropin=True)

    receipt = build_receipt(
        tmp_path,
        candidate="BAD",
        source_commit="60e72be24878ce01b4849cfb4b8efc18932a133e",
        availability={
            "silverblue-main": "UNAVAILABLE",
            "common": "AVAILABLE",
            "brew": "AVAILABLE",
        },
        base_rebuild_inputs={
            "fedora-silverblue-44": "AVAILABLE",
            "akmods-44": "AVAILABLE",
            "akmods-nvidia-open-44": "AVAILABLE",
        },
    )

    assert receipt["base_rebuild"]["ready"] is True
    assert (
        receipt["verdict"]
        == "READY_FOR_SOURCE_EQUIVALENT_BASE_REBUILD"
    )
    assert receipt["reconstruction_level"] == "SOURCE_EQUIVALENT_BASE_READY"
    assert receipt["recovery_ladder"]["executable_rebuild"] is True
    assert receipt["base_rebuild"]["claim_boundary"].startswith(
        "source-equivalent rebuild only"
    )


def test_reconstruction_refuses_wrong_source_commit(tmp_path: Path):
    _write_source(tmp_path, with_dropin=True)

    receipt = build_receipt(
        tmp_path,
        candidate="BAD",
        source_commit="deadbeef",
        availability={
            "silverblue-main": "AVAILABLE",
            "common": "AVAILABLE",
            "brew": "AVAILABLE",
        },
    )

    assert receipt["source_identity"]["source_commit_match"] is False
    assert receipt["verdict"] == "INVALID_RECONSTRUCTION_SOURCE_IDENTITY"


def test_original_historical_base_is_highest_recovery_level(tmp_path: Path):
    _write_source(tmp_path, with_dropin=True)

    receipt = build_receipt(
        tmp_path,
        candidate="BAD",
        source_commit="60e72be24878ce01b4849cfb4b8efc18932a133e",
        availability={
            "silverblue-main": "AVAILABLE",
            "common": "AVAILABLE",
            "brew": "AVAILABLE",
        },
    )

    assert receipt["verdict"] == "READY_FOR_SOURCE_PINNED_REBUILD"
    assert receipt["reconstruction_level"] == "ORIGINAL_HISTORICAL_BASE_AVAILABLE"
    assert receipt["recovery_ladder"]["original_historical_base"] is True


def test_dependency_probe_failure_is_inconclusive(tmp_path: Path):
    _write_source(tmp_path, with_dropin=True)

    receipt = build_receipt(
        tmp_path,
        candidate="BAD",
        source_commit="60e72be24878ce01b4849cfb4b8efc18932a133e",
        availability={
            "silverblue-main": "PROBE_FAILED",
            "common": "AVAILABLE",
            "brew": "AVAILABLE",
        },
    )

    assert receipt["missing_dependencies"] == []
    assert receipt["unresolved_dependencies"] == ["silverblue-main"]
    assert receipt["verdict"] == "INCONCLUSIVE_DEPENDENCY_AVAILABILITY"


def test_source_equivalent_input_probe_failure_is_inconclusive(tmp_path: Path):
    _write_source(tmp_path, with_dropin=True)

    receipt = build_receipt(
        tmp_path,
        candidate="BAD",
        source_commit="60e72be24878ce01b4849cfb4b8efc18932a133e",
        availability={
            "silverblue-main": "UNAVAILABLE",
            "common": "AVAILABLE",
            "brew": "AVAILABLE",
        },
        base_rebuild_inputs={
            "fedora-silverblue-44": "PROBE_FAILED",
            "akmods-44": "AVAILABLE",
            "akmods-nvidia-open-44": "AVAILABLE",
        },
    )

    assert receipt["base_rebuild"]["missing_inputs"] == []
    assert receipt["base_rebuild"]["unresolved_inputs"] == ["fedora-silverblue-44"]
    assert receipt["base_rebuild"]["ready"] is False
    assert receipt["verdict"] == "INCONCLUSIVE_DEPENDENCY_AVAILABILITY"


def test_reconstruction_exit_codes_preserve_inconclusive_state():
    assert exit_code_for_verdict("READY_FOR_SOURCE_PINNED_REBUILD") == 0
    assert exit_code_for_verdict("BLOCKED_MISSING_HISTORICAL_BASE") == 0
    assert exit_code_for_verdict("INVALID_RECONSTRUCTION_SOURCE_IDENTITY") == 1
    assert exit_code_for_verdict("INVALID_RECONSTRUCTION_SOURCE_CONTRACT") == 1
    assert exit_code_for_verdict("INCONCLUSIVE_DEPENDENCY_AVAILABILITY") == 2
