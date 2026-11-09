# ExecSurface #164: stdout privacy boundary — reproducible review note

Status: **source-level finding, not yet independently reproduced or upstream-qualified**.

External intake: https://github.com/AETHERXGLOBAL/execsurface/issues/164

## Exact boundary

In `AETHERXGLOBAL/execsurface`, `scripts/p8_a3_external_trial_capture.py` uses
`subprocess.run(..., stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)`
for the helper `run_text`, but the **observe** subprocess is invoked with
`subprocess.run([... "observe", "--evidence-output", ...], cwd=workdir, check=False)`
without capturing stdout/stderr. This inherits the caller's streams.

The guide tells evaluators to inspect `typed-evidence.json` before sharing.
That instruction cannot protect any path-bearing content printed by the
observe subprocess into a public CI log *before* inspection.

The initial independent CounterProof trial reported the observation in #164,
while preserving the five passing stages and bounded consumer verdict.
Do not interpret that result as AETHER X qualification or endorsement.

## Minimal falsification probe (local, synthetic; no secrets)

The following standalone Python reproduces the **subprocess stream inheritance
mechanism**, not an ExecSurface binary run:

```python
import subprocess
import sys

secret_marker = "SYNTHETIC_PATH_MARKER_DO_NOT_PUBLISH"
command = [sys.executable, "-c", f"print({secret_marker!r})"]

# Equivalent to observe-stage invocation: marker reaches parent stdout/CI log.
subprocess.run(command, check=True)

# Proposed containment: marker is not inherited by parent stdout.
result = subprocess.run(
    command, check=True, stdout=subprocess.PIPE,
    stderr=subprocess.PIPE, text=True,
)
assert secret_marker in result.stdout
assert result.returncode == 0
```

## Candidate minimal producer-side change

Capture `observe` stdout/stderr at the **trial harness boundary**, without
printing raw captured bytes or retaining them in public summary artifacts.
Keep `observe_exit_code`, `evidence_sha256`, consumer validation, and the
first-result preservation rules unchanged. For high-volume output, prefer
private temporary files with explicit permissions or bounded streaming over
unbounded in-memory `PIPE` capture. A failure should report a sanitized
error code and pointer to private diagnostics, never the raw stream.

## Regression contract

1. A synthetic observed command emits a recognizable path marker to stdout
   and stderr. Neither marker reaches the public job log.
2. The same command's exit code and typed-evidence generation remain intact.
3. A nonzero observed command still preserves the initial failed summary.
4. Consumer validation still reads the generated evidence file.
5. No raw output is silently promoted into `trial-summary.json` or
   `consumer-report.json`.

## Honest evidence boundary

This is an upstream-facing reproduction note, **not** a claim that the fix
was merged, that the CI log has been remediated, or that #164 has been
qualified. Recheck the upstream harness at the current commit before applying
any patch: a later upstream revision may already fix this.
