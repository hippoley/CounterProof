# cachy-app #2279 — historical red→green witness

Target: https://github.com/mydcc/cachy-app/pull/2279

Upstream evidence gap: PRTruth Manual Oracle Batch 29 kept the requirement

> malicious-icon component regression passes now **and was failing before the fix**

unproven as a whole because exact-head green CI established only the after-state. No machine-readable before-state execution evidence was available.

## Candidate binding

- HEAD: `4b7240a8a407565bc668127ffbbc754c5cec3de5`
- BASE: `6f86b2b67d28c958c412a9269d7155caf628aec0`
- submitted test: `src/components/shared/DashboardNav.xss.component.test.ts`
- runner: Vitest under Node 22
- trusted run: https://github.com/hippoley/CounterProof/actions/runs/36223614032

The target PR did not modify `package.json`, `package-lock.json`, or the Vitest configuration. The replay therefore reused the same installed dependency graph while changing only the repository candidate plus the submitted test transplant required to ask the historical question.

## Replay

HEAD:

```text
Test Files  1 passed (1)
Tests       3 passed (3)
```

BASE, with the exact submitted test transplanted unchanged:

```text
Test Files  1 failed (1)
Tests       2 failed | 1 passed (3)
exit        1
```

The two BASE failures are the hostile-markup assertions:

- `strips event handlers from an icon prop`
- `strips script elements and javascript: URLs from an icon prop`

The behavior-preservation guard remained passing.

## Evidence classification

```text
submitted-test evidence  WITNESSED
HEAD                     PASS
BASE                     FAIL
scope                    historical red→green property of this test
```

This does **not** prove the whole pull request or every acceptance criterion. It establishes only the before/after execution fact that PRTruth Batch 29 intentionally left unproven from current-head CI alone.

The temporary probe PR was closed without merge after the trusted run completed:
https://github.com/hippoley/CounterProof/pull/67

An interop boundary question is open with PRTruth:
https://github.com/eissasoubhi/PRTruth/issues/361
