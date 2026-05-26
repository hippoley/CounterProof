---
name: energy-saving-schedule
description: Use this skill when converting time-based or occupancy-based energy saving requirements into scheduled device control templates, especially for HVAC, lighting, and appliance management.
version: "0.1.0"
license: apache-2.0
compatibility: Requires thing-model schema v3 and scheduler engine >= 2.0
metadata:
  owner: ai-platform
  domain: smart-home
  tags: [energy, schedule, hvac, lighting, occupancy, smart-home]
---

# Energy Saving Schedule Skill

## Purpose

Convert user-described energy saving goals into reusable, scheduled device control templates.
The output must generalize across similar time-based or occupancy-based scenarios.

## When to use

Use this skill when:

- The user wants to reduce energy consumption based on time of day, day of week, or occupancy
- The request involves scheduled on/off, setpoint adjustment, or mode switching
- Multiple devices need coordinated scheduling (e.g. HVAC + blinds + lighting)
- The scenario includes override conditions (e.g. "but not when someone is home")

Do NOT use this skill when:
- The request is a one-time manual action, not a recurring schedule
- The trigger is a sensor event (use thing-model-condition-template instead)
- The schedule is already covered by an existing template

## Procedure

1. **Extract schedule parameters:**
   - Time window (start time, end time, days of week)
   - Occupancy condition (if any)
   - Target devices and their setpoints or modes
   - Override conditions

2. **Identify the energy saving pattern:**
   - Setback: reduce setpoint during unoccupied hours
   - Shutdown: turn off devices when not needed
   - Coordination: sync multiple devices for maximum savings

3. **Generalize the template:**
   - Use parameterized time windows, not hardcoded times
   - Use occupancy state as a variable, not a specific sensor ID
   - Ensure the template applies to a device class

4. **Handle conflicts:**
   - If comfort and energy saving conflict, generate a priority rule
   - Safety constraints (min/max temperature) always override energy saving

5. **Validate the output:**
   - Run scripts/validate_schedule.py output.json

## Gotchas

- Do NOT hardcode specific times like "22:00" -- use parameterized time windows
- Do NOT ignore occupancy override -- most energy saving schedules need it
- Minimum temperature safety constraints must be included for HVAC templates
- Weekend vs weekday schedules are different patterns -- do not merge them
- "Away mode" and "sleep mode" are different -- do not conflate them

## Validation

    python scripts/validate_schedule.py output.json

## References

- Read references/schedule-protocol.md for schedule field definitions
- Read references/safety-rules.md for temperature safety constraints
