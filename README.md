# 🧬 SkillFactory / EvoPR

<div align="center">

## **Self-improving agents need code review too.**

### Your agent can rewrite itself. Make it open a pull request first.

**Evidence-backed · Replay-gated · Reversible · Git-native**

[![CI](https://github.com/hippoley/SkillFactory/actions/workflows/ci.yml/badge.svg)](https://github.com/hippoley/SkillFactory/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

Most self-improving agents can **change themselves**.

Far fewer can answer:

> **Why did this behavior change? What evidence supports it? What else regressed? How do I roll it back?**

**EvoPR** is the evolution layer inside SkillFactory.

It turns a real failure into a reviewable **Behavior PR**:

~~~text
failure
   ↓
Decision Capsule + Outcome Receipt
   ↓
competing causal hypotheses
   ↓
candidate behavior mutations
   ↓
replay + holdout
   ↓
Behavior Diff
   ↓
EVOLUTION PR
   ↓
promote / hold / rollback
~~~

Not another prompt optimizer.  
Not another trajectory summarizer.  
Not another pile of SKILL.md files.

**A change-control system for agent behavior.**

---

# ⚡ 30-second demo

~~~bash
git clone -b feat/evopr-evolution-runtime https://github.com/hippoley/SkillFactory.git
cd SkillFactory

pip install -e .

evopr build examples/evolution_pr.json --out EVOLUTION_PR.md
cat EVOLUTION_PR.md
~~~

The current prototype generates a review artifact like this:

~~~text
EvoPR — evo-tenant-scope-001

FAILURE
Agent queried tenant data before validating tenant scope.

CAUSAL HYPOTHESES
h1  Skill instruction missing        uncertainty 0.32
h2  Policy guard missing             uncertainty 0.12
h3  Router mismatch                  uncertainty 0.78

CANDIDATE MUTATIONS
skill   Teach validation-before-query       +0.500
policy  Enforce tenant validation guard     +0.533  ← selected

BEHAVIOR DIFF

BEFORE
tenant_scope = provisional
selected_action = query_database
effect = DB call allowed

AFTER
tenant_scope = provisional
selected_action = validate_tenant
effect = DB call blocked

REPLAY
original failure       0.0 → 1.0
security holdout       0.4 → 1.0
normal lookup          1.0 → 1.0

REGRESSIONS  0
RISK FLAGS   0

→ ELIGIBLE FOR PROMOTION
~~~

See the committed generated example: [examples/EVOLUTION_PR.md](examples/EVOLUTION_PR.md).

---

# The killer primitive: **Behavior Diff**

Git tells you which bytes changed.

**EvoPR tells you which decisions changed.**

~~~diff
- selected_action = query_database
+ selected_action = validate_tenant

- db_access = allowed
+ db_access = blocked_until(tenant_scope == validated)
~~~

A normal code diff answers:

> What file changed?

A Behavior Diff answers:

> **What will the agent do differently in the same world?**

That is the review surface self-evolving agents are missing.

---

# Why trajectory → skill is not enough

A failure does not automatically mean the prompt is wrong.

The cause could live in:

- a Skill
- a system prompt
- a deterministic policy
- a router
- memory
- a tool contract
- an eval gap

So EvoPR does **not** start by asking:

> “What lesson should I write into SKILL.md?”

It asks:

> **“What is the smallest behavior surface that actually caused the failure?”**

~~~text
one failure
   │
   ├── H1: missing Skill instruction
   ├── H2: missing execution guard
   ├── H3: wrong router decision
   └── H4: stale memory
              ↓
       discriminating replay
              ↓
      falsify weak hypotheses
              ↓
      smallest valid mutation
~~~

The output may be a Skill.

Or it may be a policy, router rule, memory contract, tool wrapper, or executable regression test.

---

# Five first-class objects

## 1. Trace

What happened.

Not just the final answer — the relevant execution path.

## 2. Decision Capsule

What the agent believed at the decision point:

~~~text
goal
world state
candidate actions
selected action
assumptions
uncertainty
guards
human edits
~~~

This makes failure attribution more precise than “the trajectory failed”.

## 3. Outcome Receipt

What happened **after** the decision reached the world.

Examples:

~~~text
human correction
verifier failure
CI red → green
undo
retry
reuse
abandonment
silence
real-world success
~~~

These signals are intentionally **not treated as equivalent**.

Silence is not approval.  
A retry is not the same as rejection.  
An infrastructure failure is not a behavioral failure.

## 4. Evolution Artifact

The smallest persistent behavior change.

Supported mutation surfaces in the current object model:

~~~text
skill
prompt
policy
router
memory
tool
eval
~~~

## 5. Executable Eval

Every accepted lesson should eventually become a regression case.

> **No evidence, no promotion.**

---

# Architecture

~~~mermaid
flowchart TD
    A[Real task / PR / Agent run] --> B[Decision Capsule]
    B --> C[Outcome Receipt]
    C --> D[Evidence]
    D --> E[Competing hypotheses]

    E --> F1[Skill mutation]
    E --> F2[Policy mutation]
    E --> F3[Router mutation]
    E --> F4[Memory mutation]
    E --> F5[Tool mutation]
    E --> F6[Eval mutation]

    F1 --> G[Replay matrix]
    F2 --> G
    F3 --> G
    F4 --> G
    F5 --> G
    F6 --> G

    G --> H[Behavior Diff]
    H --> I[Evolution PR]

    I --> J{Gate}
    J -->|promote| K[Capability update]
    J -->|hold| L[More evidence]
    J -->|reject| M[Discard]
    K --> N[Next real task]
    N --> A
~~~

---

# The Evolution Packet

The current prototype consumes one explicit JSON packet.

~~~json
{
  "packet_id": "evo-tenant-scope-001",
  "agent": "coding-agent",
  "failure_summary": "Agent queried tenant data too early.",

  "decision_capsule": "...",
  "outcome_receipt": "...",

  "evidence": [
    {
      "source": "pr-review-418",
      "kind": "human_correction",
      "verdict": "negative",
      "confidence": 0.99
    }
  ],

  "hypotheses": [
    {
      "id": "h2",
      "mechanism": "Missing execution policy guard.",
      "target_surface": "policy",
      "uncertainty": 0.12
    }
  ],

  "candidates": [
    {
      "id": "c-policy",
      "surface": "policy",
      "title": "Enforce tenant validation precondition",
      "rollback_ref": "policy:tenant-scope@previous",
      "replay_results": []
    }
  ],

  "selected_candidate_id": "c-policy"
}
~~~

Then:

~~~bash
evopr build examples/evolution_pr.json --out EVOLUTION_PR.md
~~~

The output is designed to be usable as a GitHub PR body, review artifact, CI report, or future GitHub App payload.

---

# Promotion gate

The v0.1 prototype intentionally uses a conservative simple gate.

A candidate is automatically marked promotable only when:

~~~text
has valid replay evidence
AND mean replay delta > 0
AND regressions == 0
AND risk_flags == []
~~~

This is deliberately small and inspectable.

Future versions can plug in stronger gates without changing the review contract.

---

# Evolution is bigger than “write a better Skill”

| Question | Trajectory distillation | EvoPR |
|---|---|---|
| What failed? | trajectory outcome | decision + world outcome |
| Why did it fail? | analyst/reflection | competing causal hypotheses |
| What changes? | usually Skill text | smallest behavior surface |
| Candidate surfaces | Skill | Skill / prompt / policy / router / memory / tool / eval |
| Validation | task eval | replay + holdout + regression |
| Review unit | file / Skill diff | **Behavior Diff** |
| Deployment | replace artifact | promote / hold / rollback |
| Provenance | optional | first-class |
| Reversibility | external concern | part of the evolution contract |

**The goal is not to make agents mutate more often.**

The goal is to make every mutation **explainable, testable, and reversible**.

---

# What works today

This branch is an early but executable v0.1.

### ✅ Implemented

- Evidence model with confidence and semantics
- Decision Capsule + Outcome Receipt fields
- Competing causal hypotheses
- Multiple mutation surfaces
- Replay result model
- Regression counting
- Promotion gate
- Rollback reference
- Activation scope
- Behavior PR Markdown renderer
- <code>evopr build</code> CLI
- End-to-end CLI smoke test
- Python 3.10 / 3.11 / 3.12 CI
- Generated example output

### 🚧 Next

- Automatic PR / review / CI ingestion
- Trace → Decision Capsule compiler
- Hypothesis generator
- Counterfactual world forks
- Real replay harness
- Hidden / OOD / security holdouts
- Shadow deployment
- Canary promotion
- Automatic rollback
- Capability split / merge / decay / retire
- Codex / Claude Code / Copilot / OpenCode adapters

Nothing in the second list is presented as implemented yet.

---

# Where this is going

## v0.1 — Evolution Packet ✅

~~~text
evidence
→ hypotheses
→ candidate mutations
→ replay results
→ Behavior PR
~~~

## v0.2 — Replay Worlds

Freeze the relevant world state and rerun candidate behaviors against controlled variations.

~~~text
same task
same tools
same world snapshot
different capability mutation
~~~

Then create discriminating cases that answer:

> “Was the Skill wrong, or was the execution policy wrong?”

## v0.3 — Causal Selector

Generate multiple failure mechanisms and actively choose replays that maximize information gain.

~~~text
failure
→ H1 / H2 / H3
→ discriminating probes
→ eliminate hypotheses
→ minimal intervention
~~~

## v0.4 — GitHub-native evolution

~~~text
PR review
+ CI failure
+ merged fix
      ↓
automatic Evolution Packet
      ↓
EvoPR opens a Behavior PR
~~~

Merge promotes the capability.

Revert rolls it back.

## v0.5 — Online evolution

~~~text
candidate
→ shadow
→ canary
→ promote
          ↘ regression → rollback
~~~

## v1.0 — Verified Agent Evolution

A portable evolution runtime where agents can improve from consequences **without silently rewriting their own behavior**.

---

# A GitHub-native future

The end-state should feel boringly familiar:

~~~text
code changes        → Pull Request
agent behavior      → Evolution PR
database schema     → Migration
model capability    → Capability Migration
~~~

That familiarity is the feature.

Teams already know how to:

- review
- comment
- approve
- gate
- merge
- revert
- audit

EvoPR brings those mechanics to self-evolving agent behavior.

---

# Design principles

### 1. Minimal intervention

Do not rewrite the whole Agent when one guard is wrong.

### 2. Causal humility

A plausible explanation is still a hypothesis until replay supports it.

### 3. Evidence semantics

Human edits, deterministic verifiers, silence, retries, and infrastructure failures carry different meanings.

### 4. Behavior before prose

A beautiful SKILL.md is worthless if the behavior does not improve.

### 5. Regression is a first-class outcome

Fixing the original failure is not enough.

### 6. Reversibility

Every promoted mutation should know how to go back.

### 7. Git is the registry

Behavior evolution should leave an inspectable history instead of disappearing into an opaque memory store.

---

# Repository layout

~~~text
skill_factory/
├── evolution/
│   ├── models.py       # Evidence, hypotheses, mutations, replay results
│   ├── report.py       # Behavior PR renderer
│   └── cli.py          # evopr build
│
├── generator/          # existing trajectory → Skill generator
├── verifier/           # Skill static validation
├── evaluator/          # evaluation primitives
├── registry/           # existing Skill registry
└── web/                # existing review UI

examples/
├── evolution_pr.json   # input packet
└── EVOLUTION_PR.md     # generated review artifact

tests/
└── unit/
    └── test_evolution_report.py
~~~

The original SkillFactory remains useful.

EvoPR moves it one level up:

~~~text
SkillFactory v0
trajectory → Skill

EvoPR
experience → causal hypothesis → smallest capability change → proof → promotion
~~~

---

# Try it

~~~bash
git clone -b feat/evopr-evolution-runtime https://github.com/hippoley/SkillFactory.git
cd SkillFactory
pip install -e .

evopr build examples/evolution_pr.json --out EVOLUTION_PR.md
~~~

Then open <code>EVOLUTION_PR.md</code> and review the agent change as if it were code.

---

# The research question

> **Can an agent identify exactly which capability caused a failure, change only that capability, prove the change is better, avoid unrelated regressions, and remain reversible?**

That is the project.

---

# Contributing

The most useful contributions right now are concrete failure traces that can become executable evolution cases:

- coding-agent review corrections
- CI failures followed by a confirmed fix
- tool-selection mistakes
- router mistakes
- stale-memory failures
- premature execution
- safety guard failures
- cases where a “fix” helped one task but hurt another

If you have one, open an issue with:

~~~text
1. what the agent saw
2. what it decided
3. what happened
4. how it was corrected
5. how we can verify the correction
~~~

---

# License

Apache-2.0.

---

<div align="center">

### **Agents will learn. The question is whether you can review what they learned.**

**EvoPR — pull requests for agent behavior.**

</div>
