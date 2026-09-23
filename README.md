# Counterproof

<div align="center">

### **Your coding agent says it fixed the bug. Prove it.**

**Behavioral evidence for agent-generated pull requests.**

[![CI](https://github.com/hippoley/SkillFactory/actions/workflows/ci.yml/badge.svg)](https://github.com/hippoley/SkillFactory/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-black.svg)](LICENSE)
![No LLM](https://img.shields.io/badge/core%20PR%20proof-no%20LLM-111111.svg)
![No API key](https://img.shields.io/badge/API%20key-not%20required-111111.svg)

[**Quickstart**](#30-second-quickstart) ·
[**Live Proof Lab**](https://raw.githack.com/hippoley/SkillFactory/d7ebbc096f5d2ec0cfd0c3e4d0f914167c083dbc/site/standalone.html) ·
[**Proof Protocol v1**](docs/PROOF_PROTOCOL.md) ·
[**Deep runtime**](#the-deeper-runtime)

</div>

---

A green CI run proves that your code passes **now**.

It does not prove that the agent's new regression test would have failed **before** the fix.

Counterproof asks the missing question:

```text
PR code + PR test          → PASS
old code + the same test   → FAIL
test / CI judge unchanged  → CLEAN
                              ↓
                          VERIFIED
```

That turns:

> “the agent says it fixed the bug”

into:

> **this exact test distinguishes the code before and after the fix.**

---

## The PR card

Counterproof writes one compact, sticky proof card into the pull request:

```text
COUNTERPROOF

Regression Witness     WITNESSED
Evidence mode          PRECISE
PR head + PR tests     PASS
Base + same tests      FAIL
Proof Integrity        CLEAN
Unified Proof          VERIFIED
Proof Ready            true
```

No model grades another model.

The core PR proof is built from **Git history + your existing test runner**.

---

## 30-second quickstart

Install the current repository implementation:

```bash
python -m pip install "git+https://github.com/hippoley/SkillFactory.git"

counterproof doctor
counterproof init
```

`counterproof doctor` self-tests Counterproof's Git/worktree/integrity mechanics.

`counterproof init` detects the local test runner and writes:

```text
.github/workflows/counterproof.yml
```

Start in **advisory** mode.

After you have watched it behave correctly on real PRs:

```bash
counterproof init --force --strict
```

`--strict` means one thing:

> **Counterproof must produce VERIFIED proof.**

### Or add the Action directly

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

      # Install your project's dependencies before Counterproof.
      - uses: hippoley/SkillFactory@main
        with:
          test-command: "python -m pytest -q {tests}"
          require-proof-ready: "true"
```

No hosted service. No API key. No LLM required for this path.

---

## Why green CI is not enough

A coding agent can create a patch and a test in the same pull request.

Then this happens:

```text
agent changes code
agent adds test
CI runs changed code + changed test
CI turns green
```

But the reviewer still does not know:

> **Would this test have caught the original bug?**

Counterproof replays the PR's test against the **pre-change code**.

```text
                     PR HEAD       BASE
changed test           PASS         FAIL
                                    /
                                   /
                           WITNESSED
```

If the same test passes on both sides, Counterproof says **NOT WITNESSED**.

It does not manufacture proof.

---

## It also checks whether the PR changed the judge

A convincing test is weaker evidence if the same PR also weakens the machinery that evaluates it.

Counterproof's **Proof Integrity Guard** surfaces deterministic evidence-risk changes such as:

```text
deleted test                         → review
new skip / xfail                     → review
continue-on-error: true              → review
pytest ... || true                   → review
pull_request trigger removed         → review
test / coverage / CI config changed  → review
```

A finding does **not** mean “malicious PR.”

It means:

> the evidence surface changed, so the proof is no longer independent.

That distinction matters.

---

## One result for humans and machines

Counterproof combines Regression Witness + Proof Integrity into one conservative verdict:

```text
proof-status = verified | review-required | suite-delta | unproven | ...
proof-ready  = true | false
```

Only this combination becomes `verified / true`:

```text
witness_status   = witnessed
evidence_mode    = precise
integrity_status = clean
```

The Action exposes:

```text
status
evidence-mode
integrity-status
proof-status
proof-ready
summary-json-path
```

and writes:

```text
.counterproof/out/PROOF_SUMMARY.json
```

### Proof Protocol v1

Counterproof publishes a versioned machine contract:

```bash
counterproof schema proof-summary-v1 --out proof-summary.schema.json
```

See **[Proof Protocol v1](docs/PROOF_PROTOCOL.md)**.

The schema enforces the VERIFIED invariant, so downstream bots and agent runtimes do not have to parse Markdown or invent their own interpretation.

> `proof-ready=true` means Counterproof's configured evidence contract is satisfied.  
> It does **not** mean the entire pull request is automatically safe to merge.

---

## PRECISE is not the same as SUITE DELTA

Counterproof deliberately distinguishes evidence strength.

| Mode | Test command | What Counterproof can claim |
|---|---|---|
| **PRECISE** | contains `{tests}` | the same changed tests distinguish HEAD from BASE |
| **SUITE** | no `{tests}` | the configured full suite distinguishes HEAD from BASE |

Example:

```text
python -m pytest -q {tests}   → PRECISE
npx vitest run {tests}        → PRECISE
bundle exec rspec {tests}     → PRECISE

go test ./...                 → SUITE DELTA
mvn test                      → SUITE DELTA
./gradlew test                → SUITE DELTA
generic npm test              → SUITE DELTA
```

A full-suite failure on BASE may be useful evidence.

But Counterproof will **not** call it an exact Regression Witness unless the changed test itself was isolated.

`counterproof init --strict` refuses suite-only evidence instead of silently weakening the contract.

---

## What happens on a PR?

```text
pull request
    │
    ├─ find changed regression tests
    │
    ├─ run evidence on PR HEAD
    │      └─ must pass
    │
    ├─ create detached BASE worktree
    │
    ├─ overlay PR test/support files
    │
    ├─ run the same evidence on BASE
    │
    ├─ inspect test / CI judge changes
    │
    └─ aggregate
            │
            ├─ WITNESSED + CLEAN   → VERIFIED
            ├─ WITNESSED + RISK    → REVIEW REQUIRED
            ├─ SUITE DELTA          → SUITE DELTA
            ├─ passes on BASE       → UNPROVEN
            └─ fails on HEAD        → HEAD FAILING
```

The result appears in:

- the GitHub job summary;
- one sticky PR comment;
- Action outputs;
- JSON artifacts.

---

## Why this is not another AI reviewer

AI reviewers are useful for finding suspicious code, summarizing diffs, and suggesting changes.

Counterproof solves a different problem.

| | AI reviewer | Counterproof |
|---|---|---|
| Main question | “Does this diff look wrong?” | “Does this evidence distinguish before from after?” |
| Core input | code + model context | Git history + tests |
| Main output | comments / suggestions | replayable behavioral proof |
| Requires LLM | usually | **no** for PR proof |
| Can say “I don't know” | model-dependent | explicit states |
| Detects changed judge | not the core abstraction | **yes** |
| Machine contract | vendor-specific | **Proof Protocol v1** |

Counterproof is designed to sit **next to** Copilot, Claude Code, Codex, Cursor, PR-Agent, or any other coding agent.

It does not care which model wrote the patch.

---

## Designed for agent PRs, useful for human PRs too

Counterproof is especially useful when:

- an agent changes code and writes its own tests;
- a reviewer cannot afford to reconstruct the failure manually;
- an issue says “fixed” but the test only proves the new implementation;
- CI configuration changed in the same PR;
- teams want a deterministic gate before allowing agent-generated fixes to accumulate.

The core proof remains useful even when a human wrote the patch.

---

## Runner support

`counterproof init` currently detects common setups including:

```text
pytest
Vitest
Jest
Playwright
npm test
Go test
RSpec
Maven
Gradle
```

It also recognizes common test-file conventions across Python, JavaScript/TypeScript, Go, Ruby, Java, Kotlin, C#, and C++.

For custom harnesses:

```bash
counterproof init \
  --test-command "./scripts/regression-check"
```

For a precise custom harness:

```bash
counterproof init \
  --test-command "./scripts/regression-check {tests}" \
  --strict
```

Counterproof does not guess project-specific dependency installation when it cannot infer it safely.

---

## Pin the Action when you are ready

Generated workflows currently target `@main` because Counterproof does not yet have a published release tag.

Teams can pin a known branch, future tag, or commit SHA:

```bash
counterproof init --action-ref <git-ref>
```

The ref is validated before Counterproof writes it into workflow YAML.

---

## The deeper runtime

Regression Witness is the smallest useful entry point.

Counterproof also contains an experimental runtime for **falsifiable agent self-improvement**.

<details>
<summary><strong>Open the deeper causal loop</strong></summary>

<br>

Instead of asking only:

> “what lesson should the agent remember?”

the runtime asks:

> **which explanation survives an experiment, and what evidence earns the right to change behavior?**

```text
raw failure
    ↓
Decision Capsule + Outcome Receipt
    ↓
competing hypotheses
    ↓
falsifiable Probe Contracts
    ↓
pre-registered predictions
    ↓
same cases × multiple interventions
    ↓
fitness evidence + diagnostic evidence
    ↓
unique / ambiguous / prediction-blocked
    ↓
Next Probe Plan
    ↓
reviewed adapter binding
    ↓
structured behavior evidence
    ↓
Behavior Proof + Proof Receipt
```

### Example

```bash
counterproof evolve examples/traces/tenant_failure.json \
  --experiment-manifest examples/discrimination_suite.json \
  --surface policy \
  --surface skill \
  --surface prompt \
  --out BEHAVIOR_PROOF.md \
  --receipt-out PROOF_RECEIPT.json
```

Counterproof is allowed to return:

```text
unique-survivor
ambiguous
prediction-blocked
no-survivor
diagnostic-only
```

**No winner is better than a fake winner.**

### Structured probe protocol

Adapters can return:

```text
COUNTERPROOF_RESULT={
  "verdict": "pass",
  "score": 0.82,
  "metrics": {"latency_ms": 17},
  "observations": ["target stayed stable"],
  "artifacts": ["trace://run/42"]
}
```

This separates:

```text
process execution
from
behavioral outcome
```

See [Counterproof architecture](docs/COUNTERPROOF.md).

</details>

---

## What is real today?

Counterproof keeps a runtime truth table instead of presenting roadmap items as finished features.

```bash
counterproof audit
```

A compact view:

| Capability | Status |
|---|---|
| Regression Witness | **TESTED** |
| Proof Integrity Guard | **TESTED** |
| Unified `proof-status / proof-ready` | **TESTED** |
| Proof Protocol v1 | **TESTED** |
| One-command GitHub onboarding | **TESTED** |
| Clean wheel install | **TESTED** |
| Multi-intervention discrimination | **TESTED** |
| Pre-registered predictions | **TESTED** |
| Proof Receipt + drift detection | **TESTED** |
| Interactive Proof Lab | **DEMO** |
| Automatic domain-test synthesis | **PLANNED** |
| Live agent-framework trace adapters | **PLANNED** |
| Shadow / canary rollout | **PLANNED** |
| Automatic mutation merge / rollback | **PLANNED** |

Counterproof deliberately separates **tested**, **demo**, **partial**, and **planned** capabilities.

---

## Live Proof Lab

The browser playground visualizes four different evidence states:

```text
REAL REGRESSION  → WITNESSED + CLEAN → VERIFIED
WEAK TEST        → NOT WITNESSED     → UNPROVEN
JUDGE CHANGED    → WITNESSED + RISK  → REVIEW REQUIRED
FULL SUITE       → SUITE DELTA        → SUITE DELTA
```

**[Open the live Proof Lab →](https://raw.githack.com/hippoley/SkillFactory/d7ebbc096f5d2ec0cfd0c3e4d0f914167c083dbc/site/standalone.html)**

The visual scenarios are fixtures. Real replay evidence comes from the CLI / Action.

---

## Principles

### Claim nothing you can't replay.

If the evidence cannot be reproduced, Counterproof should not turn it into a green badge.

### Never upgrade weak evidence by wording.

A suite-level delta stays a suite-level delta.

### A changed judge is part of the change.

Do not hide CI/test changes behind a green result.

### No winner is better than a fake winner.

Ambiguity is a first-class result in the deeper causal runtime.

### Evidence is an interface.

Humans get a PR card. Machines get a versioned JSON contract.

---

## Docs

- **[Proof Protocol v1](docs/PROOF_PROTOCOL.md)** — stable machine verdict contract.
- **[Counterproof architecture](docs/COUNTERPROOF.md)** — deeper causal/self-evolution runtime.
- **[Examples](examples/)** — replay, discrimination, structured adapters, raw traces.
- **[Interactive Proof Lab](https://raw.githack.com/hippoley/SkillFactory/d7ebbc096f5d2ec0cfd0c3e4d0f914167c083dbc/site/standalone.html)** — browser demo.

---

## Roadmap

The next milestones are deliberately practical:

```text
0.2.x  first tagged / packaged release
       stable Action ref
       tighter runner adapters

0.3    GitHub-native evidence ingestion
       richer test adapters
       PR / review / CI trace normalization

0.4    executable probe synthesis
       causal discrimination across live agent runs

0.5    shadow / canary evidence
       mutation lifecycle + rollback policy
```

---

## Contributing

The best contributions are not “more AI.”

They are things that make proof stronger:

- a runner adapter that preserves evidence semantics;
- a real-world PR fixture that breaks a weak assumption;
- an integrity rule with low false-positive cost;
- a reproduction where Counterproof overclaims;
- a protocol consumer in another language/tool.

If Counterproof labels weak evidence as strong evidence, that is a bug.

---

## License

Apache-2.0.

---

<div align="center">

### **Green is a state. Proof is a relationship between before and after.**

**Counterproof**

*Claim nothing you can't replay.*

</div>
