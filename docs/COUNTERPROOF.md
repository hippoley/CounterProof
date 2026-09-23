# Counterproof — Falsifiable Change Control for Self-Modifying Agents

> **Your agent changed. Show the proof.**

Counterproof is an experimental change-control layer inside SkillFactory.

The important distinction is:

- **tested runtime behavior** — exercised by CI;
- **partial behavior** — the contract exists but the full runtime does not;
- **demo behavior** — the product surface exists with fixture outcomes;
- **planned behavior** — architecture only.

Run the source of truth:

```bash
counterproof audit
```

## Current executable path

The strongest path in the current branch is:

```text
RAW TRACE
   ↓
Decision Capsule + Outcome Receipt
   ↓
typed evidence
   ↓
competing heuristic hypotheses
   ↓
Probe Contracts
   ↓
same cases × multiple executable interventions
   ↓
survived / falsified / inconclusive
   ↓
unique survivor?
  ↙           ↘
yes            no
 ↓              ↓
select          remain ambiguous
 ↓
Behavior Proof
 ↓
promotion gate
```

Run it:

```bash
counterproof evolve examples/traces/tenant_failure.json \
  --experiment-manifest examples/discrimination_suite.json \
  --surface policy \
  --surface skill \
  --surface prompt \
  --out EVOLUTION_REVIEW.md \
  --packet-out EVOLVED_PACKET.json
```

The implementation selects a mutation automatically only when exactly one tested intervention survives.

## Trace compilation

Counterproof accepts JSON or JSONL event traces.

The current deterministic compiler:

1. finds the relevant decision before a negative outcome;
2. builds a Decision Capsule;
3. builds an Outcome Receipt;
4. converts corrections / verifier outcomes / failures into Evidence;
5. ranks candidate mutation surfaces;
6. generates one falsifiable Probe Contract per hypothesis.

The hypothesis ranking is heuristic. It is **not** unique causal inference.

Example candidate surfaces:

```text
policy
skill
prompt
router
memory
tool
eval
```

## Probe Contracts

A generated hypothesis carries:

```text
INTERVENTION
what one behavior surface should change

SUPPORTS IF
what outcome would be evidence for the hypothesis

FALSIFIED IF
what outcome would contradict it

HOLDOUT
what nearby behavior should remain unchanged
```

A Probe Contract is guidance. Executable replay evidence is what matters.

## Active discrimination

A discrimination manifest supplies the same baseline cases and multiple intervention commands:

```json
{
  "case_id": "cross-tenant-attack-07",
  "baseline": ["python", "eval.py", "baseline", "cross-tenant-attack-07"],
  "variants": {
    "policy": ["python", "eval.py", "policy", "cross-tenant-attack-07"],
    "skill": ["python", "eval.py", "skill", "cross-tenant-attack-07"],
    "prompt": ["python", "eval.py", "prompt", "cross-tenant-attack-07"]
  }
}
```

Then:

```bash
counterproof discriminate examples/traces/tenant_failure.json \
  --experiment-manifest examples/discrimination_suite.json \
  --surface policy \
  --surface skill \
  --surface prompt
```

Variant status:

- **survived** — required cases ran, failure behavior improved, no regression;
- **falsified** — an explicit failure or regression was observed;
- **inconclusive** — evidence is incomplete, timed out, missing, or non-discriminating.

Missing variants and infrastructure errors cannot silently count as success.

## Diagnostic cases

Counterproof records each intervention's behavior signature across the same cases.

Example:

```text
                    failure     security holdout     normal holdout
policy                 P               P                  P
skill                  P               F                  P
prompt                 P               F                  P
```

The security holdout is diagnostic because candidate predictions diverge there.

If several surviving interventions have identical signatures, Counterproof reports them as unresolved and asks for a new case where their predictions differ.

It does not manufacture a winner.

## Real subprocess replay

The runner executes real commands and records:

- argv;
- return code;
- duration;
- stdout;
- stderr;
- timeout;
- baseline score;
- candidate score;
- delta;
- verdict.

Current score contract:

```text
exit 0      -> 1.0
non-zero    -> 0.0
timeout     -> infra_error
```

This deliberately works with any harness that can be expressed as a command: pytest, Playwright, simulators, benchmarks, service checks, or agent evaluators.

## Promotion gate

The current automatic gate requires:

```text
valid replay evidence exists
AND explicit replay failures == 0
AND mean delta > 0
AND regressions == 0
AND risk_flags == []
```

This is an inspectable v0.1 gate, not a statistically calibrated production rollout policy.

## Behavior Proof Sheet

The browser UI uses two complementary interactions:

```text
CAUSE LENS
  ├── TEST THIS CAUSE
  │      ↓
  │   worldline fork
  │
  └── COMPARE ALL CAUSES
         ↓
      signature matrix
         ↓
   relative survivor state
```

The UI is exercised in Chromium CI.

Displayed UI outcome matrices are fixtures. Real multi-intervention execution is the CLI path.

## What is not implemented

The current branch does **not** claim:

- live GitHub / Claude / Codex / LangGraph trace adapters;
- automatic mutation construction for arbitrary agents;
- learned or unique causal inference;
- automatic discriminating-case synthesis;
- arbitrary world snapshot / restore;
- generic runtime rollback;
- merge-to-promote / revert-to-rollback GitHub automation;
- shadow / canary rollout;
- capability split / merge / decay / retire.

## CI contract

The repository currently tests:

- Python 3.10 / 3.11 / 3.12;
- Ruff;
- packet/model integrity;
- JSON / JSONL trace compilation;
- Probe Contracts;
- real subprocess replay;
- unique-survivor discrimination;
- multiple-survivor ambiguity;
- no-survivor behavior;
- incomplete evidence -> inconclusive;
- guarded `counterproof evolve` selection;
- clean wheel installation;
- packaged CLI from outside the checkout;
- packaged playground;
- Chromium Compare Causes / Proof / Accept / Rollback;
- capability truth-table synchronization.

## Target architecture

The long-term target is still larger:

```text
REALITY
  ↓
live trace capture
  ↓
causal candidate generation
  ↓
automatic discriminating probe synthesis
  ↓
controlled world forks
  ↓
Behavior Proof
  ↓
review / Evolution PR
  ↓
shadow / canary
  ↓
promote / rollback
  ↓
capability lifecycle
```

Only the parts marked **tested** by `counterproof audit` should be treated as implemented.

## Research question

> **Can an agent distinguish competing explanations for its own failure, change only the implicated capability, show executable evidence that the intervention helps, avoid unrelated regressions, and remain reviewable and reversible?**

Counterproof does not claim the full answer. It is making that question increasingly testable.
