# WindowPilot physical-observation admission gate

Status: **experimental interop probe**

This probe exists to prevent a tempting but invalid shortcut when mapping
WindowPilot hardware evidence into CounterProof:

> a fresh measured device readback from the same hardware is **not** automatically
> evidence for one exact command.

WindowPilot already has two useful artifacts:

1. `windowpilot-command-ack-v2`, carrying request/command identity, hardware
   identity, accepted-command semantics and an acknowledgement digest;
2. physical commissioning receipts, carrying measured
   `CWDS-CA01.motor_1.motorCurrentPosition` observations.

The current commissioning path persists measured observations, including on
fail-closed runs, but those phase receipts do not yet carry the exact
`command_id` of a `windowpilot-command-ack-v2` object.

CounterProof therefore refuses to manufacture that link from:

- phase ordering;
- timestamps;
- matching hardware identity;
- the words OPEN/CLOSE in a phase label;
- or the fact that both artifacts came from WindowPilot.

The admission gate becomes ready only when a measured phase explicitly carries:

- a valid physical `windowpilot-command-ack-v2`;
- matching hardware identity;
- an explicit `action_ref` whose id equals that acknowledgement's
  `command_id`.

Passing the gate still does **not** prove physical completion. It only makes the
artifact eligible for a separate outcome oracle.

## Why this seam matters

The SCITT AI-Agent Action Receipt draft describes physical completion as
requiring an authenticated physical-observation artifact bound to the action,
and explicitly leaves that artifact format undefined. AEB likewise requires
exact-action binding and authenticated reconciliation while declining to define
one universal evidence format.

The useful experiment here is therefore not a new receipt protocol. It is a
real actuator case in which command identity and physical observation are
joined without silently upgrading correlation into proof.

## Graduation rule

Do not claim external interoperability until a real CWDS-CA01 run produces an
action-bound measured artifact and an independent external implementation or
reviewer consumes/reproduces the mapping.
