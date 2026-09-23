# Counterproof

<div align="center">

## **Your agent says it fixed the bug. Prove it.**

**Behavioral proof for agent-generated pull requests and self-modifying AI systems.**

[![CI](https://github.com/hippoley/SkillFactory/actions/workflows/ci.yml/badge.svg)](https://github.com/hippoley/SkillFactory/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

</div>

---

A green CI run proves one thing:

> the code passes **now**.

It does **not** prove that the agent's new test would have caught the bug before the fix.

Counterproof starts there.

## Regression Witness

**Take the tests changed by the PR. Run them on the PR. Then replay the exact same tests against the pre-change code.**

```text
PR tests on HEAD
      ↓
     PASS
      ↓
same tests on BASE code
      ↓
     FAIL
      ↓
REGRESSION WITNESSED
```

That gives the reviewer something stronger than:

> “the agent says the bug is fixed.”

It gives:

> **this exact test passes after the fix and fails before it.**

### GitHub Action

```yaml
name: Counterproof

on:
  pull_request:

permissions:
  contents: read
  pull-requests: write

jobs:
  witness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      # Install your project dependencies before this step.
      - uses: hippoley/SkillFactory/actions/witness@main
        with:
          test-command: "python -m pytest -q {tests}"
          require-witness: "true"
          require-clean-integrity: "true"
```

Counterproof automatically:

```text
1. finds tests added or modified by the PR
2. runs them on the PR head
3. creates a detached worktree at the base commit
4. overlays the PR's changed tests onto the old code
5. runs the exact same tests again
6. emits WITNESSED / NOT WITNESSED / HEAD FAILING / INCONCLUSIVE
7. updates one sticky PR comment instead of spamming the thread
```

It also checks whether the PR changed the **judge** that produced the evidence:

```text
deleted test                     → review
new skip / xfail                 → review
continue-on-error: true          → review
pytest || true                   → review
pull_request trigger removed     → review
workflow/test config changed     → surface explicitly
```

A fix and its proof can live in the same PR. Counterproof does not call that malicious; it makes the dependency visible so a reviewer knows the evidence is no longer independent.


Example proof:

```text
COUNTERPROOF · REGRESSION WITNESS

WITNESSED

PR head                  PASS
Base code + PR tests     FAIL

tests/test_tenant_scope.py

The same changed test fails before the fix and passes after it.
```

**Green CI says it passes now. Counterproof proves whether the test failed before the fix.**

### Works with your existing test runner

```text
pytest       python -m pytest -q {tests}
Jest         npx jest {tests} --runInBand
Vitest       npx vitest run {tests}
Playwright   npx playwright test {tests}
RSpec        bundle exec rspec {tests}
Go           go test ./...
custom       ./scripts/regression-check
```

Use `{tests}` when the runner accepts explicit changed-test paths. Omit it when your runner should execute the whole suite; Counterproof still overlays the PR's changed tests onto the base worktree before replay.

Counterproof currently auto-detects common Python, JavaScript/TypeScript, Go, Java, Kotlin and Ruby test filename conventions.

---

## Why this exists

Agent PR volume is increasing faster than human review capacity. The hard part is no longer generating more code; it is deciding which agent changes deserve trust.

Counterproof does **not** try to become another AI reviewer that comments on style, naming, or likely bugs.

It focuses on a narrower question:

> **What observable evidence would make this change deserve to survive?**

Regression Witness is the fastest entry point.

The deeper runtime goes further:

```text
failure
  ↓
competing explanations
  ↓
pre-registered predictions
  ↓
same cases × multiple interventions
  ↓
falsification
  ↓
next discriminating probe
  ↓
reviewed behavior change
  ↓
fingerprinted Proof Receipt
```

## Why this is not Trace → Skill

Trajectory distillation asks:

> What lesson should the agent remember?

Counterproof asks:

> **Which explanation survives an experiment, and what evidence earns the right to change behavior?**

| | Trace → Skill | Counterproof |
|---|---|---|
| Failure handling | summarize a lesson | propose competing hypotheses |
| Causality | often implicit | intervention + falsifier |
| Evaluation | test one candidate | compare multiple interventions on the same cases |
| Predictions | usually after the run | pre-registered before execution |
| Negative outcomes | failure = bad | diagnostic FAIL can be evidence |
| Ambiguity | often pick best guess | remain unselected and design the next probe |
| Evidence | score / reflection | structured metrics, observations, artifacts |
| Reproducibility | run log | source-fingerprinted Proof Receipt |

## 60-second run

```bash
git clone -b feat/evopr-evolution-runtime https://github.com/hippoley/SkillFactory.git
cd SkillFactory
pip install -e .

counterproof evolve examples/traces/tenant_failure.json \
  --experiment-manifest examples/discrimination_suite.json \
  --surface policy \
  --surface skill \
  --surface prompt \
  --out BEHAVIOR_PROOF.md \
  --receipt-out PROOF_RECEIPT.json

counterproof verify-receipt PROOF_RECEIPT.json

counterproof demo
# http://127.0.0.1:8765
```

### The result is allowed to say “I still don’t know.”

Counterproof has explicit selection states:

```text
unique-survivor      one eligible intervention survived
ambiguous            multiple eligible interventions survived
prediction-blocked   runtime looked good, but the hypothesis contradicted its own prediction
no-survivor          no tested explanation survived
diagnostic-only      experiment generated causal evidence but cannot promote a mutation
```

No winner is better than a fake winner.

## What is actually tested

The current branch is an executable research prototype. CI exercises:

```text
JSON / JSONL trace ingestion                 TESTED
Decision Capsule + Outcome Receipt           TESTED
falsifiable Probe Contracts                  TESTED
pre-registered predictions                   TESTED
multi-intervention discrimination            TESTED
fitness vs diagnostic case roles             TESTED
ambiguity → Next Probe Plan                  TESTED
draft probe scaffold                         TESTED
reviewed adapter binding                     TESTED
Regression Witness                           TESTED
Proof Integrity Guard                        TESTED
structured COUNTERPROOF_RESULT json-v1       TESTED
continuous scores + metrics + observations   TESTED
Behavior Proof                               TESTED
Proof Receipt v2 + drift detection            TESTED
clean wheel install                          TESTED
Chromium interaction flow                    TESTED
```

Run the repository's own truth table:

```bash
counterproof audit
```

Still not implemented:

```text
live Claude / Codex / LangGraph / GitHub trace adapters
automatic trustworthy domain-test synthesis
learned or unique causal attribution
arbitrary world snapshot / restore
generic runtime mutation executors
shadow / canary rollout
automatic runtime rollback
```

Counterproof deliberately separates **what is tested** from **what is still a research target**.

## Name and compatibility

**Counterproof** is the project name and primary CLI from v0.2.

For existing integrations, these remain available:

```text
counterproof   primary CLI
evopr          legacy CLI alias
skill-factory  legacy skill-generation CLI
```

The Python implementation package remains `skill_factory` for source compatibility during the rename.

---

# The interface is not a dashboard

The playground is designed as a **Behavior Proof Sheet**.

One case becomes one experiment:

```text
INCIDENT
   ↓
CAUSE LENS
   ├── TEST THIS CAUSE
   └── COMPARE ALL CAUSES
             ↓
      intervention matrix
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

The main visual primitive is a **worldline split**.

Git answers:

> Which bytes changed?

Counterproof asks:

> **In the same case, where did behavior diverge?**

The browser interaction itself is exercised in headless Chromium in CI. The replay values shown in that browser demo are fixtures; real command replay lives in the CLI.

---

# Raw trace → proof

A minimal raw trace looks like:

~~~json
{
  "trace_id": "tenant-scope-418",
  "agent": "coding-agent",
  "events": [
    {
      "type": "decision",
      "world_state": {"tenant_scope": "provisional"},
      "selected_action": "query_database",
      "guards": {"tenant_scope_validated": false}
    },
    {
      "type": "human_correction",
      "text": "Validate tenant scope before database access.",
      "surface_hint": "policy"
    },
    {
      "type": "test_failure",
      "text": "Cross-tenant regression reproduced."
    }
  ]
}
~~~

Compile without running anything:

~~~bash
counterproof ingest examples/traces/tenant_failure.json --out EVOLUTION_PACKET.json
~~~

Or go end to end:

~~~bash
counterproof prove examples/traces/tenant_failure.json \
  --replay-manifest examples/replay_suite.json \
  --surface policy \
  --out BEHAVIOR_PROOF.md
~~~

If `--surface` is omitted, Counterproof tests the top heuristic candidate and labels the report accordingly. Replay evidence can support or reject that mutation, but it still does not establish unique causal truth.

Each generated hypothesis also gets a **Probe Contract**:

~~~text
INTERVENTION
change only one behavior surface

SUPPORTS IF
the original failure disappears

FALSIFIED IF
the failure survives, or an unrelated case regresses

HOLDOUT
a nearby case that must remain unchanged
~~~

---

# Active discrimination

The key difference from a single trajectory-to-skill pass is that Counterproof can compare **several explanations under the same cases** and register their expected outcomes **before** execution.

```bash
counterproof discriminate examples/traces/tenant_failure.json \
  --experiment-manifest examples/discrimination_suite.json \
  --surface policy \
  --surface skill \
  --surface prompt \
  --out DISCRIMINATION.md \
  --json-out DISCRIMINATION.json
```

An experiment manifest supplies one baseline command and multiple intervention commands per case:

```json
{
  "case_id": "cross-tenant-attack-07",
  "baseline": ["python", "eval.py", "baseline", "cross-tenant-attack-07"],
  "variants": {
    "policy": {
      "argv": ["python", "eval.py", "policy", "cross-tenant-attack-07"],
      "expect": "pass"
    },
    "skill": {
      "argv": ["python", "eval.py", "skill", "cross-tenant-attack-07"],
      "expect": "pass"
    },
    "prompt": {
      "argv": ["python", "eval.py", "prompt", "cross-tenant-attack-07"],
      "expect": "pass"
    }
  }
}
```

For the included tenant example the behavior signatures are:

```text
                    original   security holdout   normal holdout
policy                 PASS          PASS              PASS
skill                  PASS          FAIL              PASS
prompt                 PASS          FAIL              PASS
```

The security holdout is therefore a **diagnostic case**: it separates the policy intervention from the alternatives.

If two surviving variants have identical signatures, Counterproof reports the pair as unresolved and asks for a new case where their predictions differ. It does not manufacture a winner.

A missing variant, timeout, or infrastructure error makes that intervention **inconclusive**, not silently promotable.

---

## Fitness cases vs diagnostic probes

Not every FAIL means regression.

Counterproof now distinguishes:

~~~text
role = fitness
  used for behavior quality / regression / promotion gates

role = diagnostic
  used to test competing predictions
  may intentionally produce a pre-registered FAIL
  never promotes a mutation by itself
~~~

Generated crossed probes are always emitted as:

~~~json
{
  "suite": "discriminating-probe",
  "role": "diagnostic"
}
~~~

So this result:

~~~text
policy diagnostic case A -> PASS
policy diagnostic case B -> FAIL
~~~

can be **prediction evidence** without being counted as a product regression.

A diagnostic-only experiment returns:

~~~text
selection_state = diagnostic-only
selected_candidate_id = null
~~~

That separation matters: causal evidence and release fitness are different questions.

---

# Review before execution

Generated experiment scaffolds start as `status=draft` and cannot run.

After inspecting the case semantics, bind a real adapter explicitly:

~~~bash
counterproof bind-probe-adapter NEXT_EXPERIMENT.json \
  --adapter python \
  --adapter ./my_probe_adapter.py \
  --reviewed-by alice \
  --review-note "Checked intervention isolation and case assumptions." \
  --out READY_EXPERIMENT.json
~~~

The ready manifest records the reviewer, note and approval decision.

This authorizes **execution plumbing only**. It does not certify that the adapter faithfully models the target domain; the subsequent predictions and observed evidence still have to survive the experiment.

---

# Structured Probe Results

Exit codes are useful for process control, but too weak for real agent evaluation.

Counterproof supports:

~~~json
{
  "result_protocol": "json-v1"
}
~~~

Under `json-v1`, the adapter process should exit `0` when the **adapter executed successfully** and print one final structured line:

~~~text
COUNTERPROOF_RESULT={"verdict":"pass","score":0.82,"metrics":{"latency_ms":17},"observations":["target stayed stable"],"artifacts":["trace://run/42"]}
~~~

The semantics are deliberately split:

~~~text
process return code
  -> did the adapter / harness execute?

COUNTERPROOF_RESULT.verdict
  -> did the tested behavior pass?

COUNTERPROOF_RESULT.score
  -> continuous behavior quality in [0, 1]
~~~

So all processes can exit `0` while the behavioral matrix still contains PASS and FAIL.

Supported fields:

~~~text
verdict       pass | fail
score         0.0 .. 1.0
metrics       JSON object
observations  string[]
artifacts     string[] references
~~~

If a `json-v1` adapter exits non-zero, times out, emits malformed JSON, or omits `COUNTERPROOF_RESULT`, Counterproof records `infra_error` rather than silently converting it to behavioral failure or success.

The included structured fixture proves that a case can be:

~~~text
verdict = PASS
score   = 0.82
signature = P
~~~

A perfect score is not required for PASS.

---

# One adapter, many probes

You do not have to repeat a command for every case × intervention.

A discrimination manifest can define one reusable adapter:

~~~json
{
  "status": "ready",
  "root": "..",
  "adapter": ["python", "my_probe_adapter.py"],
  "cases": [
    {
      "case_id": "failure-418",
      "payload": {
        "tenant_scope": "provisional"
      },
      "variants": {
        "policy": {"expect": "pass"},
        "skill": {"expect": "pass"}
      }
    }
  ]
}
~~~

Counterproof invokes the same adapter with:

~~~text
COUNTERPROOF_CASE_ID
COUNTERPROOF_VARIANT
COUNTERPROOF_CASE_JSON
~~~

So your adapter only needs to answer:

> Given this case payload and this intervention surface, does the target agent behavior pass or fail?

The included example:

~~~bash
counterproof discriminate examples/traces/tenant_failure.json \
  --experiment-manifest examples/adapter_discrimination_suite.json \
  --surface policy \
  --surface skill \
  --surface prompt
~~~

uses a single env-driven Python adapter across the full matrix.

---

# Ambiguity → draft executable scaffold

When Counterproof cannot distinguish two surviving hypotheses, `counterproof evolve` can emit both the prose plan and a machine-readable next experiment:

~~~bash
counterproof evolve examples/traces/tenant_failure.json \
  --experiment-manifest examples/ambiguous_discrimination_suite.json \
  --surface policy \
  --surface skill \
  --probe-plan-out NEXT_PROBE.md \
  --probe-scaffold-out NEXT_EXPERIMENT.json
~~~

The generated scaffold contains two crossed cases:

~~~text
CASE A
isolate policy lever
policy expects PASS
skill expects FAIL

CASE B
isolate skill lever
policy expects FAIL
skill expects PASS
~~~

But it is intentionally emitted as:

~~~json
{
  "status": "draft",
  "adapter": ["TODO_REPLACE_WITH_ADAPTER"],
  "review_required": true
}
~~~

Counterproof refuses to execute a draft scaffold, and it also refuses a `ready` scaffold that still contains the adapter placeholder.

This is deliberate: **automatic experiment design is not the same thing as a trustworthy executable test.**

---

# Proof Receipts: evidence should expire when inputs drift

A Behavior Proof should not stay trustworthy after its source inputs silently change.

Add:

```bash
counterproof evolve examples/traces/tenant_failure.json \
  --experiment-manifest examples/discrimination_suite.json \
  --surface policy \
  --surface skill \
  --surface prompt \
  --out EVOLUTION_REVIEW.md \
  --receipt-out PROOF_RECEIPT.json
```

Proof Receipt v2 freezes:

```text
trace SHA256
experiment-manifest SHA256
tested surfaces
observed behavior signatures
pre-registered expected signatures
prediction status
runtime status
continuous behavior scores
fitness / diagnostic case roles
structured metrics
observations
artifact references
eligible survivors
selected candidate
diagnostic cases
```

Later:

```bash
counterproof verify-receipt PROOF_RECEIPT.json
```

If either source file changed, verification fails.

You can also verify the same receipt against files moved to a different path:

```bash
counterproof verify-receipt PROOF_RECEIPT.json \
  --trace ./exported/trace.json \
  --experiment-manifest ./exported/experiment.json
```

The current receipt fingerprints source artifacts. It does **not** yet fingerprint a full container image, dependency lock, model version or external service state.

---

# Why pre-register predictions?

Without a prediction contract, it is easy to run an intervention first and invent the explanation afterward.

Counterproof therefore tracks two different judgments:

```text
RUNTIME STATUS
survived / falsified / inconclusive

PREDICTION STATUS
supported / contradicted / partial / unregistered
```

Example:

```text
policy expected  PASS PASS PASS
policy observed  PASS PASS PASS
→ prediction supported

skill expected   PASS PASS PASS
skill observed   PASS FAIL PASS
→ prediction contradicted
```

If any experiment uses pre-registered predictions, automatic selection requires the surviving candidate to have a fully **supported** prediction contract. A runtime PASS is not enough when the hypothesis predicted something else.

This still does not prove unique causality. It prevents one common failure mode: **post-hoc storytelling**.

---

# When the evidence is ambiguous

Counterproof does not force a winner when two interventions produce the same behavior signature.

Example:

```text
                    failure      normal holdout
policy                 PASS            PASS
skill                  PASS            PASS
```

This is not enough evidence to choose between them.

Run:

```bash
counterproof evolve examples/traces/tenant_failure.json \
  --experiment-manifest examples/ambiguous_discrimination_suite.json \
  --surface policy \
  --surface skill \
  --out AMBIGUOUS_REVIEW.md \
  --packet-out AMBIGUOUS_PACKET.json \
  --probe-plan-out NEXT_PROBE.md
```

Counterproof leaves:

```json
{
  "selected_candidate_id": null,
  "metadata": {
    "discrimination_result": "ambiguous"
  }
}
```

and generates a **Next Probe Plan**.

For `policy vs skill`, the plan says roughly:

```text
KEEP FIXED
the recorded failure context and unrelated runtime surfaces

VARY INDEPENDENTLY
1. execution precondition / commit gate
2. learned instruction / demonstrations

POLICY PREDICTS
the hard guard alone changes whether the action may commit

SKILL PREDICTS
interpretation changes before execution even with policy unchanged

FALSIFY
if an isolated lever changes but its predicted behavior does not
```

This is automatic **experiment design**, not automatic domain test generation. A human or adapter still has to instantiate the proposed probe in the target environment.

---

# Real replay: smallest useful adapter

Counterproof v0.1 uses a deliberately boring integration contract: commands.

```json
{
  "cases": [
    {
      "case_id": "failure-418",
      "suite": "regression",
      "baseline": [
        "python",
        "my_eval.py",
        "baseline",
        "failure-418"
      ],
      "candidate": [
        "python",
        "my_eval.py",
        "candidate",
        "failure-418"
      ]
    }
  ]
}
```

Then:

```bash
counterproof replay replay_suite.json --out results.json
```

With the legacy `exit-code` protocol, exit `0` maps to pass (`1.0`) and non-zero maps to fail (`0.0`). With `json-v1`, process execution is separated from behavioral verdict and continuous score. Timeout remains `infra_error`.

That means you can connect Counterproof to:

- pytest
- Playwright
- a simulator
- an agent benchmark
- a shell workflow
- a service integration test
- your own evaluator executable

without waiting for a framework-specific adapter.

---

# Promotion gate

The current default gate is intentionally inspectable:

```text
at least one valid replay
AND explicit replay failures == 0
AND mean delta > 0
AND regressions == 0
AND risk_flags == []
```

A timeout / infrastructure error is excluded from behavioral regression counting.

This gate is simple. It is **not** presented as a statistically sufficient rollout policy.

---

# Trace compiler and Evolution Packet

Counterproof now supports two entry points:

1. an explicit Evolution Packet when you already know the review structure;
2. a generic JSON / JSONL event trace that Counterproof compiles into a packet.

The compiler proposes causal surfaces with explicit uncertainty. It does **not** claim that heuristic ranking proves a unique root cause.

```json
{
  "packet_id": "evo-tenant-scope-001",
  "agent": "coding-agent",
  "failure_summary": "Agent queried tenant data too early.",
  "decision_capsule": "...",
  "outcome_receipt": "...",
  "evidence": [],
  "hypotheses": [],
  "candidates": [],
  "selected_candidate_id": "c-policy"
}
```

The model supports candidate surfaces:

```text
skill
prompt
policy
router
memory
tool
eval
```

That means Counterproof can **describe and review** these mutation types today.

It does **not yet know how to automatically apply every one of them to an arbitrary live agent**. That distinction matters.

---

# Behavior Proof

```bash
counterproof build examples/evolution_pr.json --out BEHAVIOR_PROOF.md
```

The generated artifact contains:

- failure summary
- Decision Capsule
- Outcome Receipt
- competing hypotheses
- candidate mutations
- replay matrix
- Behavior Diff
- risk flags
- activation scope
- rollback reference
- promotion result

See [examples/BEHAVIOR_PROOF.md](examples/BEHAVIOR_PROOF.md).

---

# Capability truth table

| Capability | Status | What is actually proven |
|---|---|---|
| Evolution Packet model | **TESTED** | Packet integrity, hypothesis/candidate/probe references validated |
| Generic JSON / JSONL trace ingestion | **TESTED** | Raw traces compile into evidence-backed packets |
| Probe Contracts | **TESTED** | Each heuristic hypothesis gets intervention/support/falsifier/holdout guidance |
| Command replay | **TESTED** | Real baseline/candidate subprocesses execute in CI |
| Pre-registered predictions | **TESTED** | Expected PASS/FAIL outcomes are recorded before execution; contradicted predictions can block selection |
| Active discrimination | **TESTED** | Same cases run across multiple interventions; survivor/falsified/ambiguity states tested |
| Guarded `counterproof evolve` | **TESTED** | Only a unique survivor is automatically selected; ambiguity remains unselected |
| Structured Probe Result json-v1 | **TESTED** | Process execution is separated from behavioral verdict; adapters can emit continuous scores, metrics, observations and artifact refs |
| Fitness vs diagnostic roles | **TESTED** | Diagnostic expected FAILs are prediction evidence, not fitness regressions; diagnostic-only experiments cannot promote |
| Reviewed adapter binding | **TESTED** | Draft scaffold requires reviewer + note + real adapter before becoming ready |
| Probe Adapter protocol | **TESTED** | One adapter argv can execute many cases/variants via COUNTERPROOF_CASE_ID / COUNTERPROOF_VARIANT / COUNTERPROOF_CASE_JSON |
| Draft probe scaffold | **TESTED** | Ambiguity can emit crossed experiment cases with pre-registered predictions; execution is blocked until reviewed |
| Next Probe Planner | **TESTED** | Ambiguous survivor pairs produce controlled-variable, competing-prediction and falsification guidance |
| Behavior Proof renderer | **TESTED** | Measured evidence and provenance render into review artifacts |
| Proof Receipt | **TESTED** | Trace + experiment hashes and observed/expected signatures can be stored and later verified for drift |
| Clean install | **TESTED** | Wheel installs in a new venv and the CLI + packaged UI run outside the checkout |
| Multiple mutation surfaces | **PARTIAL** | Data/review contract exists; generic live mutation executors do not |
| Heuristic causal proposals | **PARTIAL** | Deterministic ranking exists; it is not learned or unique causal inference |
| Evidence semantics | **PARTIAL** | Types/confidence exist; calibrated weighting is not implemented |
| Runtime rollback | **PARTIAL** | Rollback references exist; no general rollback executor |
| Interactive playground | **DEMO** | Browser behavior is tested; displayed outcome matrix is fixture data |
| Live GitHub / agent-framework adapters | **PLANNED** | No automatic external trace ingestion yet |
| Automatic executable probe synthesis | **PLANNED** | Next Probe Plans exist, but adapters still must instantiate executable domain cases |
| Captured counterfactual worlds | **PLANNED** | No arbitrary world snapshot / restore |
| GitHub merge-to-promote / revert automation | **PLANNED** | Not wired yet |
| Shadow / canary rollout | **PLANNED** | Not implemented |

The same truth table is generated by the runtime:

```bash
counterproof audit --json-output
```

---

# What CI actually proves

Every pull request checks:

1. Python 3.10 / 3.11 / 3.12 and Ruff.
2. Unit tests for packet integrity, promotion, replay, trace compilation and Probe Contracts.
3. Unique-survivor, multiple-survivor, no-survivor and incomplete-evidence discrimination cases.
4. Real baseline/candidate subprocess replay.
5. A wheel built and installed into a clean virtualenv.
6. From that clean install, outside the repository:
   - `counterproof ingest`
   - `counterproof prove`
   - `counterproof discriminate`
   - `counterproof evolve`
   - `counterproof bind-probe-adapter`
   - `counterproof verify-receipt`
   - `counterproof demo`
7. Chromium opens the playground and exercises:
   - Compare All Causes,
   - a falsified hypothesis,
   - a surviving hypothesis,
   - accept,
   - rollback.
8. Capability truth-table synchronization.

This proves the **narrow executable loop** above. It does not prove arbitrary third-party agents can already be mutated, deployed and rolled back automatically.

---

# Why this is deeper than trajectory → skill

Trajectory distillation asks:

> What lesson can I extract?

Counterproof is moving toward:

> **What was the failure mechanism, what is the smallest intervention, and what evidence earns deployment?**

The target architecture is:

```text
REALITY
  ↓
Decision Capsule
  ↓
Outcome Receipt
  ↓
Evidence
  ↓
competing causal hypotheses
  ↓
minimal mutations
  ↓
real replay / holdout
  ↓
Behavior Proof
  ↓
review
  ↓
deployment policy
```

Only the bolded/tested subset in the capability table is available today.

---

# Roadmap

## v0.1 — Behavior proof + active discrimination

Current branch.

- raw JSON / JSONL trace compiler
- explicit Evolution Packet
- falsifiable Probe Contracts
- deterministic command replay
- multi-intervention discrimination matrix
- guarded unique-survivor selection via `counterproof evolve`
- conservative promotion gate
- honest capability audit
- worldline + Compare Causes playground

## v0.2 — Replay adapters

Make replay richer without tying Counterproof to one agent stack:

- Python callable adapter
- HTTP/service adapter
- pytest adapter
- agent-harness adapter contract
- structured scoring beyond exit code

## v0.3 — Probe synthesis

- automatic intervention construction
- automatic discriminating-case generation
- executable Probe Plan adapters
- pairwise information-gain probe selection
- automatic discriminating-case instantiation
- calibrated evidence-weight updates

## v0.4 — Git-native evolution

- ingest PR review + CI corrections
- create Evolution Packet automatically
- open Behavior Proof
- merge-to-promote
- revert-to-rollback

## v0.5 — Online evolution

- shadow routing
- canary traffic
- capability lifecycle
- automatic rollback policy

---

# Research question

> **Can an agent change exactly the capability that caused a failure, demonstrate that the intervention improves behavior without unrelated regressions, and remain reviewable and reversible?**

Counterproof does not claim to have solved that question.

It is building the testable machinery needed to answer it.

---

# Repository map

```text
skill_factory/
└── evolution/
    ├── models.py
    ├── replay.py
    ├── discriminate.py
    ├── adapter_binding.py
    ├── probe_planner.py
    ├── receipt.py
    ├── trace.py
    ├── report.py
    ├── capabilities.py
    └── cli.py

examples/
├── evolution_pr.json
├── BEHAVIOR_PROOF.md
├── replay_suite.json
├── discrimination_suite.json
├── ambiguous_discrimination_suite.json
├── adapter_discrimination_suite.json
├── structured_discrimination_suite.json
├── traces/
│   ├── tenant_failure.json
│   └── homeai_correction.json
└── replay/
    ├── tenant_policy.py
    ├── tenant_discrimination.py
    ├── env_probe_adapter.py
    ├── cross_probe_adapter.py
    └── structured_probe_adapter.py

site/
├── index.html
├── app.js
├── styles.css
└── data/
    ├── evolution_cases.json
    └── capabilities.json

tests/
├── unit/
│   └── test_evolution_report.py
└── browser/
    └── counterproof_smoke.mjs
```

---

<div align="center">

### **Claim nothing you can’t replay.**

Counterproof · Falsifiable change control for self-modifying agents.

</div>
