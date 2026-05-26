---
name: multi-sensor-priority-control
description: Use this skill when multiple sensors can trigger conflicting device actions and a priority resolution rule is needed to determine which trigger wins.
version: "0.1.0"
license: apache-2.0
compatibility: Requires thing-model schema v3 with priority field support
metadata:
  owner: ai-platform
  domain: smart-home
  tags: [multi-sensor, priority, conflict-resolution, smart-home, iot]
---

# Multi-Sensor Priority Control Skill

## Purpose

Generate device control templates that handle conflicts between multiple sensor triggers
competing to control the same device. The output must include explicit priority rules
and conflict resolution logic.

## When to use

Use this skill when:

- Two or more sensors can independently trigger actions on the same device
- The actions conflict (e.g. one wants to open a window, another wants to close it)
- The user describes a scenario with "but if", "unless", "except when", or "higher priority"
- The scenario involves safety vs comfort trade-offs

Do NOT use this skill when:
- Only one sensor controls the device (use thing-model-condition-template instead)
- The sensors trigger different devices with no conflict
- The conflict is already resolved by a safety constraint

## Procedure

1. **Identify all triggers and their actions:**
   - List every sensor that can affect the target device
   - List the action each sensor wants to perform
   - Identify which actions conflict

2. **Assign priority levels:**
   - Safety triggers: priority 90-100
   - Environmental triggers (CO2, temperature, humidity): priority 60-80
   - Comfort triggers (user preference, schedule): priority 30-50
   - Energy saving triggers: priority 10-30

3. **Define the conflict resolution rule:**
   - Higher priority wins
   - Equal priority: last-write-wins or user-configurable
   - Safety constraints always override regardless of priority

4. **Generate the priority rule template:**
   - Include all competing triggers
   - Include the resolution strategy
   - Include the override conditions

5. **Validate:**
   - Run scripts/validate_priority.py output.json
   - Confirm no two safety-level triggers conflict

## Gotchas

- Do NOT assign equal priority to conflicting triggers without a tiebreaker
- Safety triggers must always be priority >= 90
- Do NOT create separate templates for each trigger -- they must be in one priority rule
- If a user says "X is more important than Y", that is a priority assignment
- Comfort preferences can be overridden; safety constraints cannot

## Validation

    python scripts/validate_priority.py output.json

## References

- Read references/priority-protocol.md for priority field definitions
- Read references/safety-rules.md for safety constraint priority rules
