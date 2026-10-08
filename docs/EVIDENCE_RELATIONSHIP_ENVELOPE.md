# Evidence Relationship Envelope v0.1

Status: experimental interoperability layer.

## Problem

Evidence ecosystems increasingly report different notions of "independence":

- NOA can derive `SAME_SIGNING_KEY`, `SAME_ADMINISTRATIVE_PARTY`, or
  `UNKNOWN` for a settlement observer and carries the verifier's trust-policy
  and registry snapshot identities.
- WindowPilot can declare that an object observer and an actuator controller
  occupy different control-domain labels, but explicitly does **not** prove
  independence.
- Other systems expose different axes such as binary, code-generation,
  transport, authoring-party, or independence-group separation.

Flattening those into one boolean `independent=true` destroys information and
encourages claim inflation.

## Contract

`counterproof.evidence-relationship/v0.1` is a consumer-side normalization
envelope.

It records a fixed set of relationship facts as:

```text
TRUE | FALSE | UNKNOWN
```

and preserves the upstream source and basis for each fact.

The first implementation adapters are:

- NOA settlement observer relationship;
- WindowPilot object observation separation.

No adapter is allowed to infer organizational independence from:

- different key ids;
- different public keys;
- different service names;
- different binaries;
- different transports;
- different declared control domains.

## Relationship classes

The summary class is intentionally weak:

- `KNOWN_OVERLAP`
- `DECLARED_SEPARATION_ONLY`
- `UNKNOWN`
- `CONFLICT`

There is deliberately no `INDEPENDENT` class in v0.1.

## Why this is infrastructure-shaped

The envelope is useful only if upstream systems remain authoritative for their
own semantics.

CounterProof should not become the place that decides whether NOA, IOI, Crowsi,
or a physical sensor is independent. Its role is to let a downstream consumer
compare what those systems actually established without silently upgrading one
system's claim into another system's stronger vocabulary.

## Graduation criterion

This stays experimental until at least one external producer or consumer uses
the mapping contract or requests an adapter.

A second adapter written only for another hippoley-owned project does not count
as external adoption.
