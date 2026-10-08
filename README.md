# CounterProof

<div align="center">

## **Your coding agent says it fixed the bug. Prove the exact claim.**

**Replay the evidence. Test the oracle. Keep unproven claims unproven.**

[![CI](https://github.com/hippoley/CounterProof/actions/workflows/ci.yml/badge.svg)](https://github.com/hippoley/CounterProof/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-black.svg)](LICENSE)
![No LLM](https://img.shields.io/badge/core%20PR%20proof-no%20LLM-111111.svg)
![No API key](https://img.shields.io/badge/API%20key-not%20required-111111.svg)

### [**▶ PLAY PROOF LAB**](https://hippoley.github.io/CounterProof/) · [**? BRING A PR**](https://github.com/hippoley/CounterProof/issues/new?template=reality-probe.yml) · [**⚡ INSTALL**](#30-second-onboarding)

[![Open CounterProof Proof Lab](assets/counterproof-hero.svg)](https://hippoley.github.io/CounterProof/)

**One claim · exact candidates · explicit oracle · one auditable receipt.**

<sub>Not a merge bot. Not another AI reviewer. CounterProof tells you what the submitted evidence establishes — and what it still does not.</sub>

</div>

---

## Start here: inspect a proof, then challenge it

**[▶ Open the live, no-login Proof Lab](https://hippoley.github.io/CounterProof/)** · [Run it yourself](#30-second-onboarding) · [Bring a real PR](https://github.com/hippoley/CounterProof/issues/new?template=reality-probe.yml)

The public Proof Lab is an **interactive illustration backed by bundled fixtures**, not proof that CounterProof executed a live third-party repository in your browser. For independently checkable evidence, start with the [Bluefin source run](https://github.com/hippoley/CounterProof/actions/runs/37412091382), [machine receipt](examples/claim_matrix/receipts/bluefin-4539-flagship-causal.json), and [external evidence ledger](docs/EXTERNAL_EVIDENCE_LEDGER.md).

**The proof boundary matters:** a passing CI job, a convincing demo, a maintainer acknowledgement, and production adoption are four different claims. CounterProof does not treat them as interchangeable.

### Runtime authority closure gate

CounterProof can also evaluate whether an authority change is actually closed at consequential runtime sinks:

```bash
counterproof runtime-closure trace.json --require-closed
```

The machine result is one of `CLOSED`, `PARTIAL`, `UNKNOWN`, or `VIOLATION`, and includes the SHA-256 of the exact input trace. `--require-closed` exits non-zero unless every declared sink has positive closure evidence.

The profile deliberately separates:

```text
authority change recorded
!= authority change effective at a sink
!= sink closed
```

Unknown event types and ambiguous ordering are rejected rather than silently ignored. The current cross-system cases are CounterProof-side evidence mappings, not claims that upstream projects have adopted this profile.

---

## Flagship proof: one intervention, same oracle, recovery after revert

CounterProof's clearest end-to-end causal case is a controlled replay of [ublue-os/bluefin#4539](https://github.com/ublue-os/bluefin/pull/4539).

```text
CONTROL   baseline signature
   ↓ add historical 30-after-keyring.conf
BAD       late-keyring / portal-dependency signature appears
   ↓ remove that exact intervention
REVERT    baseline signature returns
```

All three candidates ran the **same projectbluefin/testsuite GNOME/QEMU oracle** in [workflow run #37412091382](https://github.com/hippoley/CounterProof/actions/runs/37412091382). The runtime jobs completed successfully for CONTROL, BAD, and REVERT; the behavioral verdict comes from the published candidate diagnostics, not from treating workflow success as the verdict.

| Candidate | QEMU runtime | keyring active | portal→keyring | NotInInitialization |
|---|---|---:|---:|---:|
| CONTROL | success | false | false | false |
| BAD | success | true | true | true |
| REVERT | success | false | false | false |

**Machine verdict: `WITNESSED_CONTROLLED_CAUSAL`**

> In the frozen controlled environment, adding the historical intervention is sufficient to produce the observed divergent signature, and removing that exact intervention restores the CONTROL signature.

This is deliberately **not** presented as an exact replay of the unavailable May 2026 historical registry images.

The same QEMU artifacts now feed three evidence layers: the Bluefin-specific controlled receipt, the reusable generic causal-replay receipt, and the provenance-bound flagship receipt.

**[Read the flagship machine receipt →](examples/claim_matrix/receipts/bluefin-4539-flagship-causal.json)** · **[Read the replay boundary →](reality/bluefin-4539/REPLAY_BOUNDARY.md)** · **[Open the source run →](https://github.com/hippoley/CounterProof/actions/runs/37412091382)**

---


## Flagship boundary: green judge, contradicted product oracle

A second flagship case shows the opposite failure mode: **green submitted evidence can still be wrong about product truth**.

In [anthropics/claude-code#89404](https://github.com/anthropics/claude-code/pull/89404), the submitted validator suite reported 5/5 passing. Reviewer-supplied measurements showed two stronger facts:

```text
submitted judge       5/5 PASS
multi-line regression suite stays green after extraction revert
product oracle        claude plugin validate --json → REJECT
oracle alignment      CONTRADICTED
```

CounterProof publishes this as an `ORACLE_CONTRADICTED_BY_PRODUCT` artifact. It is intentionally marked as **reviewer-supplied external-oracle evidence**; CounterProof does not claim it independently executed the Claude Code binary.

This case complements Bluefin:

```text
Bluefin
same oracle + controlled intervention + recovery
→ positive causal witness

Claude #89404
green submitted judge + rejecting product oracle
→ negative proof boundary
```

**[Read the oracle-disagreement artifact →](reality/claude-code-89404/ORACLE_DISAGREEMENT.md)** · **[Read the machine receipt →](examples/claim_matrix/receipts/claude-code-89404-oracle.json)**

---

## Tested on real agent PRs

CounterProof is not developed only against fixtures. New proof semantics are tested against public AI-assisted pull requests where a reviewer has a concrete reason not to trust a green check.

**[See the Reality Lab →](docs/REALITY_LAB.md)** · **[Bring an agent PR you don't trust →](https://github.com/hippoley/CounterProof/issues/new?template=reality-probe.yml)** · **[Choose a contribution path →](CONTRIBUTING.md)**

Current field cases include a genuine regression witness, a compiler-failure false positive, a changed-test-harness case, a claim-boundary case, and an oracle-mismatch case.

| Reality signal | What changed because of it |
|---|---|
| **17 public PR cases** | CounterProof gained runner, test-discovery, integrity, and claim-boundary fixes from failures against real repositories. |
| **External reviewer acceptance** | A reviewer asked for the compact claim/evidence matrix, then confirmed the automated artifact preserved the intended review semantics and was usable in review. [Read the exchange →](https://github.com/hippoley/CounterProof/issues/13#issuecomment-5812942595) |
| **External trust-boundary feedback** | Reviewer feedback and an external patch exposed that asserted oracle states need inspectable provenance. PR #50 closed unmerged, so CounterProof does not count that contribution as adopted evidence; the compatible provenance guard is being carried forward against current main. [Review thread →](https://github.com/hippoley/CounterProof/issues/16) |
| **Downstream consumer probe** | A PROVE maintainer preferred attaching CounterProof as ordinary requirement evidence instead of creating a new packet or approval layer. [See the handoff →](examples/handoff/codex-prove.md) |

These are evidence links, not endorsements. CounterProof still treats every new claim as unproven until its evidence earns a stronger status.

High-signal public claims are declared in [`examples/claim_matrix/public-claims.yml`](examples/claim_matrix/public-claims.yml) and CI checks them against canonical Reality Contract lifecycle and claim expectations.

---

A green CI run proves that your code passes **now**.

It does **not** prove that the regression test added by the same coding agent would have caught the bug **before** the fix.

CounterProof asks that missing question.

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

### **[Launch the interactive Proof Lab →](https://hippoley.github.io/CounterProof/)**

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

[![CounterProof proof walkthrough](assets/proof-walkthrough.svg)](https://hippoley.github.io/CounterProof/)

> **Click the walkthrough to open the live Proof Lab.**

---

## The fastest useful thing CounterProof does

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

If the same test already passes on BASE, CounterProof does not manufacture a success story.

It says the proof is weak.

---

## 30-second onboarding

Install the current repository build:

```bash
python -m pip install "git+https://github.com/hippoley/CounterProof.git"
```

From a feature branch, ask CounterProof for one local evidence readout **before changing repository configuration**:

```bash
counterproof check
```

A strong local result looks like:

```text
Regression       WITNESSED
Evidence scope   SUBMITTED JUDGE
Proof integrity  CLEAN
Strict gate      PASS
Product oracle   UNVERIFIED
```

That means the exact changed-test evidence distinguishes HEAD from BASE and CounterProof did not detect a changed evidence surface. It does **not** mean the PR is correct or ready to merge.

If runner or base detection is unusual, make it explicit:

```bash
counterproof check \
  --base origin/main \
  --test-command "python -m pytest -q {tests}"
```

Want to verify CounterProof itself first? Run:

```bash
counterproof doctor
```

When the local evidence shape looks useful, let CounterProof write an advisory pull-request workflow:

```bash
counterproof init
```

It detects common test runners and writes:

```text
.github/workflows/counterproof.yml
```

Only after you have watched it behave correctly on real pull requests, turn on the two narrow CI gates:

```bash
counterproof init --force --strict
```

Strict mode requires:

```text
exact changed-test witness
+
clean proof-integrity surface
```

It is an evidence gate, not a merge recommendation. If the project only exposes a full-suite command such as `go test ./...` or generic `npm test`, CounterProof refuses `--strict` instead of pretending suite-level evidence is an exact witness.

### Manual Action setup

If you prefer to write the workflow yourself, the root Action is the same Regression Witness path:

```yaml
name: CounterProof

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

CounterProof will:

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

### When a non-zero exit does not mean “the test failed”

Some build/test wrappers use the same exit code for assertion failures, compilation failures, missing SDKs, setup errors, and other infrastructure problems. In that situation, **do not mint a witness from exit code alone**.

Use the structured result protocol:

```bash
counterproof witness \
  --base origin/main \
  --test-command "python my_test_adapter.py {tests}" \
  --result-protocol json-v1
```

The adapter exits successfully only after it has determined a behavioral result and emits one final line:

```text
COUNTERPROOF_RESULT={"verdict":"pass","metrics":{}}
```

or:

```text
COUNTERPROOF_RESULT={"verdict":"fail","metrics":{}}
```

If the adapter itself exits non-zero, times out, or fails to emit a valid result, CounterProof reports **INCONCLUSIVE**. A compiler error is therefore not silently upgraded into regression evidence.

### When the test already existed but the fixture changed

Changed-test discovery is only the default. Sometimes the reviewer already knows the evidence set: an existing test becomes discriminating because the PR changes a fixture, sample, helper, or other support file.

Declare that evidence explicitly instead of asking CounterProof to infer a dependency graph:

```bash
counterproof witness \
  --base origin/main \
  --test-command "python -m pytest -q {tests}" \
  --test tests/existing_regression_test.py \
  --support-file fixtures/changed_case.json \
  --require-witness
```

CounterProof runs the selected test on HEAD, overlays the declared support file onto BASE, and runs the same test again. The receipt records `test_selection: explicit`. This path came from a real reviewer question where the test file itself was unchanged but the submitted fixture was what made the old behavior fail.

### Share a witness with a reviewer

A machine receipt is useful for automation; a reviewer needs the small set of facts they can check quickly.

```bash
counterproof share-witness REGRESSION_WITNESS.json \
  --integrity-file PROOF_INTEGRITY.json \
  --expected-head <current-pr-head-sha> \
  --source-url https://github.com/owner/repo/pull/123 \
  --runner-url https://github.com/owner/proof/actions/runs/456 \
  --out WITNESS_REVIEW_NOTE.md
```

The integrity file and candidate check are optional. Without them, the command remains backward-compatible with the witness-only reviewer note.

When `--expected-head` is supplied, CounterProof refuses to render the note if the receipt's exact `head_sha` belongs to an older candidate. This prevents a valid old replay from being silently presented as evidence for a newer PR HEAD.

When supplied, the note keeps the two evidence layers separate while putting them on one screen:

- exact HEAD / BASE commits and exit results;
- selected tests and any support files overlaid onto BASE;
- evidence digest and execution links;
- Proof Integrity status plus concrete changed evidence surfaces;
- the scope limit that a regression witness proves the tested before/after delta — not every claimed production cause or merge readiness.

### When two commits are not enough: CONTROL / BAD / REVERT

A BASE→HEAD witness shows that behavior changed. It does not, by itself, isolate the
intervention as the cause.

For a stronger controlled replay, CounterProof now has a three-candidate receipt:

```text
CONTROL     expected healthy state
BAD         intervention present
REVERT      intervention removed again

same oracle
same observation contract
same receipt semantics
```

Declare the candidate identities, evidence artifacts, frozen oracle, and expected
observations:

```bash
counterproof causal-replay examples/causal_replay/manifest.yml \
  --output CAUSAL_REPLAY_RECEIPT.json \
  --summary CAUSAL_REPLAY.md \
  --require-witness
```

A witnessed result requires at least one pre-registered observation with:

```text
CONTROL == REVERT != BAD
```

and every declared observation must match all three candidates. Each evidence file
is SHA-256 pinned, candidate identities must be distinct, evidence paths cannot escape
the manifest directory, and an optional `identity_path` can bind the declared
candidate identity to the evidence payload itself.

Rebuild the receipt later to detect either evidence or manifest drift:

```bash
counterproof verify-causal-replay-receipt CAUSAL_REPLAY_RECEIPT.json \
  --manifest examples/causal_replay/manifest.yml
```

This protocol grew out of the Bluefin #4539 CONTROL/BAD/REVERT QEMU experiment.
The historical Bluefin receipt remains frozen; the generic command is the reusable
path for new flagship causal replays.

### When one PR contains multiple review claims

A real PR can have one genuinely witnessed regression and several adjacent concerns that its tests do not exercise.

CounterProof's experimental claim matrix keeps those claims separate:

```bash
counterproof claim-matrix examples/claim_matrix/codex-plugin-cc-731.yml
```

The manifest is explicit. CounterProof does **not** use an LLM to invent claims or decide which product behavior is authoritative.

Each row now has four mechanical evidence dimensions:

```text
submitted-test evidence
  WITNESSED / NOT_WITNESSED / UNPROVEN

evidence scope
  IMPLEMENTATION < BEHAVIOR < SAFETY

oracle applicability
  APPLICABLE / PRECONDITION_MISSING

oracle alignment
  ALIGNED / CONTRADICTED / UNVERIFIED
```

The overall claim is derived conservatively. In particular:

```text
witnessed but scope too shallow
  -> WITNESSED (scope insufficient)

witnessed + oracle fixture prerequisite missing
  -> WITNESSED (oracle precondition missing)

witnessed + APPLICABLE + ALIGNED
  -> PROVEN

APPLICABLE + CONTRADICTED
  -> CONTRADICTED
```

A missing oracle prerequisite is **not** allowed to become a product contradiction.
That distinction came from a real GNOME/QEMU replay of Bluefin #4539: the first
keyring oracle assumed the synthetic CI account had a Secret Service `login`
collection, but that fixture prerequisite was absent.

That means a red→green regression can stay useful without silently becoming a
product-correctness claim, and an invalid fixture cannot manufacture a false red
product verdict.

Rows declaring `ALIGNED` or `CONTRADICTED` must cite both a nonblank
`oracle_probe` and an absolute HTTP(S) `oracle_source_url` that a reviewer can
inspect. CounterProof validates that provenance reference syntactically; it does
not fetch the URL, authenticate its owner, or decide that the cited source is
authoritative. The reference makes the assertion auditable rather than turning
free text into product truth.

Acceptance fixtures come directly from public reviewer / maintainer reality:

- `examples/claim_matrix/codex-plugin-cc-731.yml` — one witnessed submitted regression, later review concerns still unproven;
- `examples/claim_matrix/claude-code-89404.yml` — product-oracle contradiction stays stronger than an internally green submitted judge;
- `examples/claim_matrix/bluefin-4539.yml` — distinguishes shallow implementation evidence from behavior/safety claims and records an oracle precondition that is missing in the CI fixture;
- `examples/claim_matrix/clash-8017.yml` — binds behavior evidence to the exact historical replay candidate even after the live PR base moves;
- `examples/claim_matrix/scancode-2207.yml` — validates a claim-relevant behavior delta in a PostgreSQL/Django integration environment.

Those reality cases are also enforced together as a declarative contract suite:

```bash
counterproof reality-contracts examples/claim_matrix/reality-contracts.yml
```

The suite is intentionally cross-domain. A semantic change is rejected if it would, for example:

- turn Bluefin's missing fixture prerequisite into a contradiction;
- detach Clash evidence from the exact BASE that was actually replayed;
- weaken ScanCode's DB-backed behavior witness into an environment/setup failure;
- change a frozen receipt verdict without updating the explicit contract;
- swap the receipt's case, source run, candidate SHA, oracle revision, or other pinned provenance while keeping the same verdict;
- mutate any unlisted receipt content when the contract pins the receipt's Git blob identity.

Reality Contracts therefore protect both **meaning** and **evidence identity**. A matching verdict from a different receipt is not automatically the same proof.

They also track an explicit evidence lifecycle:

```text
CURRENT
SUPERSEDED
STALE
CONFLICTING
```

Lifecycle is orthogonal to claim truth. A historically valid proof does not become false merely because it is stale, but it must not be presented as current evidence for a changed candidate. `STALE`, `SUPERSEDED`, and `CONFLICTING` states require explicit provenance about why the evidence moved out of `CURRENT`.

CounterProof can also compare frozen candidates with the live upstream GitHub PR:

```bash
counterproof reality-freshness examples/claim_matrix/reality-contracts.yml
```

Freshness is reported separately from lifecycle:

```text
FRESH       frozen BASE/HEAD still match the live PR
DRIFTED     live BASE and/or HEAD moved
UNRESOLVED  the live check could not be interpreted; do not infer staleness
```

A `CURRENT` contract that is observed as `DRIFTED` requires an explicit lifecycle update to `STALE`. Stronger lifecycle states such as `SUPERSEDED` and `CONFLICTING` are never downgraded by a simple candidate-freshness check.

When multiple lifecycle signals apply at once, CounterProof merges them deterministically:

```text
SUPERSEDED > CONFLICTING > STALE > CURRENT
```

For example, an old receipt that has already been superseded stays `SUPERSEDED` even if its upstream PR later drifts; freshness cannot demote a stronger lifecycle conclusion.

When multiple evidence records exist for the same claim, CounterProof can resolve their relationship:

```bash
counterproof evidence-graph evidence.yml
```

The graph is conservative:

```text
newer PROVEN + same claim + equal/stronger scope
  -> SUPERSEDES older PROVEN evidence

PROVEN vs CONTRADICTED on the same claim
  -> CONFLICTS

either side still inconclusive
  -> PARALLEL

different claims
  -> UNRELATED
```

Only claim-directional outcomes (`PROVEN` and `CONTRADICTED`) participate in automatic supersession. A newer `WITNESSED (scope insufficient)`, `WITNESSED (oracle precondition missing)`, or other inconclusive result cannot silently retire an older proof.

Effective lifecycle decisions can be emitted as machine-readable receipts and independently verified against the exact frozen inputs. The explicit lifecycle workflow then signs `effective-lifecycle.json` with GitHub Artifact Attestations / Sigstore using `actions/attest@v4`.

```text
CounterProof verifier
  -> checks suite/graph blob identity and receipt consistency

GitHub artifact attestation
  -> binds the lifecycle receipt digest to the workflow identity
     and short-lived signing certificate
```

A downloaded lifecycle receipt can be checked both ways:

```bash
counterproof verify-lifecycle-receipt \
  effective-lifecycle.json \
  --suite examples/claim_matrix/reality-contracts.yml

gh attestation verify effective-lifecycle.json \
  --repo hippoley/CounterProof
```

Decision provenance is not a new claim oracle. It proves which evidence inputs, live candidate snapshot, and workflow produced the lifecycle decision; Claim Matrix semantics still decide claim truth.

---

## It also checks whether the PR changed the judge

A passing test is weaker evidence if the same PR also weakens the system that evaluates it.

CounterProof's **Proof Integrity Guard** surfaces changes such as:

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

CounterProof does not solve that by adding another model.

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

AI reviewers and CounterProof answer different questions.

| | AI reviewer | CounterProof |
|---|---|---|
| Main question | “Does this diff look suspicious?” | “Does this evidence distinguish before from after?” |
| Core input | code + model context | Git history + tests |
| Main output | suggestions / comments | replayable behavioral evidence |
| LLM required | usually | **no** for PR proof |
| Changed test/CI judge | not the core primitive | **explicitly surfaced** |
| Can refuse a story | model-dependent | **yes — weak/inconclusive evidence stays weak** |

Use CounterProof **next to** Claude Code, Codex, Copilot, Cursor, PR-Agent, or a human engineer.

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

### **[Open Live Proof Lab →](https://hippoley.github.io/CounterProof/)**

---

# The deeper runtime

Regression Witness is the smallest useful entry point.

CounterProof also contains an experimental runtime for **falsifiable agent self-improvement**.

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

CounterProof is allowed to return ambiguity.

**No winner is better than a fake winner.**

For the deeper architecture, see **[docs/COUNTERPROOF.md](docs/COUNTERPROOF.md)**.

---

## What is real today?

CounterProof keeps a runtime truth table instead of pretending roadmap items are finished.

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

## Break CounterProof

The highest-value contribution is a **counterexample**.

Can you make CounterProof:

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
+ actual CounterProof classification
+ why the difference matters
```

### Other valuable contributions

- runner adapters that preserve before/after semantics;
- real PR fixtures that break assumptions;
- integrity rules with low false-positive cost;
- better discriminating probes;
- adapters for real agent runtimes.

If CounterProof labels weak evidence as strong evidence, **that is a bug**.

---

## License

Apache-2.0.

---

<div align="center">

### **Green is a state. Proof is a relationship between before and after.**

**CounterProof**

*Claim nothing you can't replay.*

### **[▶ Open the Live Proof Lab](https://hippoley.github.io/CounterProof/)**

</div>
