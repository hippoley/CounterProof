import json
from pathlib import Path

import pytest

from scripts.reality_bluefin_4539_flagship import build_flagship_receipt


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


def _flagship(tmp_path: Path, **overrides):
    _write_diag(tmp_path, "control", active=False, dep=False, late=False)
    _write_diag(tmp_path, "bad", active=True, dep=True, late=True)
    _write_diag(tmp_path, "revert", active=False, dep=False, late=False)
    kwargs = {
        "control_image": "control",
        "bad_image": "bad",
        "revert_image": "revert",
        "oracle_revision": "oracle-sha",
        "source_run": 37412091382,
        "workflow_head_sha": "8b422a2334a093185bf91e6783e454077eb7cffa",
        "workflow_url": "https://github.com/hippoley/CounterProof/actions/runs/37412091382",
        "runtime_results": {
            "CONTROL": "success",
            "BAD": "success",
            "REVERT": "success",
        },
        "upstream_workflow_revision": "a99ca5ea0553f778a74f5d5152fefbbb47d86da4",
    }
    kwargs.update(overrides)
    return build_flagship_receipt(tmp_path, **kwargs)


def test_flagship_receipt_binds_same_oracle_runtime_and_causal_conclusion(tmp_path: Path):
    receipt = _flagship(tmp_path)

    assert receipt["schema_version"] == 2
    assert receipt["receipt_type"] == "FLAGSHIP_CONTROLLED_CAUSAL"
    assert receipt["verdict"] == "WITNESSED_CONTROLLED_CAUSAL"
    assert receipt["experiment"]["same_oracle_for_all_candidates"] is True
    assert receipt["source_run"]["workflow_run"] == 37412091382
    assert receipt["oracle_identity"]["runtime"] == "projectbluefin/testsuite GNOME/QEMU"
    assert receipt["runtime_execution"]["CONTROL"]["job_result"] == "success"
    assert receipt["runtime_execution"]["BAD"]["job_result"] == "success"
    assert receipt["runtime_execution"]["REVERT"]["job_result"] == "success"
    assert receipt["causal_conclusion"]["pattern"] == (
        "CONTROL_BASELINE -> BAD_DIVERGENCE -> REVERT_RECOVERY"
    )


def test_flagship_receipt_refuses_incomparable_runtime_execution(tmp_path: Path):
    with pytest.raises(ValueError, match="RUNTIME_NOT_COMPARABLE"):
        _flagship(
            tmp_path,
            runtime_results={
                "CONTROL": "success",
                "BAD": "failure",
                "REVERT": "success",
            },
        )


def test_flagship_receipt_refuses_missing_runtime_role(tmp_path: Path):
    with pytest.raises(ValueError, match="MISSING_RUNTIME_RESULT"):
        _flagship(
            tmp_path,
            runtime_results={
                "CONTROL": "success",
                "BAD": "success",
            },
        )
