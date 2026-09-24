# Reality Probe — CounterProof evidence inside Codex PROVE

Neighboring project:
https://github.com/yehyakin/codex-prove

CounterProof acceptance case:
https://github.com/hippoley/CounterProof/blob/main/examples/claim_matrix/codex-plugin-cc-731.yml

## Why these systems look complementary

Codex PROVE owns:

- Requirement IDs;
- task routing and ownership;
- final-candidate identity;
- required verification;
- Controller-only final review and PASS / FIX / BLOCKED.

CounterProof owns a narrower question:

> for one claimed property, what does the submitted executable evidence actually establish before vs. after the change?

The useful composition should therefore **not** give CounterProof final approval authority.

## Manual handoff

Suppose the PROVE Controller defines:

```yaml
done_when:
  - id: REQ-1
    criterion: "Cross-plugin-data durable review state must not fail open"
    evidence: "A regression test that distinguishes the pre-fix and post-fix behavior"

  - id: REQ-2
    criterion: "Durable config replacement preserves the previous valid file on write failure"
    evidence: "A failure-injection test exercising interrupted/failed replacement"
```

CounterProof can return:

```yaml
counterproof:
  source_pr: https://github.com/openai/codex-plugin-cc/pull/731
  base_sha: db52e28f4d9ded852ab3942cea316258ae4ef346
  head_sha: a81f52f9c2c366d7d5e095179d2473a9f7e12798
  runner: https://github.com/hippoley/CounterProof/actions/runs/35952687043
  digest: sha256:01c447fbfca700a6dcbfcec2753ca3c55a0760b5b6200a751d44a948bdbf5c97

  claims:
    - requirement: REQ-1
      submitted_test_evidence: WITNESSED
      oracle_alignment: UNVERIFIED
      overall: WITNESSED (submitted judge)
      tests:
        - tests/runtime.test.mjs
        - tests/state.test.mjs

    - requirement: REQ-2
      submitted_test_evidence: UNPROVEN
      oracle_alignment: UNVERIFIED
      overall: UNPROVEN
```

## Proposed Controller interpretation

CounterProof should not translate either row directly into PROVE's overall verdict.

The Controller would still compare each row with the **required evidence** it declared before dispatch.

For the example above:

```text
REQ-1 required evidence:
  red→green submitted regression

CounterProof:
  WITNESSED (submitted judge)

Controller:
  evidence requirement may be satisfied
  product/oracle correctness is still not implied


REQ-2 required evidence:
  failure-injection replacement test

CounterProof:
  UNPROVEN

Controller:
  requirement remains unsatisfied
  overall PASS is impossible
```

If the original `done_when` instead required alignment with an authoritative product oracle, then `WITNESSED (submitted judge)` would be insufficient for REQ-1 too.

## Boundary

This handoff preserves both projects' current authority model:

```text
CounterProof
  classifies evidence scope
      ↓
Codex PROVE Controller
  checks that evidence against predeclared REQ-ID requirements
      ↓
PASS / FIX / BLOCKED
```

CounterProof does not route workers, own files, authorize writes, or approve the task.

Codex PROVE does not need to re-infer whether a BASE process failure was behavioral, whether the submitted judge changed, or whether an oracle was contradicted if a deterministic evidence artifact already records that boundary.

## Question

Is this evidence handoff compatible with PROVE's “verify the verifier” contract?

The important design question is whether an external verifier should be represented as:

1. ordinary `Evidence:` attached to a Requirement ID; or
2. a distinct evidence-quality packet that the Controller checks before accepting the underlying test/build result.

No integration code is proposed until that boundary is clear.
