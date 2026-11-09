# ExecSurface #164: stdout privacy boundary — upstream remediation verified

Status: **original raw-stream leak reported; upstream remediation merged; typed-evidence path exposure remains a separate boundary**.

External intake: https://github.com/AETHERXGLOBAL/execsurface/issues/164

## Original finding

The earlier `scripts/p8_a3_external_trial_capture.py` observe invocation inherited
the caller's stdout/stderr. A path-bearing observe message could therefore reach
a public CI log before the evaluator inspected `typed-evidence.json`.

This was reported in ExecSurface issue #164. It was a source-level finding and
a synthetic subprocess reproduction, not a claim of product qualification.

## Upstream remediation

The producer maintainer merged [ExecSurface PR #184](https://github.com/AETHERXGLOBAL/execsurface/pull/184)
at commit `6d24e5975dfa86a33d6bf316ece0f8103d3c922e` on 2026-10-08.

The current upstream source
[`scripts/p8_a3_external_trial_capture.py`](https://github.com/AETHERXGLOBAL/execsurface/blob/main/scripts/p8_a3_external_trial_capture.py)
has blob SHA `10cce99c076d7f70cd4087c8cb12275258108f9a`. Its
`run_privacy_bounded()` helper now invokes child commands with both
`stdout=subprocess.DEVNULL` and `stderr=subprocess.DEVNULL`, returning the
exit status without retaining or forwarding raw child output.

This closes the original inherited-stream path for commands run through that
helper. It does **not** mean all evidence is path-free: the current harness
explicitly records `typed_effect_may_contain_paths: true` in its privacy
policy. Typed evidence still needs inspection and sanitization before sharing.

## Synthetic regression boundary

`tests/unit/test_execsurface_stdout_boundary.py` tests the Python subprocess
stream-containment mechanism with synthetic markers only. It does not import
the upstream harness, execute an ExecSurface binary, or prove the producer
implementation end-to-end. The upstream source/merge commit above is the
separate source-level remediation evidence.

## What this does and does not establish

Established:
- The original observe-stage stdout/stderr inheritance was reported.
- Upstream PR #184 merged a helper that sends both streams to `DEVNULL`.
- The current public source contains that helper.

Not established:
- That every producer code path uses `run_privacy_bounded()`.
- That typed evidence is free of filesystem paths or other sensitive values.
- That the external workload was qualified, or that AETHER X GLOBAL endorses
  CounterProof.

The original #140 Residual-Necessity run and the separate #164 privacy trial
remain distinct evidence records and must not be combined.
