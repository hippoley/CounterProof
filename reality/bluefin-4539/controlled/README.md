# Controlled Bluefin #4539 causal replay

This is deliberately **not** presented as an exact historical image replay.

The original May 2026 Bluefin output images and their pinned `silverblue-main`
base digests are no longer available from GHCR. The controlled experiment
therefore freezes one currently retrievable Bluefin OCI image and changes only
the intervention under test.

Frozen control:

```text
ghcr.io/ublue-os/bluefin@sha256:76aa5d6f4f2f3e18b244587bfbd45ae1777a7d0934f869534228eab6af1f0101
```

Candidates:

```text
CONTROL = frozen image unchanged
BAD     = CONTROL + historical 30-after-keyring.conf
REVERT  = BAD - that exact drop-in
```

All three candidates run the same real GNOME/QEMU oracle sourced from
`reality/bluefin-4539-testsuite-overlay`:

```text
GNOME session ready
→ org.freedesktop.secrets reachable
→ ReadAlias("login")
→ login collection Locked == false
```

Interpretation:

- CONTROL pass / BAD fail / REVERT pass = strong controlled causal witness.
- all pass = the historical regression does not reproduce on the current
  environment; keep historical behavior inconclusive.
- infrastructure/setup failure = inconclusive, never behavioral evidence.


## Published flagship receipt

The strongest frozen artifact from the successful controlled replay is:

- [Flagship causal receipt](../../../examples/claim_matrix/receipts/bluefin-4539-flagship-causal.json)
- source workflow run: https://github.com/hippoley/CounterProof/actions/runs/37412091382
- oracle revision: `1c0a23317d420b77396770ae2a8fdf71804cde4e`
- upstream QEMU workflow revision: `a99ca5ea0553f778a74f5d5152fefbbb47d86da4`

The flagship receipt keeps runtime execution success separate from the behavioral candidate signature and records the causal scope explicitly as `CONTROLLED_CAUSAL`.
