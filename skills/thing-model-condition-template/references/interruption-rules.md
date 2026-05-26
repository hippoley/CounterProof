# Interruption Rules Reference

## When to define an interruption rule

Any template where the action has a `running` state that can be interrupted
MUST define an interruption rule. Examples:

- Window closing (can be stopped mid-way)
- Curtain drawing
- Fan speed ramping
- Heating/cooling cycles

## Interruption actions

| Action | Description |
|---|---|
| `stop` | Immediately halt the action |
| `pause_and_notify` | Pause and send notification to user |
| `reverse` | Reverse the action (e.g. re-open window) |
| `complete_then_stop` | Finish current step, then stop |

## Priority

If two templates conflict (both want to control the same device),
the one with higher `priority` value wins (0 = lowest, 100 = highest).
Safety constraints always win regardless of priority.
