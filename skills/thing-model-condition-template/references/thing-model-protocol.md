# Thing Model Protocol Reference

## Overview

A thing-model condition template defines a reusable, parameterized behavior pattern
for IoT devices. It is protocol-level: it describes WHAT should happen and WHEN,
not HOW a specific device implements it.

## Required Fields

| Field | Type | Description |
|---|---|---|
| template_id | string | Unique identifier, format: `{domain}-{trigger}-{action}-v{n}` |
| name | string | Human-readable name |
| domain | string | Domain label (e.g. smart-home, industrial) |
| version | string | Semantic version |
| trigger | object | What causes the action to fire |
| action | object | What the device does when triggered |
| state_machine | object | States and transitions |

## State Machine

Every template must define these four states:

- `idle`: waiting for trigger
- `running`: action in progress
- `success`: action completed successfully
- `failure`: action failed or timed out

## Trigger Object

```json
{
  "device_type": "rain_sensor",
  "capability": "rain_detection",
  "condition": "rain_detected == true",
  "threshold": null
}
```

## Action Object

```json
{
  "device_type": "smart_window",
  "capability": "position_control",
  "command": "close",
  "parameters": {"target_position": 0}
}
```

## Interruption Rule

Optional. Defines what stops or pauses a running action.

```json
{
  "condition": "manual_override == true",
  "action": "pause_and_notify"
}
```

## Safety Constraints

Array of constraint identifiers. Safety constraints always override other rules.
Example: `"do_not_close_if_person_detected_in_window_path"`
