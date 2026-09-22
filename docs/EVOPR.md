# EvoPR — Pull Requests for Agent Behavior

> **Your agent can rewrite itself. Make it open a pull request first.**

EvoPR is an evolution layer for SkillFactory. It turns real failures and corrections into
reviewable behavior changes, then proves those changes before promotion.

The key shift:

- Trace-to-skill systems ask: **what lesson should become a better Skill?**
- EvoPR asks: **what is the smallest behavior surface that should change, what evidence proves it,
  and can that change survive counterfactual replay, holdout, and rollout?**

## The loop

~~~text
REALITY
  ↓
Decision Capsule
  ↓
Outcome Receipt
  ↓
Evidence Graph
  ↓
Competing causal hypotheses
  ↓
Minimal mutations
  ├─ Skill
  ├─ Prompt
  ├─ Policy
  ├─ Router
  ├─ Memory
  ├─ Tool
  └─ Eval
  ↓
Counterfactual world forks
  ↓
Behavior Diff
  ↓
EVOLUTION PR
  ↓
Holdout → Shadow → Canary
  ↓
Merge / Rollback
  ↓
Capability Profile
  └──────────────→ next reality
~~~

## Five first-class objects

### Trace
What happened.

### Decision Capsule
What the agent believed, which candidates it considered, what it selected, which assumptions
were present, and what uncertainty remained.

### Outcome Receipt
What happened in the world after execution. A verifier pass, a human correction, undo, retry,
reuse, abandonment, and silence are not treated as equivalent evidence.

### Evolution Artifact
The smallest persistent behavior change. A lesson does not have to become a SKILL.md. It can compile
into a policy, router rule, memory contract, tool wrapper, executable subagent, or eval.

### Executable Eval
Every accepted lesson creates a regression test. No evidence, no promotion.

## Killer primitive: Behavior Diff

Git shows which bytes changed. EvoPR shows which decisions changed.

~~~text
BEFORE
tenant_scope = provisional
selected_action = query_database
tool_call = db.lookup(...)

AFTER
tenant_scope = provisional
selected_action = validate_tenant
tool_call = blocked

CAUSE
policy precondition introduced from hypothesis h2

EVIDENCE
human review
deterministic regression
security holdout
~~~

## Evolution PR contract

Every proposed evolution contains:

- failure fingerprint
- Decision Capsule
- Outcome Receipt
- evidence references and semantics
- competing causal hypotheses
- candidate mutations across multiple behavior surfaces
- selected minimal intervention
- Behavior Diff
- replay matrix
- hidden, OOD, and security holdout summary
- risk flags
- activation scope
- rollback reference
- provenance

## The research question

The interesting question is not simply **can an agent learn?**

It is:

> Can an agent change exactly the capability that caused a failure, demonstrate why the change is
> better, avoid unrelated regressions, and remain reversible?

## Viral demo

The first public demo should use one real pull request:

1. a coding agent submits a faulty change;
2. a reviewer leaves one correction;
3. CI goes red then green;
4. EvoPR identifies competing causal mechanisms;
5. it forks the recorded world and falsifies the weak explanations;
6. it proposes one minimal policy or skill mutation;
7. the PR shows a before/after Behavior Diff and replay matrix;
8. merge promotes the behavior and revert restores the previous capability.

The screenshot should be understandable without reading a paper.

## Prototype

~~~bash
pip install -e .
evopr build examples/evolution_pr.json --out EVOLUTION_PR.md
~~~

## Roadmap

**v0.1 — Evolution Packet**  
Decision Capsules, Outcome Receipts, causal hypotheses, mutation candidates, Behavior PR renderer.

**v0.2 — Replay Worlds**  
Deterministic trace capture and controlled counterfactual forks.

**v0.3 — Causal Selector**  
Generate competing mechanism hypotheses and pick the minimal intervention using discriminating
replays rather than one-shot reflection.

**v0.4 — GitHub-native loop**  
PR/review/CI ingestion, automatic Evolution PR creation, merge-to-promote, revert-to-rollback.

**v0.5 — Online evolution**  
Shadow and canary routing, calibrated capability profile, decay/split/merge/retire lifecycle.

**v1.0 — Verified Agent Evolution**  
Portable evolution runtime across Codex, Claude Code, Copilot, OpenCode, and custom agents.
