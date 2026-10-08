# Outcome Witness v0.1

Status: **experimental**

Issue: #180

Outcome Witness is a small post-execution evidence object for one question:

> Did the intended external outcome actually become true?

It is deliberately **not** another generic agent trace, action receipt, approval packet, or policy format.

## Boundary

Outcome Witness separates four facts that are often collapsed:

```text
intent
  != command
  != executor acknowledgement
  != externally observed outcome
```

A successful tool call MUST NOT be upgraded to `VERIFIED` without a qualifying external observation and an explicit oracle.

## Inputs

An Outcome Witness binds:

- the intended external state;
- a reference to the action or trace being evaluated;
- the observer used to inspect external state;
- observation freshness;
- an explicit oracle;
- content-addressed observation evidence;
- one conservative verdict;
- the allowed recovery boundary.

The machine schema is:

```text
schemas/outcome-witness-v0.1.schema.json
```

## Verdicts

### VERIFIED

Use only when:

1. the external observation is within its declared freshness bound;
2. the declared oracle is applicable;
3. the observed state satisfies the intended outcome.

### CONTRADICTED

Use only when:

1. the observation is fresh enough to evaluate;
2. the oracle is applicable;
3. the observed state positively conflicts with the intended outcome.

### INCONCLUSIVE

Use when the evidence cannot safely establish either of the above, including:

- stale observation;
- missing observer data;
- missing oracle prerequisite;
- ambiguous observer authority;
- unverifiable evidence identity.

`INCONCLUSIVE` is not failure. It is refusal to manufacture outcome confidence.

## Non-claims

An Outcome Witness does not prove:

- that the action was authorized correctly;
- that the referenced action caused the observed state;
- that the executor behaved correctly internally;
- that the oracle is universally authoritative;
- that an executor-reported success is an external observation.

Causality requires a stronger experiment.

## Observer independence

`observer.independent_of_executor` records whether the observation comes from a source independent of the component that reports action success.

This field is descriptive in v0.1. It does not automatically decide the verdict.

A future version may define stricter assurance profiles. v0.1 intentionally avoids pretending all domains share the same trust model.

## Interoperability rule

Outcome Witness SHOULD reference existing execution identifiers instead of creating a parallel tracing system.

Examples:

- OpenTelemetry tool-execution span id;
- MCP/A2A invocation id;
- payment request id;
- deployment/change request id;
- device command id;
- an existing signed action receipt.

The witness owns post-execution evidence semantics only.

## First acceptance case

The first target is a physical-window workflow:

```text
agent intent: window should be closed
        ↓
bounded command dispatch
        ↓
executor ACK = success
        ↓
fresh device readback
        ↓
oracle evaluates terminal state
        ↓
VERIFIED / CONTRADICTED / INCONCLUSIVE
```

The most valuable fixture is not a happy path.

It is a real case where:

```text
executor acknowledgement = success
outcome verdict = CONTRADICTED or INCONCLUSIVE
```

That demonstrates why the primitive exists.

## Graduation criterion

Outcome Witness remains experimental until at least one workflow outside CounterProof can consume or reproduce its semantics.

A schema used only by CounterProof is not adoption.

## Design rule

**Do not turn an execution record into proof of reality.**
