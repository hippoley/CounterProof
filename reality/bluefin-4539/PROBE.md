# Bluefin #4539 / #4683 — behavioral oracle probe

Historical chain:

- fix PR: https://github.com/ublue-os/bluefin/pull/4539
- regression: https://github.com/ublue-os/bluefin/issues/4683
- revert: https://github.com/ublue-os/bluefin/pull/4685
- CounterProof intake: https://github.com/hippoley/CounterProof/issues/96

## What the merge-time lab check proved

The historical lab check established an **implementation** fact:

```text
drop-in exists
+ After=gnome-keyring-daemon.service
+ Wants=gnome-keyring-daemon.service
+ systemd parses the ordering
= PASS
```

That is a valid candidate delta. It is not the user-facing acceptance criterion.

## User-facing acceptance criterion

Issue #4683 states the product requirement directly:

> after automatic login, the login keyring should already be unlocked.

That gives a stronger candidate-neutral oracle:

```text
GNOME session is up
AND org.freedesktop.secrets is reachable
AND login alias resolves
AND login collection Locked == false
```

This oracle does not care whether the implementation uses `After=`, `Wants=`,
PAM, socket activation, or another mechanism.

## Proposed testsuite scenario

The current `projectbluefin/testsuite` already boots a real GNOME session in QEMU
and already executes session D-Bus commands through its common suite. The missing
probe can therefore live beside `common_portals.feature` without a new harness.

See `proposed_common_portals_keyring.feature` in this directory.

## Evidence layers

| Layer | Probe | #4539 historical lab |
|---|---|---|
| IMPLEMENTATION | drop-in exists / systemd sees ordering | witnessed |
| BEHAVIOR | login collection is unlocked after autologin | not checked |
| SAFETY / diagnosis | activation path / journal explains why it failed | not checked |

The behavior probe is the acceptance oracle. Journal and dependency evidence are
diagnostics, not substitutes for it.

## BASE / HEAD experiment

For a historical replay, the strongest experiment is not merely source checkout.
The change affected the boot image and login lifecycle, so the candidates should be
booted as images or reconstructed images corresponding to:

- pre-change BASE: `f2a60b9b6e62880b38b70595f035e7a6ac571bc5`
- #4539 HEAD: `42b32a75fbfb83a316bd3473e80043d551af20da`
- known-good revert: `99e089a0d85e360c69b9aa83c4abb1283b6c9b7b`

Expected historical shape if the regression is reproducible:

```text
                         shallow order check    keyring-unlocked behavior
BASE                     absent / fail          PASS
#4539 HEAD                PASS                   FAIL
REVERT                    absent / fail          PASS
```

That is a **counterexample to "HEAD green implies fix proven"** and a useful
three-candidate receipt:

```text
implementation delta: WITNESSED
claimed behavior:      CONTRADICTED
revert recovery:       WITNESSED
```

## Demand-side question

If this receipt can be reproduced, return it to the Bluefin thread and ask only:

> Would a pre-merge receipt that separated "systemd ordering is present" from
> "login keyring is actually unlocked" have prevented or shortened the
> #4539 → #4685 merge/revert loop?

Do not claim adoption until a maintainer answers.


## Controlled causal replay result

The original historical OCI artifacts are no longer retrievable from GHCR, so
the current executable result is deliberately labeled **controlled-causal**,
not an original-image historical replay.

Using one frozen Bluefin control image, CounterProof constructed:

```text
CONTROL
  -> add exactly #4539's 30-after-keyring.conf
BAD
  -> remove exactly that file
REVERT
```

All three candidates booted through projectbluefin/testsuite into real GNOME
sessions under QEMU.

The first unlock oracle exposed a fixture-precondition problem: the synthetic
CI user has no `login` Secret Service alias. That condition is now reported as
`ORACLE_PRECONDITION_MISSING` rather than being misclassified as a product
failure.

The candidate-neutral diagnostic produced this causal signature:

| candidate | keyring user unit | portal dependency | NotInInitialization |
|---|---|---|---|
| CONTROL | inactive | absent | absent |
| BAD | active | present | present |
| REVERT | inactive | absent | absent |

In BAD, `xdg-desktop-portal.service` explicitly depends on
`gnome-keyring-daemon.service`; systemd starts the keyring unit immediately
before the portal; and the daemon emits the historical
`org.gnome.SessionManager.NotInInitialization` error. CONTROL and REVERT do
not show that behavior.

This is therefore a reproducible:

```text
Y -> Y' -> Y
```

controlled causal witness for the activation-path effect of the #4539
intervention.

It is **not yet** evidence that the original 2026-05-26 shipped BAD image has
been replayed byte-for-byte. Historical registry artifacts were garbage
collected, so that stronger claim remains blocked pending source-pinned
reconstruction or another surviving original artifact.
