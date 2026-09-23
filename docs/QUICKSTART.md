# Counterproof in 60 seconds

> Your agent says it fixed the bug. Prove it.

## 1. Install

```bash
pip install counterproof
```

## 2. Generate the GitHub workflow

From the repository root:

```bash
counterproof init-github \
  --require-witness \
  --require-clean-integrity
```

Counterproof detects common test runners and writes:

```text
.github/workflows/counterproof.yml
```

If detection is wrong:

```bash
counterproof init-github \
  --test-command "python -m pytest -q {tests}" \
  --require-witness
```

## 3. Open an agent-generated PR with a regression test

Counterproof takes the tests changed by the PR and asks two questions:

```text
Do the changed tests pass on the PR head?
                 ↓ yes
Do the same tests fail on the pre-change code?
                 ↓ yes
          REGRESSION WITNESSED
```

At the same time it checks whether the PR changed its own judge:

```text
deleted tests
skip / xfail
continue-on-error
|| true
PR workflow trigger removal
test / coverage / CI config changes
```

## 4. Read one sticky PR proof

The PR receives one updateable proof instead of comment spam:

```text
COUNTERPROOF · REGRESSION WITNESS

WITNESSED

PR head                  PASS
Base code + PR tests     FAIL

Proof Integrity          CLEAN
```

That is the first value loop. No LLM, API key or server is required.

## CLI-only usage

```bash
counterproof witness \
  --base origin/main \
  --test-command "python -m pytest -q {tests}" \
  --require-witness

counterproof integrity \
  --base origin/main \
  --fail-on-high-risk
```

## What comes after

Regression Witness is the lightweight entry point.

The deeper Counterproof runtime can then handle:

```text
failure
→ competing hypotheses
→ pre-registered predictions
→ controlled interventions
→ diagnostic probes
→ guarded selection
→ structured evidence
→ Proof Receipt
```

Start with proof-of-fix. Add causal debugging only when you need it.
