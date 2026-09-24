# Claim / Evidence Matrix — vercel/ai #17096

Source PR: https://github.com/vercel/ai/pull/17096

Independent replay: https://github.com/hippoley/CounterProof/actions/runs/35986126197

- HEAD: `da4b91f82c8ccb3eb15ed5abe5217607539cc504`
- BASE: `66b71512135a0246a9306e97c8847a5d0bcc57ae`
- digest: `sha256:fe2dac513057c98dd17985e6e6be759559a49a8013a0412ec80e07d9efa89bb1`
- HEAD changed tests: **38/38 pass**
- BASE + same changed tests: **37/38 pass, 1 fail**

| Claim | BASE | HEAD | Submitted-test evidence | Oracle alignment | Overall |
|---|---:|---:|---|---|---|
| sandbox settings reach the bridge start message | FAIL | PASS | **WITNESSED** | **UNVERIFIED** | **WITNESSED (submitted judge)** |
| new protocol test distinguishes sandbox-schema support | PASS | PASS | **NOT WITNESSED** | **UNVERIFIED** | **UNPROVEN** |
| Claude Agent SDK actually enforces sandbox restrictions in production | — | — | **UNPROVEN** | **UNVERIFIED** | **UNPROVEN** |

## Assertion-level evidence

The only BASE failure is:

```text
createClaudeCode adapter forwards the sandbox settings to the bridge start message

AssertionError:
expected the start message to match an object containing sandbox settings
```

The new protocol test:

```text
inboundMessageSchema accepts a start message with sandbox settings
```

passes on **both BASE and HEAD**. It asserts only that parsing does not throw, so it does not independently witness the schema change.

## Boundary

The PR body also reports a production integration where Claude Agent SDK sandboxing fails closed, blocks non-allowlisted egress, and denies configured filesystem paths.

That may be valid production evidence, but this CounterProof run did **not** independently reproduce that oracle. It therefore remains `UNVERIFIED` rather than being promoted by the unit-test witness.

The useful statement is:

> host-to-bridge forwarding is independently witnessed; schema-specific discrimination and real SDK sandbox enforcement are not established by the same submitted tests.
