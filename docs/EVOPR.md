# EvoPR — Behavior Proof for Self-Changing Agents

> **Your agent changed. Show the proof.**

EvoPR is an experimental change-control layer inside SkillFactory.

The project is deliberately split into two things:

1. **what is executable today**;
2. **the larger verified-agent-evolution architecture we are working toward**.

Do not read the target architecture as a statement that every stage is already implemented.

## Current executable path

Today EvoPR can:

```text
explicit Evolution Packet
        ↓
candidate mutations + replay evidence
        ↓
promotion gate
        ↓
Behavior PR Markdown
```

It can also execute a real command-based comparison:

```text
same replay case
    ├── baseline argv → real subprocess → score
    └── candidate argv → real subprocess → score
                               ↓
                         replay result
```

The command adapter is intentionally generic. Any test runner, simulator, benchmark, service check
or agent harness that can expose an exit code can participate.

## Current status

Run:

```bash
evopr audit
```

The audit uses four statuses:

- **tested** — exercised by automated tests / CI;
- **partial** — a data contract or review representation exists, but the full runtime behavior does not;
- **demo** — interactive product surface exists, but it uses fixture outcomes;
- **planned** — architecture / roadmap only.

The repository treats that distinction as part of the product contract.

## Behavior Proof Sheet

The interactive UI is not intended to be an operations dashboard.

It treats one behavior change as one experiment:

```text
INCIDENT
   ↓
CAUSE LENS
   ↓
MUTATION POINT
  ↙         ↘
recorded   candidate
 world       world
  ↘         ↙
    PROOF
     ↓
ACCEPT / REJECT
```

The central visual primitive is a **worldline split**: the same recorded case shares a history until
one behavior mutation causes the candidate path to diverge.

The browser interaction is tested in Chromium. Its displayed replay scores are currently fixtures.
Use `evopr replay` for real subprocess measurement.

## Current real replay contract

Example:

```json
{
  "root": "..",
  "cases": [
    {
      "case_id": "failure-418",
      "suite": "regression",
      "baseline": ["python", "baseline_eval.py", "failure-418"],
      "candidate": ["python", "candidate_eval.py", "failure-418"]
    }
  ]
}
```

Run:

```bash
evopr replay examples/replay_suite.json --out REPLAY_RESULTS.json
```

Current scoring:

- exit code 0 → 1.0;
- non-zero → 0.0;
- timeout → infra_error.

This is a minimal adapter, not a claim that arbitrary world state can already be snapshotted.

## Current promotion gate

A candidate is promotable when:

```text
valid replay evidence exists
AND mean delta > 0
AND regression count == 0
AND risk flags are empty
```

Infrastructure errors are excluded from behavior regression counting.

This is a deterministic default gate. It is not yet a calibrated production rollout policy.

## Current Evolution Packet

The current packet contains:

- failure summary;
- Decision Capsule;
- Outcome Receipt;
- evidence entries;
- hypotheses;
- candidate mutation surfaces;
- replay results;
- risk flags;
- activation scope;
- rollback reference.

Some fields are currently free-form rather than typed domain objects.

Supported mutation labels are:

```text
skill
prompt
policy
router
memory
tool
eval
```

This means EvoPR can represent and review those change surfaces. It does not yet automatically edit
each surface inside an arbitrary agent runtime.

## Target architecture

The larger architecture remains:

```text
REALITY
  ↓
Trace capture
  ↓
Decision Capsule
  ↓
Outcome Receipt
  ↓
Evidence graph
  ↓
Competing causal hypotheses
  ↓
Minimal mutation candidates
  ↓
Counterfactual replay / holdout
  ↓
Behavior Proof
  ↓
Evolution PR
  ↓
Shadow / canary
  ↓
Promote / rollback
  ↓
Capability lifecycle
```

### Not implemented yet

- automatic PR/review/CI/agent-trace ingestion;
- automatic Trace → Decision Capsule compilation;
- causal hypothesis generation;
- discriminating probe generation;
- arbitrary world snapshot / restore;
- automatic mutation application for every surface;
- automatic GitHub Evolution PR open / merge / revert;
- shadow routing;
- canary traffic;
- production rollback executor;
- capability split / merge / decay / retire.

## Why this is still interesting

Trajectory distillation asks:

> What lesson should we extract?

EvoPR asks a stricter question:

> **What mechanism caused the failure, what is the smallest intervention, and what executable evidence earns deployment?**

The project is useful only if that question can be turned into reproducible tests.

## CI evidence

The branch is designed to test:

- Python 3.10 / 3.11 / 3.12;
- unit and CLI behavior;
- measured baseline/candidate subprocess replay;
- clean wheel installation;
- packaged CLI from outside the repository;
- packaged playground serving;
- browser interaction in Chromium;
- example skill validation;
- capability truth-table synchronization.

See the GitHub Actions results for the current branch for the latest pass/fail state.

## Roadmap

### v0.1
Explicit packets, command replay, review artifact, conservative gate, audited capability table.

### v0.2
Structured replay adapters and richer scoring.

### v0.3
Trace compilation and causal probes.

### v0.4
GitHub-native ingestion and Evolution PR automation.

### v0.5
Online shadow/canary deployment and rollback.

### v1.0
A portable verified-evolution runtime across multiple agent harnesses.

## Research question

> **Can an agent change exactly the capability that caused a failure, show executable evidence that the intervention helps, avoid unrelated regressions, and remain reviewable and reversible?**

EvoPR does not claim the full answer yet. It is building and testing the machinery needed to make
that question falsifiable.
