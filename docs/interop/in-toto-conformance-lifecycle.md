# in-toto conformance vectors: lifecycle and freshness boundary

CounterProof is tracking [in-toto/attestation#597](https://github.com/in-toto/attestation/pull/597)
because repository-owned conformance vectors are a natural interoperability boundary for
independent verifiers.

The useful boundary is not “CounterProof should define an in-toto predicate.” Existing
predicates such as Simple Verification Result, SCAI, and Test Result already cover large
parts of the evidence space. The narrower contribution is lifecycle semantics for the
conformance corpus itself.

## The stale-conformance failure mode

A verifier can truthfully report:

```text
passed every vector in corpus revision A
```

and later be incorrectly presented as:

```text
conforms to the current predicate corpus
```

after the specification, manifest, or vectors move to revision B.

That is the same class of error CounterProof has already had to harden elsewhere:

```text
valid historical evidence
!=
current applicable evidence
```

## Minimum binding

A portable conformance receipt should bind at least:

```text
predicateType
spec revision / digest
conformance manifest digest
vector-set identity
comparison surface
verifier identity/version
observed verdict per vector
evaluated_at
```

The important distinction is between **content identity** and **freshness**.

A receipt can remain byte-valid forever while becoming stale as evidence for a newer
corpus. Consumers should therefore be able to represent:

```text
CURRENT
STALE
SUPERSEDED
CONFLICTING
```

without rewriting the historical receipt.

## Why this belongs outside the predicate verdict

The predicate specification remains normative. The vector corpus tests whether a
verifier agrees with selected readings of that specification. Lifecycle answers a
different question: whether an old conformance result is still applicable to the
current corpus/spec state.

Keeping those separate prevents a historical PASS from silently expanding into a
current conformance claim.

## Proposed interoperability experiment

If the in-toto conformance layout stabilizes, CounterProof can consume one manifest as
an external producer contract and emit a receipt that:

1. pins the manifest and referenced statement bytes;
2. records the comparison surface and per-vector result;
3. refuses cross-corpus substitution;
4. preserves the original receipt when the upstream corpus moves;
5. marks applicability stale until the verifier is rerun.

This would be an interoperability experiment, not an endorsement, adoption claim, or
new in-toto normative layer.
