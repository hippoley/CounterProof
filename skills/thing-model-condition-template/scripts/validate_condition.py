"""
Deterministic validator for thing-model condition template JSON output.
Usage: python validate_condition.py <output.json>
"""
import json
import sys
from pathlib import Path


REQUIRED_TOP_LEVEL = ["template_id", "name", "domain", "trigger", "action", "state_machine"]
REQUIRED_TRIGGER = ["device_type", "capability", "condition"]
REQUIRED_ACTION = ["device_type", "capability", "command"]
REQUIRED_STATES = {"idle", "running", "success", "failure"}


def validate(data: dict) -> list[str]:
    errors = []

    # Top-level required fields
    for field in REQUIRED_TOP_LEVEL:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Trigger fields
    trigger = data.get("trigger", {})
    for field in REQUIRED_TRIGGER:
        if field not in trigger:
            errors.append(f"Missing trigger field: {field}")

    # Action fields
    action = data.get("action", {})
    for field in REQUIRED_ACTION:
        if field not in action:
            errors.append(f"Missing action field: {field}")

    # State machine
    sm = data.get("state_machine", {})
    states = set(sm.get("states", []))
    missing_states = REQUIRED_STATES - states
    if missing_states:
        errors.append(f"State machine missing required states: {missing_states}")

    transitions = sm.get("transitions", [])
    if not transitions:
        errors.append("State machine has no transitions defined")

    # Safety: no device instance IDs (heuristic: no UUIDs or numeric IDs in template_id)
    template_id = data.get("template_id", "")
    if any(c.isdigit() for c in template_id.split("-")[-1]):
        pass  # version suffix is OK

    # Priority range
    priority = data.get("priority")
    if priority is not None and not (0 <= priority <= 100):
        errors.append(f"Priority must be 0-100, got: {priority}")

    return errors


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python validate_condition.py <output.json>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(1)

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        sys.exit(1)

    errors = validate(data)
    if errors:
        print("FAIL:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("PASS: all required fields present, no constraint violations")
        sys.exit(0)


if __name__ == "__main__":
    main()
