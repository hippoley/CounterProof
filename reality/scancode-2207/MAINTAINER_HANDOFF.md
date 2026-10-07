# ScanCode.io #2207 — maintainer evidence handoff

This is a compact reviewer-facing summary of an independent CounterProof replay for
[aboutcode-org/scancode.io#2207](https://github.com/aboutcode-org/scancode.io/pull/2207).

## Claim checked

> The `scanpipe run` management command can be invoked without
> `input_location`.

## Exact candidates

- BASE: `41868632dcaba1ad9b6402d114b169564c08d121`
- HEAD: `f71185995aee043e2e9acfd31028501f23992aea`

## Exact submitted test

```text
scanpipe.tests.test_commands.ScanPipeManagementCommandTest.test_scanpipe_management_command_run_without_input_location
```

The same submitted test was executed against both candidates in ScanCode.io's
PostgreSQL / Django test shape.

## Result

```text
HEAD
f71185995aee043e2e9acfd31028501f23992aea
→ PASS

BASE + exact submitted HEAD test
41868632dcaba1ad9b6402d114b169564c08d121
→ FAIL

failure:
django.core.management.base.CommandError:
Error: the following arguments are required: input_location
```

Machine verdict:

```text
WITNESSED_BEHAVIOR_DELTA
```

The BASE failure is claim-relevant: it occurs because the old CLI still requires
`input_location`, not because of dependency installation, database startup, test
collection, or a new implementation-only helper.

## Environment

- PostgreSQL service
- Django test database: `test_scancodeio`
- Python 3.12
- project dependencies installed from the PR HEAD before candidate replay

## What this establishes

The exact submitted regression distinguishes the PR HEAD from the exact PR BASE for
the user-visible command behavior being claimed.

## What this does not establish

This evidence does not decide whether the PR should merge. It does not independently
prove unrelated compatibility, documentation, API, or broader product requirements.

## Auditable sources

- [Trusted execution run](https://github.com/hippoley/CounterProof/actions/runs/36373412716)
- [Machine receipt](../../examples/claim_matrix/receipts/scancode-2207-behavior.json)
- [Claim matrix](../../examples/claim_matrix/scancode-2207.yml)

The purpose of this handoff is only to reduce uncertainty around the specific
before/after behavior claim.
