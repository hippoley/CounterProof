# Black-box Behavior Witness Contract (experimental)

This experiment asks a narrow question:

> Can we turn observations of an authorized black-box program into a portable, replayable compatibility contract without pretending we recovered its source or full specification?

It is deliberately **not** a reverse-engineering framework and not a new general-purpose "behavioral IR". Existing work already covers specification mining, state-machine learning, differential testing, and source-derived behavioral IRs. This experiment focuses on a missing evidence boundary:

```
probe input
  -> observed output / state transition
  -> normalization rule
  -> evidence-backed claim
  -> candidate replay
  -> PASS / FAIL / UNKNOWN
```

The contract records only what was observed or explicitly declared. Unobserved behavior stays unknown.

## Why this belongs in CounterProof as an experiment

CounterProof already distinguishes claims, evidence, oracles, provenance, and proof boundaries. A black-box compatibility claim has the same failure mode as an agent-fix claim: a green check can overstate what the evidence actually establishes.

This experiment tests whether the same discipline can be applied to compatibility:

- exact probe identity;
- reference observation;
- comparison semantics;
- candidate observation;
- explicit provenance;
- verdict scoped to the probes actually executed;
- no "equivalent implementation" claim unless the evidence supports it.

## Minimal contract

See `contract.schema.json`.

A witness contains:

- `subject`: the reference artifact or service identity;
- `operation`: the public behavior being probed;
- `probe`: exact input and environment assumptions;
- `reference_observation`: what happened on the reference;
- `comparator`: how candidate output is normalized and compared;
- `evidence`: capture provenance and confidence;
- `scope`: what this witness does **not** establish.

## Replay

```bash
python experiments/behavior_witness/verify.py \
  experiments/behavior_witness/examples/reference-contract.json \
  experiments/behavior_witness/examples/candidate-pass.json

python experiments/behavior_witness/verify.py \
  experiments/behavior_witness/examples/reference-contract.json \
  experiments/behavior_witness/examples/candidate-fail.json
```

Expected verdicts:

```text
PASS    observed behavior matches the frozen witness
FAIL    candidate differs under the declared comparator
UNKNOWN contract or observation is insufficient for a verdict
```

## Non-claims

This experiment does **not** claim:

- complete behavioral equivalence;
- recovery of proprietary source or hidden implementation details;
- correctness outside the recorded probe scope;
- that the reference implementation itself is correct.

The goal is much smaller and more useful: make a compatibility statement replayable and difficult to overclaim.

## Adoption test

This experiment graduates only if a second tool or repository can consume the contract without importing CounterProof internals. If no external consumer appears, the format should remain an experiment rather than become a new project.
