# Bluefin #4539 replay boundary

## What can no longer be replayed exactly

Registry probe:

- https://github.com/hippoley/CounterProof/actions/runs/36397806254

returned `not found` for all of:

- known-good Bluefin 44.20260519 immutable digest;
- shipped-regression Bluefin 44.20260526 immutable digest;
- post-revert historical tag candidate.

A second dependency probe:

- https://github.com/hippoley/CounterProof/actions/runs/36398053967

found:

| Historical dependency | BASE | BAD / REVERT |
|---|---|---|
| `projectbluefin/common` pinned digest | available | available |
| `ublue-os/brew` pinned digest | available | available |
| `ublue-os/silverblue-main` pinned digest | **unavailable** | **unavailable** |

Therefore CounterProof must **not** claim a bit-for-bit historical image replay.

Current verdict:

```text
historical source provenance       AVAILABLE
historical Bluefin output OCI      UNAVAILABLE
historical common/brew OCI         AVAILABLE
historical silverblue base OCI     UNAVAILABLE

exact historical replay            INCOMPLETE
```

## Two experiments, not one

### 1. Historical provenance replay

Preserve the exact source states:

- BASE: `f2a60b9b6e62880b38b70595f035e7a6ac571bc5`
- BAD: `60e72be24878ce01b4849cfb4b8efc18932a133e`
- REVERT: `bd12c2e29f6ecb2cabd5bfb53bc00281a7d9118f`

This answers **what source changed**, while recording the missing environment artifacts.

### 2. Controlled causal replay

Freeze one retrievable Bluefin image:

```text
ghcr.io/ublue-os/bluefin@
sha256:76aa5d6f4f2f3e18b244587bfbd45ae1777a7d0934f869534228eab6af1f0101
```

Then construct:

```text
CONTROL = frozen image
BAD     = CONTROL + exact historical 30-after-keyring.conf
REVERT  = BAD - exact historical 30-after-keyring.conf
```

This does not recreate May 2026. It asks a narrower causal question:

> Holding the boot environment fixed, does adding the exact #4539 intervention
> break the real GNOME-session keyring invariant, and does removing it restore
> that invariant?

That distinction must remain visible in every receipt.
