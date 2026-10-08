# claimproof ClaimBasis handoff experiment

This fixture implements the smallest consumer experiment requested by the
claimproof maintainer in the CounterProof #64 discussion.

The producer-native ClaimBasis store remains unchanged. CounterProof does not
add BASE→HEAD semantics, merge recommendations, confidence, or a "fix verified"
field to claimproof's data.

The only external wrapper binds:

- the producer identity;
- the exact claimproof `basis.py` source blob used to interpret the store;
- a producer-defined candidate identity;
- the exact ClaimBasis file consumed.

Frozen upstream source:

```text
Cshearer210/claimproof
src/claimproof/basis.py
Git blob f22f599d8b77077bfabbc95d031f12f68a088e0a
```

The included `claim-basis.json` follows claimproof's native v1 store shape:

```text
version: 1
claims:
  <claim-id>:
    claim
    recorded
    evidence[{ref,digest,kind}]
    scope
```

The handoff experiment asks one narrow question:

> Is a native durable ClaimBasis entry plus an exact candidate identity enough
> for CounterProof to admit the record as reusable input without taking ownership
> of claimproof's HOLDS/REOPENED/UNKNOWN/RETIRED semantics?

This is not a claimproof adoption or shipped producer export. It is a frozen
downstream consumer fixture for the first-class use case invited by the
claimproof maintainer.
