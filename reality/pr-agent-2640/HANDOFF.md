# Reality Probe — CounterProof → PR-Agent artifact handoff

Related PR-Agent issue:
https://github.com/The-PR-Agent/pr-agent/issues/2640

Independent handoff run:
https://github.com/hippoley/CounterProof/actions/runs/35984022875

PR-Agent commit:
`eb15fc225ee39c341a1647bfb8db2139a15fbb2f`

## Question

Can CounterProof's deterministic claim/evidence output enter PR-Agent's existing review path **without a custom integration**?

## Input

CounterProof generated its existing #731 acceptance fixture with:

```bash
counterproof claim-matrix \
  examples/claim_matrix/codex-plugin-cc-731.yml \
  --out CLAIM_EVIDENCE_MATRIX.md
```

That artifact contains, among other rows:

```text
authority-boundary regression:
  submitted-test evidence = WITNESSED
  oracle alignment        = UNVERIFIED
  overall                 = WITNESSED (submitted judge)

restrictive permissions:
  submitted-test evidence = UNPROVEN
  overall                 = UNPROVEN

atomic replacement:
  submitted-test evidence = UNPROVEN
  overall                 = UNPROVEN
```

## Existing PR-Agent surface

No PR-Agent source change was used.

The probe set:

```text
ARTIFACT_PATH=CLAIM_EVIDENCE_MATRIX.md
```

and invoked PR-Agent main's real `inject_artifact_context()` / `load_artifact()`.

## Result

**HANDOFF CONFIRMED**

PR-Agent reported:

```text
Injected artifact context into tools:
  pr_reviewer
  pr_description
  pr_code_suggestions
```

The probe then verified each target's `extra_instructions` contained both:

- `WITNESSED (submitted judge)`
- `UNPROVEN`

Machine receipt:

```json
{
  "pr_agent_commit": "eb15fc225ee39c341a1647bfb8db2139a15fbb2f",
  "counterproof_artifact": "CLAIM_EVIDENCE_MATRIX.md",
  "targets": {
    "pr_reviewer": {
      "contains_counterproof_matrix": true,
      "contains_unproven_boundary": true
    },
    "pr_description": {
      "contains_counterproof_matrix": true,
      "contains_unproven_boundary": true
    },
    "pr_code_suggestions": {
      "contains_counterproof_matrix": true,
      "contains_unproven_boundary": true
    }
  },
  "result": "handoff-confirmed"
}
```

## What this does not prove

This run does not use an LLM and does not claim that PR-Agent will always interpret the artifact correctly.

It proves only the handoff contract:

> CounterProof can produce a deterministic evidence boundary and PR-Agent can already carry that artifact into its review prompts with no dedicated integration code.

## Why #2640 is interesting

PR-Agent #2640 asks for CI-failure analysis and relatedness judgement across many jobs.

A possible division of labor is:

```text
raw CI / replay evidence
        ↓
CounterProof
deterministic claim / evidence boundary
        ↓
PR-Agent [artifacts]
language-model review / explanation
        ↓
human reviewer
```

The question is whether this split reduces false confidence compared with asking the model to infer both the evidence semantics and the explanation from raw logs.
