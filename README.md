# EvoPR · SkillFactory

<div align="center">

## **Your agent changed. Show the proof.**

**Behavior-change review for self-improving agents.**

[![CI](https://github.com/hippoley/SkillFactory/actions/workflows/ci.yml/badge.svg)](https://github.com/hippoley/SkillFactory/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

</div>

---

Agents are getting better at changing prompts, skills, policies and tools.

The uncomfortable question is no longer:

> Can the agent learn?

It is:

> **What exactly changed, what evidence supports it, what regressed, and can I reject it before it becomes permanent?**

EvoPR explores a Git-like review contract for agent behavior.

```text
raw trace
  ↓
Decision Capsule + Outcome Receipt
  ↓
evidence extraction
  ↓
competing hypotheses
  ↓
falsifiable Probe Contracts
  ↓
SAME cases × MULTIPLE interventions
  ↓
survivor / falsified / ambiguous
  ↓
guarded mutation selection
  ↓
Behavior Proof
  ↓
PROMOTE / HOLD / REJECT
```

## What is real today

This repository is an **early executable prototype**, not a finished self-evolving runtime.

The following paths are exercised in CI:

```text
generic JSON / JSONL trace ingest TESTED
Trace → Evolution Packet          TESTED
Probe Contracts                   TESTED
Active multi-intervention compare TESTED
Trace → discriminate → selection  TESTED
Trace → replay → Behavior Proof   TESTED
Promotion gate                    TESTED
Behavior PR Markdown renderer     TESTED
command-based baseline replay     TESTED
clean wheel install               TESTED
interactive browser flow          TESTED UI / FIXTURE DATA
```

These are **not implemented yet**:

```text
live GitHub / framework trace adapters
automatic intervention synthesis
learned / unique causal attribution
captured world-state forks
automatic mutation application to every surface
GitHub PR open / merge / revert automation
shadow / canary rollout
automatic runtime rollback
```

Run the truth table yourself:

```bash
evopr audit
```

EvoPR intentionally exposes its limitations instead of turning roadmap items into product claims.

---

# 60-second run

```bash
git clone -b feat/evopr-evolution-runtime https://github.com/hippoley/SkillFactory.git
cd SkillFactory
pip install -e .

# Raw trace → competing interventions → guarded selection → Behavior Proof
evopr evolve examples/traces/tenant_failure.json \
  --experiment-manifest examples/discrimination_suite.json \
  --surface policy \
  --surface skill \
  --surface prompt \
  --out EVOLUTION_REVIEW.md \
  --packet-out EVOLVED_PACKET.json

# Inspect the project's own capability truth table
evopr audit

# Open the interactive Behavior Proof Sheet
evopr demo
# http://127.0.0.1:8765
```

The trace compiler extracts the last relevant decision before a negative outcome, builds a Decision Capsule and Outcome Receipt, turns corrections/verifier results into evidence, ranks candidate mutation surfaces, and creates a falsifiable Probe Contract for each hypothesis.

Then `evopr evolve` runs the **same baseline cases against multiple executable interventions**. A candidate can be:

```text
SURVIVED      all required cases ran; failure improved; no regression
FALSIFIED     an explicit failure or regression was observed
INCONCLUSIVE  missing / timed-out evidence, or no useful improvement
```

EvoPR automatically selects a mutation only when exactly one tested intervention survives. If multiple interventions survive, it leaves `selected_candidate_id` empty rather than inventing certainty.

That still does **not** establish unique causal truth. It establishes relative support among the interventions and cases actually tested.

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

EvoPR asks:

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
evopr ingest examples/traces/tenant_failure.json --out EVOLUTION_PACKET.json
~~~

Or go end to end:

~~~bash
evopr prove examples/traces/tenant_failure.json \
  --replay-manifest examples/replay_suite.json \
  --surface policy \
  --out EVOLUTION_PR.md
~~~

If `--surface` is omitted, EvoPR tests the top heuristic candidate and labels the report accordingly. Replay evidence can support or reject that mutation, but it still does not establish unique causal truth.

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

The key difference from a single trajectory-to-skill pass is that EvoPR can compare **several explanations under the same cases**.

```bash
evopr discriminate examples/traces/tenant_failure.json \
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
    "policy": ["python", "eval.py", "policy", "cross-tenant-attack-07"],
    "skill": ["python", "eval.py", "skill", "cross-tenant-attack-07"],
    "prompt": ["python", "eval.py", "prompt", "cross-tenant-attack-07"]
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

If two surviving variants have identical signatures, EvoPR reports the pair as unresolved and asks for a new case where their predictions differ. It does not manufacture a winner.

A missing variant, timeout, or infrastructure error makes that intervention **inconclusive**, not silently promotable.

---

# Real replay: smallest useful adapter

EvoPR v0.1 uses a deliberately boring integration contract: commands.

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
evopr replay replay_suite.json --out results.json
```

Exit code `0` is currently scored as pass (`1.0`), non-zero as fail (`0.0`). Timeout is classified as `infra_error`, not silently counted as a behavioral regression.

That means you can connect EvoPR to:

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

EvoPR now supports two entry points:

1. an explicit Evolution Packet when you already know the review structure;
2. a generic JSON / JSONL event trace that EvoPR compiles into a packet.

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

That means EvoPR can **describe and review** these mutation types today.

It does **not yet know how to automatically apply every one of them to an arbitrary live agent**. That distinction matters.

---

# Behavior PR

```bash
evopr build examples/evolution_pr.json --out EVOLUTION_PR.md
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

See [examples/EVOLUTION_PR.md](examples/EVOLUTION_PR.md).

---

# Capability truth table

| Capability | Status | What is actually proven |
|---|---|---|
| Evolution Packet model | **TESTED** | Packet integrity, hypothesis/candidate/probe references validated |
| Generic JSON / JSONL trace ingestion | **TESTED** | Raw traces compile into evidence-backed packets |
| Probe Contracts | **TESTED** | Each heuristic hypothesis gets intervention/support/falsifier/holdout guidance |
| Command replay | **TESTED** | Real baseline/candidate subprocesses execute in CI |
| Active discrimination | **TESTED** | Same cases run across multiple interventions; survivor/falsified/ambiguity states tested |
| Guarded `evopr evolve` | **TESTED** | Only a unique survivor is automatically selected; ambiguity remains unselected |
| Behavior PR renderer | **TESTED** | Measured evidence and provenance render into review artifacts |
| Clean install | **TESTED** | Wheel installs in a new venv and the CLI + packaged UI run outside the checkout |
| Multiple mutation surfaces | **PARTIAL** | Data/review contract exists; generic live mutation executors do not |
| Heuristic causal proposals | **PARTIAL** | Deterministic ranking exists; it is not learned or unique causal inference |
| Evidence semantics | **PARTIAL** | Types/confidence exist; calibrated weighting is not implemented |
| Runtime rollback | **PARTIAL** | Rollback references exist; no general rollback executor |
| Interactive playground | **DEMO** | Browser behavior is tested; displayed outcome matrix is fixture data |
| Live GitHub / agent-framework adapters | **PLANNED** | No automatic external trace ingestion yet |
| Automatic intervention / test synthesis | **PLANNED** | Experiment commands and discriminating cases are still supplied by users |
| Captured counterfactual worlds | **PLANNED** | No arbitrary world snapshot / restore |
| GitHub merge-to-promote / revert automation | **PLANNED** | Not wired yet |
| Shadow / canary rollout | **PLANNED** | Not implemented |

The same truth table is generated by the runtime:

```bash
evopr audit --json-output
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
   - `evopr ingest`
   - `evopr prove`
   - `evopr discriminate`
   - `evopr evolve`
   - `evopr demo`
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

EvoPR is moving toward:

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
- guarded unique-survivor selection via `evopr evolve`
- conservative promotion gate
- honest capability audit
- worldline + Compare Causes playground

## v0.2 — Replay adapters

Make replay richer without tying EvoPR to one agent stack:

- Python callable adapter
- HTTP/service adapter
- pytest adapter
- agent-harness adapter contract
- structured scoring beyond exit code

## v0.3 — Probe synthesis

- automatic intervention construction
- automatic discriminating-case generation
- pairwise information-gain probe selection
- calibrated evidence-weight updates

## v0.4 — Git-native evolution

- ingest PR review + CI corrections
- create Evolution Packet automatically
- open Behavior PR
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

EvoPR does not claim to have solved that question.

It is building the testable machinery needed to answer it.

---

# Repository map

```text
skill_factory/
└── evolution/
    ├── models.py
    ├── replay.py
    ├── discriminate.py
    ├── trace.py
    ├── report.py
    ├── capabilities.py
    └── cli.py

examples/
├── evolution_pr.json
├── EVOLUTION_PR.md
├── replay_suite.json
├── discrimination_suite.json
├── traces/
│   ├── tenant_failure.json
│   └── homeai_correction.json
└── replay/
    ├── tenant_policy.py
    └── tenant_discrimination.py

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
    └── evopr_smoke.mjs
```

---

<div align="center">

### **Claim nothing you can’t replay.**

EvoPR · Behavior proof for self-changing agents.

</div>
