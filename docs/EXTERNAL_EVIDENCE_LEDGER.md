# External evidence ledger

This page is an index of **externally checkable evidence about CounterProof's
role in other projects**.

It is not a list of self-awarded titles. A record enters the ledger only when
there is an external repository, external intake, producer-owned artifact, or
maintainer statement that another reviewer can inspect without trusting
CounterProof's wording.

The machine-readable source is
`examples/claim_matrix/external-evidence-ledger.yml`.

## AVERA — producer-named first consumer

**Current status:** `THIRD_PARTY_NAMED_ROLE`

AVERA's own repository now carries three durable pieces of evidence:

1. `docs/AVERA_CHECK_EVIDENCE_V0.md` names CounterProof as the **first
   consumer** involved in designing the experimental evidence envelope.
2. AVERA issue #12 records the maintainer's closeout that the envelope shipped
   and CounterProof's first consumer was merged and green.
3. AVERA PR #14 implements the producer-side contract agreed through the
   AVERA/CounterProof interoperability discussion.

This is stronger than a mention or a reply: the producer changed its own
contract, documentation and shipped implementation while naming the downstream
consumer role.

What it does **not** establish: AVERA adoption of CounterProof, endorsement,
certification, or a standard.

### Credential value

For a future interoperability/conformance discussion, this record can support:

> CounterProof has already served as the first downstream consumer for a
> producer-defined evidence envelope and maintained the producer/consumer
> semantic boundary through implementation.

A reviewer can verify that claim from AVERA's repository without relying on a
CounterProof README.

## ExecSurface — preserved external evidence submitted

**Current status:** `EXTERNAL_EVIDENCE_SUBMITTED_QUALIFICATION_PENDING`

CounterProof independently ran ExecSurface's frozen experimental typed-evidence
trial against a frozen CounterProof workload with zero assistance before the
first result.

The preserved run completed preflight, build, doctor, observe and reference
consumer validation. The same first result reported a CI-log privacy friction
instead of discarding or rewriting the run.

The result has been submitted into AETHER X's own public evidence intake as
`AETHERXGLOBAL/execsurface#164`.

This is already durable evidence that CounterProof participated as an
unaffiliated external evaluator. It is **not yet** evidence that AETHER X has
qualified the result. Until they independently classify or act on #164, no
higher recognition state is recorded here.

## Why this ledger exists

A 6–12 month credential should not depend on remembering a conversation.

The intended chain is:

```text
external repository / intake
        ↓
immutable or content-addressed source
        ↓
exact role and status
        ↓
explicit non-claims
        ↓
future reviewer can re-check it
```

The identity value comes from the external evidence. This page only makes that
evidence cheap to discover.

## Additional third-party signals

These records are useful, but they are deliberately kept below the AVERA
producer-owned role.

### External reviewer — claim/evidence matrix

An external reviewer confirmed that CounterProof's automated matrix preserved
the requested semantics and stated:

> "I would use this shape in review."

This is durable **use intent plus semantic acceptance**. It is not evidence that
the upstream project adopted CounterProof or that the reviewer represents that
project's maintainers.

### Codex PROVE — optional handoff boundary

The PROVE maintainer confirmed that the documented CounterProof → PROVE handoff
matches the intended composition, clarified stale-evidence/scoped-reuse rules,
and agreed the optional handoff is the right stopping point.

This compresses a future proof burden: CounterProof no longer needs to re-prove
from scratch that its receipts can be composed as optional requirement evidence
without owning PROVE's final decision.

It does not establish a PROVE dependency or adoption.

### claimproof — consumer artifact implemented, producer confirmation pending

The claimproof maintainer confirmed that CounterProof found a real gap at the
durable `ClaimBasis` layer and invited a first-class candidate-bound export use
case.

CounterProof has now merged PR #164: a frozen native `ClaimBasis` v1 store
plus an outer opaque candidate identity, with exact producer-source and store
blob identities. The consumer deliberately emits only `BOUND_INPUT` and does
not take ownership of claimproof's lifecycle semantics.

That moves this record beyond an invitation: a concrete consumer artifact now
exists and has been handed back to the maintainer for judgment.

It still remains below AVERA's credential strength because claimproof has not
yet confirmed the implemented shape or shipped a producer-side export.

### agent-done-or-not — receipt reuse boundary

The maintainer explicitly agreed that `review-pr` receipts may be reused as
input to a CounterProof BASE→HEAD check while CounterProof remains responsible
for deciding whether the evidence demonstrates a fix.

No frozen producer payload or adapter has landed yet, so this remains a
confirmed interoperability boundary rather than an implementation credential.

## Credential strength

The current ordering is intentionally conservative:

```text
producer-owned named role + shipped interop
    > maintainer-confirmed executable boundary
    > explicit reviewer use intent
    > upstream use-case invitation
    > discussion only
```

A future identity claim should cite the strongest applicable record rather than
collapsing all external interactions into one "adoption" bucket.
