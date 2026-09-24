# Reality Probe — continuedev/continue #12576

External PR: https://github.com/continuedev/continue/pull/12576

Independent runner: https://github.com/hippoley/CounterProof/actions/runs/35972260870

## Result

**WITNESSED**

The PR's changed Vitest file passes on the PR head and fails when the exact same changed test is replayed against the pre-change base code.

- Head commit: `0f2e62e54b6f5bc2bc749e22e15b0dd5342bde2a`
- Base commit: `a3076b444af3fb0d9fd3805c10f75177d8f70137`
- Test: `core/config/profile/doLoadConfig.vitest.ts`
- Result protocol: `json-v1`
- HEAD: behavioral **PASS** — 5/5 tests passed
- BASE + same changed test: behavioral **FAIL** — 4/5 passed, 1 failed
- Evidence digest: `sha256:23b69b350eb966d65faf9616af31eb6c961a765e4db2672083cde7ca336b6866`

## Assertion-level result

The failing BASE assertion is the PR's primary migration case:

`doLoadConfig tabAutocompleteModel migration should transform a JSON-style tabAutocompleteModel object into a roles-based model entry`

On BASE, Vitest reports:

```text
expected 'name: My Config ...' not to contain 'tabAutocompleteModel'
```

The other four assertions in the changed test file still pass on BASE.

A second clean replay reproduced the same semantic result:

- HEAD: 5/5 passed
- BASE + same changed test: 4/5 passed, 1 failed

Second runner:
https://github.com/hippoley/CounterProof/actions/runs/35975618130

## What this establishes

The regression coverage added by #12576 is not merely green on the proposed implementation.

At least one assertion in the changed test file distinguishes the PR from the exact pre-change base, while the rest of the file continues to pass.

That gives the migration change a real before/after regression witness.

## What it does not establish

This receipt does **not** say the whole PR is ready to merge.

It does not independently prove every YAML edge case, every config shape, long-term backwards compatibility, or maintainer policy/design acceptance.

It proves one narrower statement:

> the submitted regression test file contains behavior that passes after #12576 and fails before it.

## Reproducibility note

The external repository is a TypeScript monorepo. The probe used Continue's Node version and built the local packages before running the changed core Vitest file.

CounterProof used a structured Vitest adapter so setup/build failures could not be mistaken for behavioral regression evidence.
