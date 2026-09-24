# Reality Probe — rundef/async_rithmic #53

External PR: https://github.com/rundef/async_rithmic/pull/53

CounterProof replay run: https://github.com/hippoley/CounterProof/actions/runs/35947453810

## Result

**WITNESSED**

The PR's changed regression test passes on the PR head and fails when the exact same test file is replayed against the pre-change base code.

- Head commit: `4fca039e9041f5ba256f5c3bf9887267b3998572`
- Base commit: `0b73330ba5dd1b9e7118d42168c73ebcd3c8b67e`
- Test: `tests/test_order_terminal_response.py`
- Command: `python -m pytest -q tests/test_order_terminal_response.py`
- HEAD exit: `0`
- BASE exit: `1`
- Evidence digest: `sha256:bd917b1739406ad79a93fcf9080d72c5fde8ad6e4dab2bc8d30162fcde95a9ff`

## What happened

On HEAD:

- `test_terminal_only_order_ack_is_stored` — PASS
- `test_concurrent_terminal_only_acks_all_stored` — PASS
- `test_genuine_absence_still_times_out` — PASS

On BASE with the PR test overlaid:

- `test_terminal_only_order_ack_is_stored` — FAIL: terminal-only 313 ack is dropped
- `test_concurrent_terminal_only_acks_all_stored` — FAIL: all six terminal-only acks are dropped
- `test_genuine_absence_still_times_out` — PASS

This is stronger than “the new test is green”: the same changed test distinguishes the old and new code.

## Environment note

The first clean run exposed a reproducibility wrinkle: `pyproject.toml`'s `test` extra declares pytest but not `pytest-asyncio`, while the repository CI installs `pytest-asyncio` separately. The final replay matched that CI environment before producing the witness.

## Scope / non-claim

This proves the code-level regression delta exercised by this test. It does **not** independently prove that the live prop-firm incident had exactly this causal mechanism, nor that every order-path behavior is correct.
