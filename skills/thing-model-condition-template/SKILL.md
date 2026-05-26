---
name: thing-model-condition-template
description: Use this skill when converting open-ended smart-home or IoT device behavior requirements into reusable thing-model condition templates, especially when existing templates do not match the user's scenario.
version: "0.1.0"
license: apache-2.0
compatibility: Requires thing-model schema v3 and behavior-tree validator >= 1.0
metadata:
  owner: ai-platform
  domain: smart-home
  tags: [iot, thing-model, condition, behavior-tree, smart-home]
---

# Thing Model Condition Template Skill

## Purpose

Convert user-described device scenarios into reusable, protocol-compliant thing-model
condition templates. The output must be a generalized template that covers a class of
similar scenarios, not just the specific example provided.

## When to use

Use this skill when:

- The user describes a device-triggered behavior that existing templates cannot cover
- The request involves conditional execution, interruption, priority, or safety constraints
- The output must be persisted as a reusable protocol-level template
- The scenario involves running-state management (start, pause, resume, stop)
- Multiple devices interact with priority or conflict resolution rules

Do NOT use this skill when:
- A matching template already exists in the template library
- The request is a one-time automation rule, not a reusable template
- The scenario is too specific to generalize (single device, single user, single time)

## Procedure

1. **Extract the scenario components:**
   - Device type and capabilities
   - Trigger condition (event, threshold, schedule, state change)
   - Action sequence (what happens when triggered)
   - Interruption rule (what stops or pauses the action)
   - Safety boundary (what must never happen)
   - Priority (if multiple actions conflict)

2. **Check for existing coverage:**
   - Search the template library for similar patterns
   - If a match exists with >80% overlap, extend it rather than creating a new one

3. **Generalize the template:**
   - Replace specific values with parameterized placeholders
   - Ensure the template applies to a device class, not a single device instance
   - Add all required fields per the thing-model schema

4. **Validate the output:**
   - Run `scripts/validate_condition.py output.json`
   - Confirm all required fields are present
   - Confirm no safety constraint violations

5. **Explain the generalization:**
   - State what class of scenarios this template covers
   - State what it does NOT cover (scope boundaries)

## Gotchas

- Do NOT create one template per user sentence. Generalize.
- Do NOT ignore interruptibility when the device action has a running state.
- Safety constraints ALWAYS override comfort and energy-saving preferences.
- If two actions conflict, generate a priority rule instead of two independent actions.
- The `running` state must have both `success` and `failure` exit transitions.
- Do not use device instance IDs in templates; use device type and capability references.

## Validation

Run the validator script:

    python scripts/validate_condition.py output.json

Expected output: `PASS: all required fields present, no constraint violations`

## References

- Read `references/thing-model-protocol.md` for field definitions and schema
- Read `references/interruption-rules.md` when the scenario includes running-state interruption
- Read `references/safety-rules.md` when the scenario involves safety-critical devices
