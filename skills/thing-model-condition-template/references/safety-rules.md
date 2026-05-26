# Safety Rules Reference

## Principle

Safety constraints ALWAYS override comfort, energy-saving, and user preferences.
They cannot be disabled by user configuration.

## Common Safety Constraints

| Constraint ID | Description |
|---|---|
| `no_close_if_fire_alarm_active` | Never close windows/doors if fire alarm is active |
| `no_close_if_person_in_path` | Never close if motion sensor detects person in path |
| `no_heating_if_gas_leak_detected` | Never activate heating if gas sensor triggers |
| `no_lock_if_emergency_mode` | Never lock doors in emergency mode |
| `max_temperature_override` | Never exceed safe temperature thresholds |

## Conflict Resolution

When a safety constraint conflicts with a user-requested action:
1. Block the action
2. Log the conflict with reason
3. Notify the user
4. Do NOT silently ignore the request
