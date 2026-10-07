# ITE #63 dry run: OpenFab Generation proposal (#604)

This note pressure-tests the current draft of
[in-toto/ITE#63](https://github.com/in-toto/ITE/pull/63) against a live predicate
proposal:
[in-toto/attestation#604](https://github.com/in-toto/attestation/issues/604).

It is **not** a recommendation to accept, reject, promote, or demote the
predicate. The goal is to ask a narrower process question:

> can a reviewer tell, from public evidence, which parts of the proposed
> `vetted` criterion are actually established?

## Observation snapshot

This dry run is bound to external-state observation
`ite63-openfab-604-dry-run` in
`examples/claim_matrix/external-state.yml`.

The reviewed snapshot is:

- ITE #63 head: `ef11838ea97886f5e3702513983c4bf0af50d3b3`;
- #604: open, last observed update `2026-10-02T17:46:36Z`;
- OpenFab predicate-spec Git blob:
  `77051b33a8ab5c9fdf95bab8c6b263a173810ad4`;
- agent-evidence-vectors AI-generation manifest Git blob:
  `89cbc4f7d8f0e268a2da35e2417eb2c5090629d5`;
- agent-evidence-vectors findings Git blob:
  `0b764141c515f4b6c408b92a906147a7c35d2451`.

The observation expires after 14 days. Expiry means **refresh the governance
assessment**; it does not retroactively make the historical note false.


### Discussion refresh

A follow-up review of the #604 discussion observed six comments. The discussion
now explicitly separates generation/review provenance from runtime-effect
evidence and records a planned non-goal in the registration text. It also
clarifies the ACP-to-Generation join through the commit tree rather than by
assuming equal Statement subjects.

Those are useful interoperability refinements, but they do **not** change this
dry run's E2/E3 assessment: the reviewed discussion still does not establish the
named independent implementer/consent facts required by E2 or the complete
full-corpus promotion-run packaging required by E3.

The external-state snapshot therefore also pins the issue's comment count.
A new comment is treated as a re-review trigger rather than silently allowing
the governance reading to remain current.

## Candidate claim

#604 says the Generation predicate has:

- two implementations (Rust and browser/WebCrypto);
- cross-verification of signed vectors;
- a third-party conformance suite in
  `probityai/agent-evidence-vectors`.

Those are strong interoperability signals. ITE #63, however, defines a more
specific evidence contract.

## E1 — conformance corpus with negative controls

**Publicly observed: strong evidence.**

The third-party `vectors-ai-generation/` corpus:

- pins specification revision 0.1.5 from OpenFab commit
  `13fd0a8b89399e02dbc9a0322b2c34d3466cbf15`;
- contains 38 vectors: 18 required accepts and 20 required rejects;
- vendors the specification, schema and licence by digest;
- carries clause/condition mappings;
- copies four upstream signed vectors byte-for-byte with source provenance;
- has a deterministic generator and self-check path.

The corpus's findings record eight specification/implementation discrepancies
(F1–F8) that were subsequently adopted into OpenFab revisions 0.1.4 and 0.1.5.

This is exactly the kind of evidence ITE #63 is trying to reward.

**Boundary:** this note does not independently verify the proposed signed
promotion bundle required by ITE #63 as a whole.

## E2 — implementation by someone other than the specification author

**Not yet established by the public material reviewed here.**

#604 names two implementations:

- Rust;
- browser/WebCrypto.

That establishes implementation diversity, but ITE #63's current E2 wording is
about **implementer identity**, not implementation language:

- a named person;
- not a contributor to the specification as of the first pinned run;
- public consent to being named.

The issue and repository material reviewed for this dry run do not establish
those three facts for a qualifying second implementer.

This is not evidence that E2 fails. It means the phrase “two implementations”
must not be silently upgraded into “E2 satisfied.”

## E3 — published full-corpus runs with a defect record

**Publicly observed: substantial but incomplete evidence.**

The third-party findings record real initial disagreements and their
resolutions. In particular, the corpus documented disagreements over:

- canonical member ordering;
- signature coverage;
- unsigned sign-off records;
- typed-round-trip verification;
- the golden vector's verification scope;
- integer value-domain semantics;
- overlapping attribution ranges;
- Assisted-by trailer disagreement.

That is strong evidence for the *defect-record* part of E3.

What this dry run did not find packaged as the ITE #63 E3 bundle contract:

- a `blind` or `directed` label on each qualifying implementation run;
- the complete full-corpus run records for each qualifying implementation,
  packaged with the specification commit and corpus digest;
- the ordering evidence that the corpus digest was published before the second
  implementer's first run;
- the second implementation and output committed before later corpus changes;
- the per-producer signed run bundle contemplated by ITE #63.

Again, absence from this review is not proof that the facts do not exist. It is
a process finding: they are not yet obvious enough to be mechanically admitted
from the proposal's headline evidence.

## The process gap this exposes

The proposal can truthfully say:

```text
two implementations
+ cross-verification
+ third-party corpus
+ eight discovered-and-fixed disagreements
```

and still leave a reviewer doing manual archaeology to answer:

```text
who qualifies for E2?
which exact run qualifies for E3?
was it blind or directed?
which spec and corpus bytes did it bind?
what was the publication/run ordering?
who signed the run evidence?
```

That suggests an important implementation requirement for ITE #63:

> the evidence criterion needs a machine-readable admission record, not only a
> prose checklist.

CounterProof should not define that record unilaterally. Its useful contribution
is narrower: mechanically checking evidence identities and refusing common
upgrades such as:

```text
two implementations
=> independent implementer

PASS report
=> named verifier actually ran

historical full-corpus run
=> current applicability

strong interoperability evidence
=> every promotion criterion satisfied
```

## CounterProof relevance

CounterProof now has concrete guards for two of these failure classes:

1. exact corpus/input identity and lifecycle binding;
2. named external verifier execution completeness, including refusal of
   reference-rail substitution.

It does **not** currently establish:

- E2 authorship independence;
- public consent;
- blind/directed provenance;
- promotion-bundle signatures;
- the full ITE #63 run-ordering constraints.

That is the correct boundary for a future standards contribution.

## Why #604 is a useful test case

#604 is useful precisely because its evidence is not weak. If a strong candidate
with real cross-implementation findings still requires a reviewer to infer which
ITE #63 conditions are established, the missing piece is likely in the process
artifact shape rather than the candidate's engineering quality.

That makes this a good dry run for the criterion itself.
