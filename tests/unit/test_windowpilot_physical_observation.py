from skill_factory.evolution.windowpilot_physical_observation import (
    assess_windowpilot_physical_observation,
)

HARDWARE_SHA = "a" * 64
ACK_SHA = "b" * 64
COMMAND_ID = "11111111-1111-4111-8111-111111111111"
REQUEST_ID = "22222222-2222-4222-8222-222222222222"


def _bundle():
    return {
        "status": "FAIL",
        "hardware_identity": {"identity_sha256": HARDWARE_SHA},
        "commissioning": {
            "phases": [
                {
                    "phase": "READ",
                    "measured_pct": 0.0,
                    "timestamp": 100.0,
                    "source": "CWDS-CA01.motor_1.motorCurrentPosition",
                    "quality": "measured",
                },
                {
                    "phase": "OPEN_5",
                    "measured_pct": 1.5,
                    "timestamp": 101.0,
                    "source": "CWDS-CA01.motor_1.motorCurrentPosition",
                    "quality": "measured",
                },
            ]
        },
    }


def _ack():
    return {
        "receipt": "windowpilot-command-ack-v2",
        "accepted": True,
        "request_id": REQUEST_ID,
        "command_id": COMMAND_ID,
        "simulated": False,
        "hardware_identity_sha256": HARDWARE_SHA,
        "evidence_kind": "physical-command-accepted",
        "command_ack_sha256": ACK_SHA,
    }


def test_current_style_measured_bundle_is_blocked_without_exact_action_binding():
    result = assess_windowpilot_physical_observation(_bundle())

    assert result["admission"] == "BLOCKED"
    assert result["measured_phases"] == ["READ", "OPEN_5"]
    assert result["action_bound_phases"] == []
    assert any("none is explicitly bound" in item for item in result["blockers"])


def test_temporal_proximity_and_same_hardware_do_not_create_binding():
    bundle = _bundle()
    bundle["commissioning"]["phases"][1]["command_ack"] = _ack()

    result = assess_windowpilot_physical_observation(bundle)

    assert result["admission"] == "BLOCKED"
    assert any("explicit action_ref is required" in item for item in result["blockers"])


def test_mismatched_action_reference_is_rejected():
    bundle = _bundle()
    phase = bundle["commissioning"]["phases"][1]
    phase["command_ack"] = _ack()
    phase["action_ref"] = {
        "type": "windowpilot-command-id",
        "id": "33333333-3333-4333-8333-333333333333",
    }

    result = assess_windowpilot_physical_observation(bundle)

    assert result["admission"] == "BLOCKED"
    assert any("does not match" in item for item in result["blockers"])


def test_explicit_command_bound_measured_phase_can_cross_the_admission_gate():
    bundle = _bundle()
    phase = bundle["commissioning"]["phases"][1]
    phase["command_ack"] = _ack()
    phase["action_ref"] = {
        "type": "windowpilot-command-id",
        "id": COMMAND_ID,
    }

    result = assess_windowpilot_physical_observation(bundle)

    assert result["admission"] == "READY_FOR_EXTERNAL_OUTCOME_EVALUATION"
    assert result["action_bound_phases"] == ["OPEN_5"]
    assert result["blockers"] == []
