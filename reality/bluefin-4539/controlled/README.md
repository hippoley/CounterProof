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


The workflow now publishes two receipts from the same QEMU artifacts:

- the original Bluefin-specific controlled-causal receipt, preserved for continuity;
- a generic CounterProof `WITNESSED_CAUSAL_REPLAY` receipt produced through the
  reusable CONTROL/BAD/REVERT core protocol.

The generic adapter intentionally scopes its oracle to the observable keyring
service lifecycle and portal dependency. The missing `login` Secret Service alias
is recorded as a shared fixture state, not silently promoted into proof that the
login keyring is unlocked.
