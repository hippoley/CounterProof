import json
from pathlib import Path

from scripts.reality_bluefin_4539_reconstruction_gate import build_receipt


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
        source_commit="60e72be",
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


def test_revert_reconstruction_has_same_dependency_contract_without_dropin(tmp_path: Path):
    _write_source(tmp_path, with_dropin=False)

    receipt = build_receipt(
        tmp_path,
        candidate="REVERT",
        source_commit="bd12c2e",
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
        source_commit="60e72be",
        availability={
            "silverblue-main": "AVAILABLE",
            "common": "AVAILABLE",
            "brew": "AVAILABLE",
        },
    )

    assert receipt["verdict"] == "INVALID_RECONSTRUCTION_SOURCE_CONTRACT"
