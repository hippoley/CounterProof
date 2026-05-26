---
name: device-safety-interlock
description: Use this skill when a device action must be blocked, paused, or reversed if a safety condition is detected, such as fire alarm, gas leak, emergency mode, or person-in-path detection.
version: "0.1.0"
license: apache-2.0
compatibility: Requires thing-model schema v3 with safety_constraints field support
metadata:
  owner: ai-platform
  domain: smart-home
  tags: [safety, interlock, emergency, fire-alarm, gas-leak, smart-home, iot]
---

# Device Safety Interlock Skill

## Purpose

Generate safety interlock rules that block, pause, or reverse device actions when
a safety condition is detected. Safety interlocks are non-negotiable: they cannot
be overridden by user preference, schedule, or energy saving rules.

## When to use

Use this skill when:

- A device action could be dangerous if a safety condition is active
- The user mentions fire alarm, gas leak, emergency mode, or person detection
- The scenario requires "never do X if Y is active"
- The output must include a safety_constraints field

Do NOT use this skill when:
- The constraint is a comfort preference, not a safety requirement
- The scenario is about priority between two non-safety triggers
- The safety condition is already handled by an existing interlock template

## Procedure

1. **Identify the safety condition:**
   - What sensor or system state triggers the interlock?
   - Is it a binary state (active/inactive) or a threshold?
   - What is the severity? (life-safety vs property-safety vs comfort)

2. **Identify the blocked action:**
   - What device action must be prevented?
   - Is it a full block, a pause, or a reversal?
   - What should happen to in-progress actions when the interlock fires?

3. **Define the interlock behavior:**
   - BLOCK: prevent the action from starting
   - PAUSE: stop an in-progress action and hold
   - REVERSE: undo the action (e.g. re-open a door that was closing)
   - NOTIFY: alert the user and wait for acknowledgment

4. **Generate the safety constraint:**
   - Add to safety_constraints array in the template
   - Set priority to 90-100 (safety level)
   - Ensure the constraint cannot be disabled by user config

5. **Validate:**
   - Run scripts/validate_interlock.py output.json
   - Confirm safety_constraints field is present and non-empty
   - Confirm priority >= 90

## Gotchas

- Safety interlocks CANNOT be overridden by user preference or schedule
- Do NOT use priority < 90 for safety interlocks
- An in-progress action must be handled -- do not just block new actions
- "Person in path" detection requires motion sensor, not just occupancy sensor
- Gas leak interlocks must also block heating and spark-generating devices
- Fire alarm interlocks must OPEN doors and windows, not close them

## Validation

    python scripts/validate_interlock.py output.json

Expected: PASS with safety_constraints non-empty and priority >= 90

## References

- Read references/safety-rules.md for the full list of safety constraint IDs
- Read references/interlock-protocol.md for interlock behavior definitions
