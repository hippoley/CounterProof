# CounterProof → Codex PROVE: runnable evidence handoff

Neighbor project: https://github.com/yehyakin/codex-prove

This example follows the boundary suggested by the Codex PROVE maintainer:

> attach CounterProof output to the relevant REQ-ID as ordinary Evidence; keep the PROVE Controller responsible for deciding whether that evidence satisfies the requirement.

No new packet type or integration layer is introduced here.

## 1. Generate the CounterProof artifact

From the CounterProof repository:

```bash
counterproof claim-matrix \
  examples/claim_matrix/codex-plugin-cc-731.yml \
  --out /tmp/CLAIM_EVIDENCE_MATRIX.md \
  --json-out /tmp/CLAIM_EVIDENCE_MATRIX.json
```

The source manifest is a real public case:

- PR: https://github.com/openai/codex-plugin-cc/pull/731
- BASE: `db52e28f4d9ded852ab3942cea316258ae4ef346`
- HEAD: `a81f52f9c2c366d7d5e095179d2473a9f7e12798`
- runner: https://github.com/hippoley/CounterProof/actions/runs/35952687043
- digest: `sha256:01c447fbfca700a6dcbfcec2753ca3c55a0760b5b6200a751d44a948bdbf5c97`

## 2. Bind one CounterProof row to one PROVE requirement

Suppose the PROVE Controller declared:

```yaml
done_when:
  - id: REQ-1
    criterion: "Cross-plugin-data durable review state must not fail open"
    evidence: "A regression test that distinguishes pre-fix from post-fix behavior"

  - id: REQ-2
    criterion: "Failed config replacement preserves the previous valid file"
    evidence: "A failure-injection test for interrupted/failed replacement"
```

The generated CounterProof matrix contains:

```text
REQ-1-shaped claim:
  submitted-test evidence  WITNESSED
  oracle alignment         UNVERIFIED
  overall                  WITNESSED (submitted judge)

REQ-2-shaped claim:
  submitted-test evidence  UNPROVEN
  oracle alignment         UNVERIFIED
  overall                  UNPROVEN
```

## 3. Put the artifact into PROVE's existing worker/result vocabulary

No special CounterProof packet is required.

A PROVE result can reference the generated artifact directly:

```text
Task ID: verify-regression-evidence
Status: PASS
Summary: Generated CounterProof claim/evidence artifact for the final candidate.
Inspected:
  - examples/claim_matrix/codex-plugin-cc-731.yml
Changed: None

Requirement coverage:
  REQ-1:
    evidence:
      artifact: /tmp/CLAIM_EVIDENCE_MATRIX.md
      BASE: db52e28f4d9ded852ab3942cea316258ae4ef346
      HEAD: a81f52f9c2c366d7d5e095179d2473a9f7e12798
      tests:
        - tests/runtime.test.mjs
        - tests/state.test.mjs
      submitted_test_evidence: WITNESSED
      oracle_alignment: UNVERIFIED
      overall_claim: WITNESSED (submitted judge)
      digest: sha256:01c447fbfca700a6dcbfcec2753ca3c55a0760b5b6200a751d44a948bdbf5c97
      scope_limit:
        "This proves the submitted regression distinguishes BASE from HEAD.
         It does not prove product-oracle correctness."

  REQ-2:
    evidence:
      artifact: /tmp/CLAIM_EVIDENCE_MATRIX.md
      submitted_test_evidence: UNPROVEN
      oracle_alignment: UNVERIFIED
      overall_claim: UNPROVEN
      scope_limit:
        "No submitted failure-injection test exercises this requirement."

Verification:
  counterproof claim-matrix examples/claim_matrix/codex-plugin-cc-731.yml
  -> artifact generated successfully

Evidence:
  /tmp/CLAIM_EVIDENCE_MATRIX.md
  /tmp/CLAIM_EVIDENCE_MATRIX.json

Assumptions:
  - CounterProof does not decide whether either REQ-ID is satisfied.
  - The PROVE Controller still verifies candidate identity and evidence quality.

Risks:
  - REQ-1 product-oracle alignment remains UNVERIFIED.
  - REQ-2 remains UNPROVEN.

Failure class: none
Blocker: None
```

## 4. Controller interpretation stays inside PROVE

The PROVE Controller still compares the artifact to the evidence contract it declared before execution.

For this example:

```text
REQ-1
required evidence:
  red→green submitted regression

CounterProof:
  WITNESSED (submitted judge)

Controller:
  may mark the regression-evidence requirement satisfied
  must not infer product-oracle correctness


REQ-2
required evidence:
  failed-write / interruption test

CounterProof:
  UNPROVEN

Controller:
  requirement remains unsatisfied
  overall PASS is impossible
```

If REQ-1 had instead required agreement with an authoritative product oracle, then `WITNESSED (submitted judge)` would also be insufficient.

## Why this handoff stays small

CounterProof does not:

- create REQ-IDs;
- route workers;
- own files;
- authorize writes;
- return PROVE's final `PASS / FIX / BLOCKED`.

Codex PROVE does not need CounterProof-specific orchestration.

The composition is only:

```text
CounterProof artifact
        ↓
ordinary REQ-ID Evidence
        ↓
PROVE Controller verifies the verifier
        ↓
PASS / FIX / BLOCKED
```

That keeps CounterProof useful as a verifier input without turning it into another controller.
