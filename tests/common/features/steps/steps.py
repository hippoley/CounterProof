from __future__ import annotations

import json
import os
import re
from pathlib import Path

from behave import step

from tests.shared.ssh_steps import *  # noqa: F401,F403
from tests.shared.ssh_steps import run_ssh


@step("Capture CounterProof keyring causal diagnostics")
def capture_counterproof_keyring_causal_diagnostics(context):
    probes = {
        "secret_login_alias": (
            "gdbus call --session --dest org.freedesktop.secrets "
            "--object-path /org/freedesktop/secrets "
            "--method org.freedesktop.Secret.Service.ReadAlias login 2>&1 || true"
        ),
        "keyring_unit": (
            "systemctl --user show gnome-keyring-daemon.service "
            "--property=ActiveState,SubState,MainPID,ExecMainStartTimestampMonotonic "
            "--no-pager 2>&1 || true"
        ),
        "portal_unit": (
            "systemctl --user show xdg-desktop-portal.service "
            "--property=ActiveState,SubState,MainPID,ExecMainStartTimestampMonotonic "
            "--no-pager 2>&1 || true"
        ),
        "keyring_processes": "pgrep -a gnome-keyring-daemon 2>&1 || true",
        "portal_dependencies": (
            "systemctl --user list-dependencies xdg-desktop-portal.service "
            "--plain --no-pager 2>&1 || true"
        ),
        "keyring_journal": (
            "journalctl --user -b --no-pager -o short-monotonic 2>/dev/null "
            "| grep -E 'gnome-keyring|xdg-desktop-portal|NotInInitialization' "
            "| tail -80 || true"
        ),
    }

    snapshot = {}
    for name, command in probes.items():
        stdout, rc = run_ssh(context, command)
        snapshot[name] = {"rc": rc, "stdout": stdout.strip()}

    # Deliberately print one stable JSON record: this is diagnostic evidence,
    # not an acceptance verdict. The outer replay compares it across candidates.
    payload = {
        "image": os.environ.get("IMAGE", ""),
        "snapshot": snapshot,
    }
    encoded = json.dumps(payload, sort_keys=True)
    print("COUNTERPROOF_KEYRING_DIAGNOSTIC=" + encoded)

    # Persist the same diagnostic into the testsuite result volume so the
    # parent workflow can build a machine-readable three-candidate receipt.
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", payload["image"]).strip("-") or "unknown"
    results_dir = Path(os.environ.get("COUNTERPROOF_RESULTS_DIR", "results"))
    out = results_dir / f"counterproof-keyring-diagnostic-{slug}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(encoded + "\n", encoding="utf-8")
