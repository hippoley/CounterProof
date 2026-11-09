# Raw agent-done v2 capture evidence — 2026-11-09

This fixture preserves exact producer bytes from a fresh run of
`mohamedzhioua/agent-done-or-not@v0.13.1`.

## What was run

- Command: `python -m pytest -q tests/unit/test_conformance_receipt.py tests/unit/test_external_state_freshness.py`
- Result: 14 passed, exit code 0.
- Producer disposition: `reexecuted`.
- Receipt kind: **capture**, not `review-pr`.

## Exact-byte preservation

- `receipt.json` is the exact final JSONL receipt line copied from `ledger.jsonl`.
- `counterproof-unit.log` is the exact captured output file.
- The receipt's `sha256` equals the SHA-256 of the preserved output log.
- `ledger.sha256` and `log.sha256` pin the preserved bytes.
- `provenance.json` pins the producer tag object, resolved commit, producer script/schema digests, GitHub workflow run, artifact ID/digest, and expiry.

## Commit semantics

The run occurred on GitHub's synthetic `refs/pull/206/merge` preview. The receipt's
`commit` (`5a5b6b9…`) is the merge-preview commit, **not** the PR head or base.
`capture-context.json` separately records:
- PR head: `6cc6068…`
- PR base: `7f57d31…`

Do not use the receipt's `commit` as a BASE or HEAD identity for a later
BASE→HEAD evaluation.

## Trust boundary

The receipt is unsigned. `verifier` and `ci` are producer-supplied labels, not
attestations. The GitHub Actions run and retained artifact provide the external
execution provenance; they do not make the receipt cryptographically authentic.
A passing test run is execution evidence, not proof that the test suite is an
authoritative oracle for any downstream product claim.
