# Third-party physical-completion criterion parity probe

This bounded, **independent consumer** checks the exact 14-entry `criterionMet`
table published by `probityai/agent-evidence-vectors` after hippoley's
missing/null-to-false correction on PR #554.

Pinned external inputs (not a released version):
- Repository: `probityai/agent-evidence-vectors`
- Commit: `8da583e977147edfdb588b074e01e3a2dd21c9b0`
- File: `corpusreaders/testdata/physical-completion-criterion.json`
- Source Git blob: `9110d9f5f9907c4c0a18ca64c62f8ae7815cf99a`
- Upstream review: https://github.com/probityai/agent-evidence-vectors/pull/554
- Discussion and credit: https://github.com/probityai/agent-evidence-vectors/issues/80

The local file is a frozen copy of that upstream JSON. `replay.py` uses no
producer code or dependencies and independently returns `decision`, `reason`
and `owed` for the subset's post-verification reporting rules. It deliberately
does not authenticate observations, verify signatures, establish a real
witness, test freshness or reimplement the entire 48-member corpus.

```sh
cd examples/interop/probityai-criterion-parity
python -m unittest -v test_replay.py
```

## Boundaries

- `absent` and explicit JSON `null` are **not** `false`.
- A negative finding requires an explicit negative observation.
- Controller success with an explicit negative witness produces a conflict
  instead of silently erasing either claim.
- Proposal-only reasons remain **ambiguous** where the pinned draft does not
  supply a normative result. No SCITT conformance or physical-completion proof
  is asserted.
- This is a frozen candidate at the commit above. Upstream #554 was still
  open and conflicted at the time of the snapshot; do not claim v1 adoption or
  released compatibility without independently replaying a tagged release.
