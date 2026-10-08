# Outcome Witness: interoperability boundary (experimental)

Status: **design note, not a standard or proof of external adoption**. See [issue #180](https://github.com/hippoley/CounterProof/issues/180) and [executable fixtures](../examples/outcome_witness/v0_1_vectors.json).

## Existing infrastructure we should reuse

| Existing layer | What it already establishes | What it does NOT establish |
| --- | --- | --- |
| OpenTelemetry GenAI `execute_tool` span | An execution attempt and its trace context | That an external target state converged |
| in-toto Statement + predicate | A subject-bound, typed claim; envelopes may authenticate its issuer | That the issuer's asserted observation is true |
| SCITT signed statements + transparency receipts | Issuer accountability and registration/inclusion evidence | That the asserted external outcome occurred |
| CounterProof Outcome Witness experiment | A bounded predicate over intended vs observed terminal state, with freshness and independence checks | Authentication, non-repudiation, causal attribution or standard conformance |

**Design rule:** link to the upstream span/statement/receipt by its native identifier; do not replace its format or conflate an authenticated statement with a verified outcome. A named observer is not an authenticated observer. A self-declared independence flag is not proof of independence.

## Minimal interoperable input contract (candidate, not stable)

1. Freeze an intended subject, predicate, expected terminal state and action reference.
2. Carry an opaque upstream execution reference (e.g. OTel span context) without rewriting its identity.
3. Bind the observation to an explicitly identified observer and timestamp; record the maximum accepted age.
4. Evaluate a frozen, versioned oracle. Missing, stale, unauthenticated or unverifiable evidence must never yield VERIFIED in a **trusted** profile.
5. Keep **outcome** separate from **authorization**, **issuer authenticity**, **transparency**, and **causality**.
6. Allow independent consumers to reproduce the decision without invoking the original agent.

The current fixture checker only implements an illustrative subset: structural presence, a self-asserted observer independence flag, relative age, and exact equality for `position`. It must **not** be used as a production trust gate.

## Promotion gates

- **Fixture:** frozen vectors pass in CI (achieved).
- **Observed:** a real producer emits immutable observation bytes, capture time and execution binding (not yet).
- **Authenticated:** a verifier checks source identity, integrity, clock/freshness and replay protections against a declared trust policy (not yet).
- **Independent:** an unrelated consumer validates a producer-owned artifact and publishes its own test or PR (not yet).
- **Adopted:** another project maintains this contract as a dependency, not merely a discussion (not yet).

## High-value counterexample

`execute_tool(close_window)` reports success, while a fresh, independently authenticated controller readback reports `position=open`. A properly bound witness must return CONTRADICTED, regardless of the tool's status. This is a *proposed* hardware experiment, not an executed claim.

## Sources

- [OpenTelemetry GenAI execute-tool spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md)
- [in-toto attestation framework](https://github.com/in-toto/attestation/blob/main/spec/README.md)
- [in-toto Statement v1](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md)
- [IETF SCITT architecture, RFC 9943](https://datatracker.ietf.org/doc/rfc9943/)
