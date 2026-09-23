# Counterproof Proof Protocol v1

Counterproof's human-facing PR card is useful for review. The machine contract is
`PROOF_SUMMARY.json`.

Use this contract when another tool needs to consume Counterproof evidence without
parsing Markdown, log text, or GitHub comments.

## Contract

Export the schema:

```bash
counterproof schema proof-summary-v1 --out proof-summary.schema.json
```

A valid summary looks like:

```json
{
  "schema_version": 1,
  "witness_status": "witnessed",
  "evidence_mode": "precise",
  "integrity_status": "clean",
  "proof_status": "verified",
  "proof_ready": true,
  "reasons": [
    "The exact changed tests pass on PR head, fail on base, and the evidence surface is clean."
  ]
}
```

## Status semantics

| proof_status | Meaning | proof_ready |
|---|---|---:|
| `verified` | exact changed-test witness + clean evidence surface | true |
| `review-required` | PR changed tests/CI evidence machinery | false |
| `suite-delta` | full suite distinguishes base from head, but changed test was not isolated | false |
| `unproven` | configured evidence also passes on base | false |
| `head-failing` | configured evidence fails on PR head | false |
| `no-changed-tests` | no changed regression test detected | false |
| `inconclusive` | replay did not produce a trustworthy verdict | false |
| `integrity-unknown` | witness exists but integrity result is unavailable/unknown | false |
| `unknown` | unrecognized or unavailable evidence state | false |

## VERIFIED invariant

`proof_ready=true` is deliberately narrow.

It is valid only when all of the following are true:

```text
witness_status   = witnessed
evidence_mode    = precise
integrity_status = clean
proof_status     = verified
proof_ready      = true
```

The JSON Schema enforces this invariant.

## What VERIFIED does not mean

`verified` means Counterproof's configured behavioral evidence contract was
satisfied. It does **not** mean:

- the entire pull request is secure;
- every requirement was tested;
- the inferred root cause is uniquely proven;
- deployment is safe;
- a human review is unnecessary.

Counterproof is designed to make one class of evidence stronger, not to replace
the rest of software assurance.

## GitHub Action outputs

The root Action exposes:

```text
status
evidence-mode
integrity-status
proof-status
proof-ready
summary-json-path
```

Example:

```yaml
- id: counterproof
  uses: hippoley/SkillFactory@main
  with:
    test-command: "python -m pytest -q {tests}"

- if: steps.counterproof.outputs.proof-ready == 'true'
  run: echo "Counterproof evidence contract satisfied"
```

For an aggregate gate:

```yaml
- uses: hippoley/SkillFactory@main
  with:
    test-command: "python -m pytest -q {tests}"
    require-proof-ready: "true"
```

Or generate it:

```bash
counterproof init --strict
```

## Why this matters for self-evolving agents

A self-improving system should not learn from every successful-looking run.

A safe promotion loop can consume `proof_ready` as one required signal:

```text
agent change
  ↓
Counterproof evidence
  ↓
PROOF_SUMMARY.json
  ↓
proof_ready?
  ├─ false → do not learn / do not promote
  └─ true  → eligible for the next review or rollout gate
```

That is intentionally **eligibility**, not automatic promotion.

The deeper Counterproof runtime can then add competing hypotheses, diagnostic
probes, Proof Receipts, and later rollout evidence without changing the meaning
of Proof Protocol v1.
