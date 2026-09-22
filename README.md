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
failure
  ↓
evidence + decision context
  ↓
candidate mutation
  ↓
baseline / candidate replay
  ↓
Behavior Proof
  ↓
PROMOTE / HOLD / REJECT
```

## What is real today

This repository is an **early executable prototype**, not a finished self-evolving runtime.

The following paths are exercised in CI:

```text
Evolution Packet                  TESTED
Promotion gate                    TESTED
Behavior PR Markdown renderer     TESTED
evopr build                       TESTED
command-based baseline replay     TESTED
clean wheel install               TESTED
interactive browser flow          TESTED UI / FIXTURE DATA
```

These are **not implemented yet**:

```text
automatic trace / PR ingestion
automatic causal-hypothesis generation
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

# 1. Build a review artifact from an explicit Evolution Packet
evopr build examples/evolution_pr.json --out EVOLUTION_PR.md

# 2. Execute REAL baseline/candidate commands
evopr replay examples/replay_suite.json --out REPLAY_RESULTS.json

# 3. Inspect capability status
evopr audit

# 4. Open the interactive Behavior Proof playground
evopr demo
# http://127.0.0.1:8765
```

The command replay is not a mocked UI animation. EvoPR launches the baseline and candidate processes, records return codes, duration and output, then produces measured replay evidence.

The current example intentionally uses a tiny deterministic fixture so the behavior is reproducible in CI. Your project can replace those commands with its own tests, evaluator, agent harness, simulator or workflow.

---

# The interface is not a dashboard

The playground is designed as a **Behavior Proof Sheet**.

One case becomes one experiment:

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

The main visual primitive is a **worldline split**.

Git answers:

> Which bytes changed?

EvoPR asks:

> **In the same case, where did behavior diverge?**

The browser interaction itself is exercised in headless Chromium in CI. The replay values shown in that browser demo are fixtures; real command replay lives in the CLI.

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
AND mean delta > 0
AND regressions == 0
AND risk_flags == []
```

A timeout / infrastructure error is excluded from behavioral regression counting.

This gate is simple. It is **not** presented as a statistically sufficient rollout policy.

---

# Evolution Packet

Today EvoPR expects an explicit packet rather than pretending it can already infer causality automatically.

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

| Capability | Status | What the status means |
|---|---|---|
| Evolution Packet model | **TESTED** | Constructed and validated in unit tests |
| Promotion gate | **TESTED** | Regression, risk and infra-error behavior are tested |
| Behavior PR renderer | **TESTED** | CLI renders the real example in CI |
| Command replay | **TESTED** | CI starts real baseline/candidate subprocesses |
| Clean install | **TESTED** | CI builds a wheel, installs into a fresh venv, runs the CLI |
| Multiple mutation surfaces | **PARTIAL** | Data contract exists; live mutation executors do not |
| Evidence semantics | **PARTIAL** | Kind/verdict/confidence represented; calibrated weighting not implemented |
| Rollback contract | **PARTIAL** | References are stored/rendered; runtime rollback is not implemented |
| Interactive playground | **DEMO** | UI interaction tested; replay values inside the page are fixture data |
| Automatic trace ingestion | **PLANNED** | Not implemented |
| Automatic causal selector | **PLANNED** | Not implemented |
| Captured counterfactual worlds | **PLANNED** | Not implemented |
| Automatic GitHub change control | **PLANNED** | Not implemented |
| Shadow / canary rollout | **PLANNED** | Not implemented |

The same table is available from the runtime:

```bash
evopr audit --json-output
```

---

# What CI actually proves

Every pull request currently checks:

1. Python 3.10 / 3.11 / 3.12.
2. Ruff.
3. Unit and CLI tests.
4. A measured baseline/candidate replay.
5. The capability truth table.
6. A wheel built from the repository and installed into a clean virtualenv.
7. `evopr build` executed from outside the repository using that installed wheel.
8. The browser JavaScript syntax.
9. A Chromium interaction test that:
   - opens the playground,
   - chooses a bad hypothesis,
   - proves it cannot be promoted,
   - chooses the better fixture hypothesis,
   - runs proof,
   - accepts the mutation,
   - rolls it back.

This does **not** prove that EvoPR can already ingest and evolve arbitrary third-party agents end to end.

It proves the narrower capabilities above.

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

## v0.1 — Evidence packet + real command replay

Current branch.

- explicit Evolution Packet
- Behavior PR
- deterministic command replay
- conservative promotion gate
- honest capability audit
- worldline playground

## v0.2 — Replay adapters

Make replay richer without tying EvoPR to one agent stack:

- Python callable adapter
- HTTP/service adapter
- pytest adapter
- agent-harness adapter contract
- structured scoring beyond exit code

## v0.3 — Causal probes

- Trace → Decision Capsule compiler
- competing failure hypotheses
- discriminating case generation
- evidence-weight updates

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
    ├── report.py
    ├── capabilities.py
    └── cli.py

examples/
├── evolution_pr.json
├── EVOLUTION_PR.md
├── replay_suite.json
└── replay/
    └── tenant_policy.py

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
