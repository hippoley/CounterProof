# Counterproof

<div align="center">

## **Your coding agent says it fixed the bug. Prove it.**

**Behavioral proof for agent-generated pull requests.**

[![CI](https://github.com/hippoley/CounterProof/actions/workflows/ci.yml/badge.svg)](https://github.com/hippoley/CounterProof/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-black.svg)](LICENSE)
![No LLM](https://img.shields.io/badge/core%20PR%20proof-no%20LLM-111111.svg)
![No API key](https://img.shields.io/badge/API%20key-not%20required-111111.svg)

### [**▶ PLAY LIVE DEMO**](https://raw.githack.com/hippoley/CounterProof/main/site/standalone.html) · [**⚡ INSTALL ACTION**](#30-second-onboarding) · [**◎ UNDERSTAND THE IDEA**](#why-green-ci-is-not-enough)

[![Open Counterproof Proof Lab](assets/counterproof-hero.svg)](https://raw.githack.com/hippoley/CounterProof/main/site/standalone.html)

**Click the panel. Break the proof. Change the judge. See what survives.**

<sub>Works beside Claude Code · Codex · Copilot · Cursor · PR-Agent · human-written PRs — Counterproof verifies the evidence, not the author.</sub>

</div>

---

A green CI run proves that your code passes **now**.

It does **not** prove that the regression test added by the same coding agent would have caught the bug **before** the fix.

Counterproof asks that missing question.

```text
PR code + PR test         → PASS
old code + the same test  → FAIL
test / CI judge unchanged → CLEAN
                             ↓
                     REGRESSION WITNESSED
```

That turns:

> “the agent says it fixed the bug”

into:

> **this exact test behaves differently before and after the fix.**

---

## See it before you install it

### **[Launch the interactive Proof Lab →](https://raw.githack.com/hippoley/CounterProof/main/site/standalone.html)**

The browser experience lets you play with different evidence situations instead of reading another architecture diagram.

```text
REAL REGRESSION
HEAD passes / BASE fails
→ strong before-vs-after evidence

WEAK TEST
HEAD passes / BASE also passes
→ the test does not witness the claimed fix

JUDGE CHANGED
the regression evidence exists
but CI / test machinery changed too
→ reviewer attention required

FULL SUITE
the full suite differs
but the changed test was not isolated
→ weaker evidence than an exact witness
```

The browser scenarios are fixtures. **Real evidence comes from the CLI / GitHub Action.**

---

[![Counterproof proof walkthrough](assets/proof-walkthrough.svg)](https://raw.githack.com/hippoley/CounterProof/main/site/standalone.html)

> **Click the walkthrough to open the live Proof Lab.**

---

## The fastest useful thing Counterproof does

Take tests changed in a pull request.

Run them on the PR.

Then replay the **same tests** against the pre-change code.

```text
                         PR HEAD        BASE
same changed test          PASS          FAIL
                              \          /
                               \        /
                              WITNESSED
```

If the same test already passes on BASE, Counterproof does not manufacture a success story.

It says the proof is weak.

---

## 30-second onboarding

Install the current repository build:

```bash
python -m pip install "git+https://github.com/hippoley/CounterProof.git"
```

Run a real local self-test first:

```bash
counterproof doctor
```

Then let Counterproof inspect the repository and write the pull-request workflow:

```bash
counterproof init
```

It detects common test runners, keeps the first install **advisory**, and writes:

```text
.github/workflows/counterproof.yml
```

After you have watched it behave correctly on real pull requests, turn on the two hard gates:

```bash
counterproof init --force --strict
```

Strict mode means:

```text
exact changed-test witness required
+
proof-integrity surface must stay clean
```

If the project only exposes a full-suite command such as `go test ./...` or generic `npm test`, Counterproof refuses `--strict` instead of pretending suite-level evidence is an exact witness.

### Manual Action setup

If you prefer to write the workflow yourself, the root Action is the same Regression Witness path:

```yaml
name: Counterproof

on:
  pull_request:

permissions:
  contents: read
  pull-requests: write

jobs:
  proof:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      # Install your project dependencies first.
      - uses: hippoley/CounterProof@main
        with:
          test-command: "python -m pytest -q {tests}"
          require-witness: "true"
          require-clean-integrity: "true"
```

For the deeper trace / hypothesis / multi-intervention runtime, use the explicit advanced Action:

```yaml
- uses: hippoley/CounterProof/actions/behavior-proof@main
  with:
    trace: path/to/trace.json
    experiment-manifest: path/to/experiments.json
```

Counterproof will:

```text
1. find tests added or modified by the PR
2. run them on PR HEAD
3. create a detached worktree at BASE
4. overlay the PR test/support files
5. run the same evidence on old code
6. classify PRECISE witness vs SUITE DELTA
7. inspect whether the PR changed the judge
8. write one sticky proof comment
```

No hosted service. No API key. No LLM is required for this path.

### Share a witness with a reviewer

A machine receipt is useful for automation; a reviewer needs the small set of facts they can check quickly.

```bash
counterproof share-witness REGRESSION_WITNESS.json \
  --source-url https://github.com/owner/repo/pull/123 \
  --runner-url https://github.com/owner/proof/actions/runs/456 \
  --out WITNESS_REVIEW_NOTE.md
```

The note includes the exact HEAD / BASE commits, exit codes, executed changed-test command, evidence digest, links, and the scope limit that a regression witness proves the tested before/after delta — not every claimed production cause.

---

## It also checks whether the PR changed the judge

A passing test is weaker evidence if the same PR also weakens the system that evaluates it.

Counterproof's **Proof Integrity Guard** surfaces changes such as:

```text
deleted test                         → review
new skip / xfail                     → review
continue-on-error: true              → review
pytest ... || true                   → review
pull_request trigger removed         → review
test / coverage / CI config changed  → surface explicitly
```

A finding does **not** mean “malicious PR.”

It means:

> **the evidence surface changed, so the reviewer should not treat the green result as independent evidence.**

---

## Why this matters now

Coding agents are getting very good at producing:

```text
code
+ tests
+ green CI
+ a confident explanation
```

That is useful.

It also creates a new review problem:

> **the system proposing the fix can now help produce the evidence for its own fix.**

Counterproof does not solve that by adding another model.

It adds a deterministic before/after experiment.

```text
Git history
+
your existing test runner
+
the same evidence on both sides
=
something a reviewer can inspect
```

---

## Not another AI reviewer

AI reviewers and Counterproof answer different questions.

| | AI reviewer | Counterproof |
|---|---|---|
| Main question | “Does this diff look suspicious?” | “Does this evidence distinguish before from after?” |
| Core input | code + model context | Git history + tests |
| Main output | suggestions / comments | replayable behavioral evidence |
| LLM required | usually | **no** for PR proof |
| Changed test/CI judge | not the core primitive | **explicitly surfaced** |
| Can refuse a story | model-dependent | **yes — weak/inconclusive evidence stays weak** |

Use Counterproof **next to** Claude Code, Codex, Copilot, Cursor, PR-Agent, or a human engineer.

It does not care who wrote the patch.

---

## Run the playground locally

```bash
python -m pip install "git+https://github.com/hippoley/CounterProof.git"

counterproof demo
```

Open:

```text
http://127.0.0.1:8765
```

Or just use the public version:

### **[Open Live Proof Lab →](https://raw.githack.com/hippoley/CounterProof/main/site/standalone.html)**

---

# The deeper runtime

Regression Witness is the smallest useful entry point.

Counterproof also contains an experimental runtime for **falsifiable agent self-improvement**.

Instead of asking only:

> “what lesson should the agent remember?”

it asks:

> **which explanation survives an experiment, and what evidence earns the right to change behavior?**

```text
RAW TRACE
   ↓
Decision Capsule + Outcome Receipt
   ↓
typed evidence
   ↓
competing hypotheses
   ↓
Probe Contracts
   ↓
same cases × multiple interventions
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

### One-command proof

```bash
counterproof prove examples/traces/tenant_failure.json \
  --replay-manifest examples/replay_suite.json \
  --surface policy \
  --out BEHAVIOR_PROOF.md
```

### Active discrimination

```bash
counterproof discriminate examples/traces/tenant_failure.json \
  --experiment-manifest examples/discrimination_suite.json \
  --surface policy \
  --surface skill \
  --surface prompt \
  --out DISCRIMINATION.md \
  --json-out DISCRIMINATION.json
```

### Guarded evolution

```bash
counterproof evolve examples/traces/tenant_failure.json \
  --experiment-manifest examples/discrimination_suite.json \
  --surface policy \
  --surface skill \
  --surface prompt \
  --out EVOLUTION_REVIEW.md \
  --packet-out EVOLVED_PACKET.json
```

Counterproof is allowed to return ambiguity.

**No winner is better than a fake winner.**

For the deeper architecture, see **[docs/COUNTERPROOF.md](docs/COUNTERPROOF.md)**.

---

## What is real today?

Counterproof keeps a runtime truth table instead of pretending roadmap items are finished.

```bash
counterproof audit
```

The current project includes tested paths for:

```text
Regression Witness
Proof Integrity Guard
raw JSON / JSONL trace ingestion
real subprocess replay
Probe Contracts
multi-intervention discrimination
pre-registered PASS / FAIL predictions
fitness vs diagnostic case semantics
reviewed adapter binding
structured probe results
Proof Receipt + source fingerprints
clean wheel installation
browser interaction smoke tests
```

And it still has clear research gaps:

```text
live agent-framework trace adapters
automatic trustworthy domain-test synthesis
arbitrary world snapshot / restore
generic live mutation executors
shadow / canary rollout
automatic mutation rollback
```

That distinction is intentional.

---

## The design rules

### **Claim nothing you can't replay.**

If the evidence cannot be reproduced, it should not become a stronger claim.

### **A changed judge is part of the change.**

CI and test configuration are evidence-producing machinery.

### **No winner is better than a fake winner.**

Ambiguity is a valid result.

### **Evidence should survive outside the model that produced the patch.**

That is the point.

---

## Repository map

```text
skill_factory/evolution/
├── trace.py
├── replay.py
├── discriminate.py
├── probe_planner.py
├── adapter_binding.py
├── receipt.py
├── capabilities.py
├── report.py
└── cli.py

actions/
└── witness/
    └── action.yml

site/
├── index.html
├── standalone.html
├── app.js
├── styles.css
└── data/

examples/
├── traces/
├── replay/
└── *_suite.json
```

---

## Share it

A 1280×640 social card is included at:

```text
assets/social-preview.svg
```

Use it for the repository social preview, launch posts, HN/X screenshots, or release notes.

---

## Break Counterproof

The highest-value contribution is a **counterexample**.

Can you make Counterproof:

- call weak evidence strong?
- miss a real regression witness?
- trust a changed judge?
- confuse infrastructure failure with behavioral failure?
- produce a proof that looks convincing but is semantically wrong?

If yes, that is not an edge case we want to hide.

**[Open a Counterexample issue →](https://github.com/hippoley/CounterProof/issues/new?template=counterexample.yml)**

A great report gives us:

```text
small reproducible PR
+ expected evidence classification
+ actual Counterproof classification
+ why the difference matters
```

### Other valuable contributions

- runner adapters that preserve before/after semantics;
- real PR fixtures that break assumptions;
- integrity rules with low false-positive cost;
- better discriminating probes;
- adapters for real agent runtimes.

If Counterproof labels weak evidence as strong evidence, **that is a bug**.

---

## License

Apache-2.0.

---

<div align="center">

### **Green is a state. Proof is a relationship between before and after.**

**Counterproof**

*Claim nothing you can't replay.*

### **[▶ Open the Live Proof Lab](https://raw.githack.com/hippoley/CounterProof/main/site/standalone.html)**

</div>
