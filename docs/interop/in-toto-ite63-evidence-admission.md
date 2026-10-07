# Evidence admission boundary for in-toto ITE #63

CounterProof is tracking
[in-toto/ITE#63](https://github.com/in-toto/ITE/pull/63), which proposes a
`vetted` predicate tier backed by three evidence items:

- E1 — a conformance corpus with negative controls;
- E2 — an implementation built from the specification by someone other than
  the specification author;
- E3 — published full-corpus runs, including at least one blind run, pinned to
  the specification and corpus and carrying a disagreement record.

CounterProof does **not** claim to establish E1, E2 or E3 for a predicate.

Its useful boundary is narrower: deciding whether a harness report is even
admissible as evidence that the **named external implementation actually ran**.

## Why that boundary exists

`probityai/agent-evidence-vectors` documents a fixed harness defect affecting
releases through v0.12.0: a named external verifier could fail to start while
the harness substituted its reference rail and still emitted a passing result.

So this implication is unsafe:

```text
report says PASS
therefore
named implementation ran
```

The first question must instead be:

```text
did the named implementation actually execute the claimed corpus?
```

Only after that question is answered does conformance scoring become evidence
about that implementation.

## CounterProof admission check

As of CounterProof commit
`6b73377137d08cbc90fbdc5416e68f73f2390598`,
`counterproof verify-external-harness-report` requires:

```text
rail == external
verifier.command is present
verifier.vectorsExecuted == totals.vectors
totals.suiteRefusals == 0
no reported vector has verifierRan == false
```

A complete run is admitted even when the verifier disagrees with the corpus.

That distinction is deliberate:

```text
execution authenticity/completeness
!=
conformance success
```

A verifier that genuinely runs all vectors and fails many of them produces
useful negative evidence. A report that silently ran a different rail does not
produce evidence about the named verifier, even if every score is green.

## Relationship to ITE #63 E3

ITE #63's current E3 text additionally requires items CounterProof does not
establish with this gate, including:

- the specification commit;
- the corpus digest;
- a `blind` or `directed` label;
- the record of initial disagreements and their resolution;
- the ordering constraints around corpus publication and the second
  implementation's first run.

CounterProof's conformance receipts can separately bind exact manifest and
observation identities, but that still does not prove that an implementation
qualifies under E2 or that a run satisfies every E3 requirement.

The narrow claim is:

> before a full-corpus run is counted as evidence from a named external
> implementation, the report should mechanically prove that the named
> implementation ran every claimed member.

This is an evidence-admission invariant, not a new predicate tier, new in-toto
requirement, endorsement, or certification proposal.
