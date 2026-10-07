import json
from pathlib import Path

import pytest

from scripts.reality_bluefin_4539_receipt import build_receipt, prepare_generic_replay
from skill_factory.evolution.causal_replay import build_causal_replay_receipt


def _write_diag(root: Path, image: str, *, active: bool, dep: bool, late: bool) -> None:
    snapshot = {
        "keyring_unit": {
            "stdout": (
                f"ActiveState={'active' if active else 'inactive'}\n"
                f"MainPID={2740 if active else 0}"
            )
        },
        "portal_dependencies": {
            "stdout": (
                "xdg-desktop-portal.service\n  gnome-keyring-daemon.service"
                if dep
                else "xdg-desktop-portal.service\n  dbus.socket"
            )
        },
        "keyring_journal": {
            "stdout": (
                "gnome-keyring-daemon: NotInInitialization"
                if late
                else "portal started cleanly"
            )
        },
        "secret_login_alias": {"stdout": "(objectpath '/',)"},
    }
    payload = {"image": image, "snapshot": snapshot}
    path = root / f"counterproof-keyring-diagnostic-{len(list(root.iterdir()))}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_bluefin_controlled_receipt_witnesses_y_yprime_y(tmp_path: Path):
    control = "control"
    bad = "bad"
    revert = "revert"

    _write_diag(tmp_path, control, active=False, dep=False, late=False)
    _write_diag(tmp_path, bad, active=True, dep=True, late=True)
    _write_diag(tmp_path, revert, active=False, dep=False, late=False)

    receipt = build_receipt(
        tmp_path,
        control_image=control,
        bad_image=bad,
        revert_image=revert,
        oracle_revision="oracle-sha",
    )

    assert receipt["verdict"] == "WITNESSED_CONTROLLED_CAUSAL"
    assert receipt["candidates"]["CONTROL"]["keyring_unit_active"] is False
    assert receipt["candidates"]["BAD"]["keyring_unit_active"] is True
    assert receipt["candidates"]["BAD"]["portal_wants_keyring"] is True
    assert receipt["candidates"]["BAD"]["not_in_initialization"] is True
    assert receipt["candidates"]["REVERT"]["keyring_unit_active"] is False


def test_bluefin_controlled_receipt_stays_inconclusive_without_revert_recovery(tmp_path: Path):
    _write_diag(tmp_path, "control", active=False, dep=False, late=False)
    _write_diag(tmp_path, "bad", active=True, dep=True, late=True)
    _write_diag(tmp_path, "revert", active=True, dep=True, late=True)

    receipt = build_receipt(
        tmp_path,
        control_image="control",
        bad_image="bad",
        revert_image="revert",
        oracle_revision="oracle-sha",
    )

    assert receipt["verdict"] == "INCONCLUSIVE_CONTROLLED_CAUSAL"


def test_bluefin_controlled_receipt_rejects_duplicate_diagnostics(tmp_path: Path):
    _write_diag(tmp_path, "control", active=False, dep=False, late=False)
    _write_diag(tmp_path, "control", active=True, dep=True, late=True)
    _write_diag(tmp_path, "bad", active=True, dep=True, late=True)
    _write_diag(tmp_path, "revert", active=False, dep=False, late=False)

    with pytest.raises(ValueError, match="AMBIGUOUS_EVIDENCE"):
        build_receipt(
            tmp_path,
            control_image="control",
            bad_image="bad",
            revert_image="revert",
            oracle_revision="oracle-sha",
        )


def test_bluefin_controlled_receipt_requires_distinct_candidate_images(tmp_path: Path):
    _write_diag(tmp_path, "shared", active=False, dep=False, late=False)
    _write_diag(tmp_path, "bad", active=True, dep=True, late=True)

    with pytest.raises(ValueError, match="INVALID_EXPERIMENT"):
        build_receipt(
            tmp_path,
            control_image="shared",
            bad_image="bad",
            revert_image="shared",
            oracle_revision="oracle-sha",
        )


def test_bluefin_diagnostics_can_feed_generic_causal_replay(tmp_path: Path):
    diagnostics = tmp_path / "diagnostics"
    diagnostics.mkdir()
    _write_diag(diagnostics, "control", active=False, dep=False, late=False)
    _write_diag(diagnostics, "bad", active=True, dep=True, late=True)
    _write_diag(diagnostics, "revert", active=False, dep=False, late=False)

    manifest = prepare_generic_replay(
        diagnostics,
        output_dir=tmp_path / "generic",
        control_image="control",
        bad_image="bad",
        revert_image="revert",
        oracle_revision="oracle-sha",
        adapter_revision="counterproof-sha",
    )
    receipt = build_causal_replay_receipt(manifest)

    assert receipt["verdict"] == "WITNESSED_CAUSAL_REPLAY"
    assert receipt["oracle"]["revision"] == "oracle-sha"
    assert receipt["oracle"]["adapter_revision"] == "counterproof-sha"
    assert receipt["oracle"]["scope"] == (
        "keyring service lifecycle / portal dependency, not keyring unlock"
    )
    assert receipt["causal_expectation_count"] == 4
    for role in ("CONTROL", "BAD", "REVERT"):
        source = receipt["candidates"][role]["evidence"]["source"]
        assert source["path"].startswith("sources/")
        assert source["sha256"]
    login_alias = next(
        item for item in receipt["expectations"] if item["path"] == "login_alias"
    )
    assert login_alias["causal_pattern"] is False
    assert login_alias["match"] is True


def test_bluefin_generic_replay_preserves_raw_diagnostic_bytes(tmp_path: Path):
    diagnostics = tmp_path / "diagnostics"
    diagnostics.mkdir()
    _write_diag(diagnostics, "control", active=False, dep=False, late=False)
    _write_diag(diagnostics, "bad", active=True, dep=True, late=True)
    _write_diag(diagnostics, "revert", active=False, dep=False, late=False)

    original_bad = next(
        path for path in diagnostics.iterdir()
        if json.loads(path.read_text(encoding="utf-8"))["image"] == "bad"
    )
    manifest = prepare_generic_replay(
        diagnostics,
        output_dir=tmp_path / "generic",
        control_image="control",
        bad_image="bad",
        revert_image="revert",
        oracle_revision="oracle-sha",
        adapter_revision="counterproof-sha",
    )

    raw_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    source_name = raw_manifest["candidates"]["BAD"]["source_evidence"]
    copied = manifest.parent / source_name
    assert copied.read_bytes() == original_bad.read_bytes()
