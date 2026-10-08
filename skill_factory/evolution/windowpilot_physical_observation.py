"""Fail-closed admission gate for WindowPilot physical observation artifacts.

This module deliberately does not infer an action/outcome binding from timing,
phase names, or a shared hardware identity. A measured readback becomes eligible
for external-outcome evaluation only when the artifact carries an explicit
reference to the exact accepted physical command it is claimed to observe.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _valid_uuid(value: Any) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def assess_windowpilot_physical_observation(bundle: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []

    hardware = bundle.get("hardware_identity") or {}
    hardware_sha = str(hardware.get("identity_sha256") or "")
    if not _SHA256_RE.fullmatch(hardware_sha):
        blockers.append("missing or invalid hardware_identity.identity_sha256")

    commissioning = bundle.get("commissioning") or {}
    phases = commissioning.get("phases")
    if not isinstance(phases, list) or not phases:
        blockers.append("commissioning phases are missing")
        phases = []

    measured_phases = []
    bound_phases = []

    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            blockers.append(f"phase[{index}] is not an object")
            continue

        label = str(phase.get("phase") or f"phase[{index}]")
        measured = all(
            key in phase and phase.get(key) is not None
            for key in ("measured_pct", "timestamp", "source")
        )
        if measured:
            measured_phases.append(label)

        ack = phase.get("command_ack")
        action_ref = phase.get("action_ref")
        if ack is None and action_ref is None:
            continue
        if not isinstance(ack, dict):
            blockers.append(f"{label}: command_ack is required when action_ref is present")
            continue
        if ack.get("receipt") != "windowpilot-command-ack-v2":
            blockers.append(f"{label}: unsupported command acknowledgement contract")
            continue
        if ack.get("accepted") is not True:
            blockers.append(f"{label}: command acknowledgement is not accepted")
            continue
        if ack.get("simulated") is not False:
            blockers.append(f"{label}: simulated command cannot support physical completion")
            continue
        if ack.get("evidence_kind") != "physical-command-accepted":
            blockers.append(f"{label}: command evidence is not physical-command-accepted")
            continue
        if ack.get("hardware_identity_sha256") != hardware_sha:
            blockers.append(f"{label}: command hardware identity does not match observation bundle")
            continue
        command_id = ack.get("command_id")
        request_id = ack.get("request_id")
        if not _valid_uuid(command_id) or not _valid_uuid(request_id):
            blockers.append(f"{label}: command/request identity is not a valid UUID")
            continue
        if not _SHA256_RE.fullmatch(str(ack.get("command_ack_sha256") or "")):
            blockers.append(f"{label}: command acknowledgement digest is missing or invalid")
            continue
        if not isinstance(action_ref, dict):
            blockers.append(f"{label}: explicit action_ref is required")
            continue
        if action_ref.get("type") != "windowpilot-command-id":
            blockers.append(f"{label}: action_ref.type must be windowpilot-command-id")
            continue
        if str(action_ref.get("id") or "") != str(command_id):
            blockers.append(f"{label}: action_ref does not match command_ack.command_id")
            continue
        if not measured:
            blockers.append(f"{label}: action-bound phase lacks measured observation fields")
            continue
        bound_phases.append(label)

    if measured_phases and not bound_phases:
        blockers.append(
            "measured physical observations exist, but none is explicitly bound "
            "to an exact accepted command"
        )

    admission = (
        "READY_FOR_EXTERNAL_OUTCOME_EVALUATION"
        if bound_phases and not blockers
        else "BLOCKED"
    )
    return {
        "schema_version": "counterproof.windowpilot-physical-observation-gate/v0.1",
        "admission": admission,
        "measured_phases": measured_phases,
        "action_bound_phases": bound_phases,
        "blockers": blockers,
        "non_claims": [
            "This gate does not prove physical completion.",
            "A command acknowledgement is not a physical observation.",
            "Shared hardware identity and temporal proximity do not create an action binding.",
        ],
    }
