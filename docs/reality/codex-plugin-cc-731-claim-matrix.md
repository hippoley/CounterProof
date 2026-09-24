# Claim / Evidence Matrix — openai/codex-plugin-cc #731

Source PR: https://github.com/openai/codex-plugin-cc/pull/731

Human review context: https://github.com/openai/codex-plugin-cc/pull/731

This matrix is a manual Reality Probe shaped by external reviewer feedback.

## Execution provenance

- HEAD: `a81f52f9c2c366d7d5e095179d2473a9f7e12798`
- BASE: `db52e28f4d9ded852ab3942cea316258ae4ef346`
- changed tests:
  - `tests/runtime.test.mjs`
  - `tests/state.test.mjs`
- CounterProof replay: https://github.com/hippoley/CounterProof/actions/runs/35952687043
- evidence digest: `sha256:01c447fbfca700a6dcbfcec2753ca3c55a0760b5b6200a751d44a948bdbf5c97`

## Claim / evidence matrix

| Review claim / failure mode | Exact evidence | BASE | HEAD | Submitted-test evidence | Oracle alignment | Overall claim |
|---|---|---:|---:|---|---|---|
| Cross-`CLAUDE_PLUGIN_DATA` state must not fail open when the durable review gate is read from a different plugin-data location | `tests/runtime.test.mjs`, `tests/state.test.mjs` | **FAIL** | **PASS** | **WITNESSED** | **UNVERIFIED** | **WITNESSED (submitted judge)** |
| Durable config file should use restrictive permissions such as `0600` | No changed test exercises mode bits | — | — | **UNPROVEN** | **UNVERIFIED** | **UNPROVEN** |
| Replacement should be atomic / preserve the previous valid config if a write is interrupted or fails | No changed test injects replacement/write failure | — | — | **UNPROVEN** | **UNVERIFIED** | **UNPROVEN** |

## Assertion / failure excerpt

The before/after replay establishes the original authority-boundary regression relative to the submitted tests.

On BASE, the changed tests report the old behavior where the expected durable review state is not preserved across the plugin-data boundary. On HEAD, both changed test files pass.

The later reviewer concerns about file permissions and atomic replacement have no corresponding changed assertion.

## Reviewer-facing conclusion

```text
original authority-boundary regression
  submitted-test evidence  WITNESSED
  oracle alignment         UNVERIFIED
  overall                  WITNESSED (submitted judge)

restrictive file permissions
  submitted-test evidence  UNPROVEN
  oracle alignment         UNVERIFIED
  overall                  UNPROVEN

atomic replacement / failure preservation
  submitted-test evidence  UNPROVEN
  oracle alignment         UNVERIFIED
  overall                  UNPROVEN
```

A red→green submitted-test witness is evidence for the first row only. It is not product-level correctness while oracle alignment remains UNVERIFIED.
