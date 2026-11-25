# Outcome Witness ↔ Intent-to-State Conformance

**Experimental interoperability probe. Not a new protocol.**

This public experiment tests a narrow composition:

```text
CounterProof Outcome Witness
  authoritative external observation
        +
separate task-semantic policy contract
        ↓
PASS / FAIL / INDETERMINATE
```

## Ownership boundary

CounterProof / Outcome Witness owns:

- action reference;
- authoritative observer;
- freshness/provenance;
- oracle evaluation;
- `VERIFIED / CONTRADICTED / INCONCLUSIVE` external-outcome evidence.

The policy input owns:

- which durable effect was authorized;
- which values are allowed.

The bridge owns only:

- reconciling sufficient external evidence with that declared policy.

An approval receipt is not automatically the policy contract, and an executor success is not an Outcome Witness.

## Run

```bash
python experiments/outcome-witness-intent-state-conformance/bridge.py \
  --witness experiments/outcome-witness-intent-state-conformance/fixtures/window-verified.json \
  --policy experiments/outcome-witness-intent-state-conformance/fixtures/window-policy.json
```

Expected result: `PASS`.

Swap in `window-contradicted.json` and the result is `FAIL`.

`INCONCLUSIVE` witnesses map to `INDETERMINATE`, not PASS.

## Why this experiment exists

The goal is to prove composition, not ownership.

If Outcome Witness becomes useful, it should remain an external-effect evidence provider that can feed:

- SCITT/AEB-aligned verification;
- OpenTelemetry-linked workflows;
- independent intent/effect conformance evaluators.

Graduation criterion:

> at least one external workflow consumes or reproduces the semantics.

Until then this branch is a public experiment, not adopted infrastructure.


## Machine-readable interoperability vectors

`vectors.json` freezes the current experimental contract as data rather than prose.

Each vector names:

- witness fixture;
- policy fixture;
- expected verdict;
- expected reason.

The repository test suite executes every vector. A third-party implementation can therefore
consume the same file and compare its own results without importing CounterProof internals.

Current vectors cover:

1. verified + authorized → `PASS`;
2. contradicted value → `FAIL`;
3. inconclusive witness → `INDETERMINATE`;
4. verified but unauthorized effect → `FAIL`.

The manifest is experimental and versioned independently from Outcome Witness itself.
