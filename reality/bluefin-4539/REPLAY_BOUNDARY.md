# Bluefin #4539 replay boundary

## Evidence states are intentionally separate

This case now has three different candidate identities that must not be collapsed:

1. **PR source states** — exact review/merge commits.
2. **Shipped stable releases** — the images users actually moved between.
3. **Controlled causal candidates** — one frozen modern boot environment with the
   exact #4539 intervention added and then removed.

## PR-level source provenance

```text
PR_BASE       f2a60b9b6e62880b38b70595f035e7a6ac571bc5
PR_HEAD       42b32a75fbfb83a316bd3473e80043d551af20da
MERGED_BAD    60e72be24878ce01b4849cfb4b8efc18932a133e
MERGED_REVERT bd12c2e29f6ecb2cabd5bfb53bc00281a7d9118f
```

BAD and MERGED_REVERT have the same historical `image-versions.yml` dependency
digests. Their relevant source delta is the presence/removal of
`30-after-keyring.conf`.

## Shipped release provenance

Official Bluefin release metadata establishes:

```text
stable-20260519 -> source head 5de075a6ccbcc37d2551cc8d3cf854d96f8e4845
stable-20260526 -> source head 60e72be24878ce01b4849cfb4b8efc18932a133e
stable-20260527 -> source head 42c737ee6d232f7351dc3af08a9bd1dbea57dd47
```

The 2026-05-27 release head is two commits ahead of merged revert
`bd12c2e` and zero commits behind it, so it is a genuine post-revert shipped
release.

This also fixes an earlier identity ambiguity: PR_BASE `f2a60b9` is **not** the
same thing as the shipped known-good `stable-20260519` release.

## Registry executability

Current probes show that these final historical artifacts are no longer
retrievable from GHCR:

- user-reported immutable BASE digest;
- user-reported immutable BAD digest;
- `stable-daily-44.20260519`;
- `stable-daily-44.20260526`;
- `stable-daily-44.20260529`;
- official `stable-20260519`;
- official `stable-20260527`.

The official BAD release `stable-20260526` is probed in the same workflow; its
availability must be read from the current run rather than inferred from release
metadata.

Historical dependency availability is narrower:

| Historical dependency | status |
|---|---|
| `projectbluefin/common` pinned digest | AVAILABLE |
| `ublue-os/brew` pinned digest | AVAILABLE |
| `ublue-os/silverblue-main` pinned digest | UNAVAILABLE |

Therefore a bit-for-bit historical rebuild must not be claimed while the pinned
Silverblue base is missing.

## Controlled causal replay — witnessed

CounterProof freezes one retrievable Bluefin control image and constructs:

```text
CONTROL
  -> add exactly #4539's 30-after-keyring.conf
BAD
  -> remove exactly that file
REVERT
```

All three candidates boot in real GNOME sessions under
`projectbluefin/testsuite` QEMU.

Observed signature:

| candidate | keyring unit active | portal -> keyring dependency | NotInInitialization |
|---|---:|---:|---:|
| CONTROL | false | false | false |
| BAD | true | true | true |
| REVERT | false | false | false |

This is a reproducible `Y -> Y' -> Y` controlled causal witness for the
activation-path effect of the historical intervention.

It is **not** the same claim as replaying the original May 2026 shipped images.

## Oracle applicability

The first behavior probe assumed the synthetic CI user would have a Secret
Service `login` collection. It did not.

That condition is now classified as:

```text
ORACLE_PRECONDITION_MISSING
```

rather than product failure.

CounterProof therefore needs two distinct boundaries:

```text
Evidence Scope          — is this probe deep enough for the claim?
Oracle Applicability    — are this probe's prerequisites true here?
```

## Source reconstruction gate

The reconstruction workflow now checks, mechanically:

1. exact BAD / MERGED_REVERT source commit;
2. exact historical dependency digests;
3. exact intervention presence/absence;
4. current registry availability for every historical dependency.

Its allowed verdicts include:

```text
READY_FOR_SOURCE_PINNED_REBUILD
BLOCKED_MISSING_HISTORICAL_BASE
BLOCKED_MISSING_HISTORICAL_DEPENDENCIES
INVALID_RECONSTRUCTION_SOURCE_CONTRACT
```

With the current registry state, the expected honest boundary is:

```text
official release provenance          AVAILABLE
controlled causal replay             WITNESSED
historical common/brew               AVAILABLE
historical Silverblue base           UNAVAILABLE
source-pinned historical rebuild     BLOCKED_MISSING_HISTORICAL_BASE
bit-for-bit original replay          INCOMPLETE
```
