# Real external execution receipt — agent-done-or-not v0.13.1

This fixture is the first real producer-generated execution receipt used for the
CounterProof ↔ agent-done-or-not handoff discussed in CounterProof #82.

The producer was frozen at annotated tag `v0.13.1`:

```text
tag object:      34bb41a35e96d544a9a17365d694214b1e75e413
resolved commit: 4a801bf056519af5a845e773260ef23796eea3ff
done-gate.sh:
  sha256:6f8a6fd1dad47d806d3be0ba98ca5723be4b7569c08c01e821a3eff63fb4eb2c
proof.schema.json:
  sha256:865db35fd05cc89de305022427cd9f6e96cdefde9ee2fd112059da323b4091ef
```

The producer re-executed two CounterProof unit suites in GitHub Actions run
`37711284061`. Fourteen tests passed, and the producer emitted a v2 execution
receipt with:

- exact repo / commit / tree;
- clean working-tree state;
- exact command;
- exit code;
- output SHA-256;
- producer version;
- verifier identity;
- `disposition = reexecuted`.

CounterProof's consumer is intentionally narrower than a verdict engine. It may
admit this record as external execution evidence input, but it must not call the
candidate fixed or correct merely because the command passed.
