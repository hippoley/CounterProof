# in-toto #597 conformance consumer experiment

This fixture freezes the public conformance manifest proposed in
[in-toto/attestation#597](https://github.com/in-toto/attestation/pull/597) at
head commit `8c8d21c4908cff5b5c241e7fce32d342975216f9`.

CounterProof does **not** implement or claim to verify the
`adversarial-execution-evidence` predicate here.

The experiment starts one layer later:

1. an external verifier evaluates the predicate-specific statements;
2. its per-vector observations are supplied to CounterProof;
3. CounterProof compares only the manifest-declared normative surface;
4. CounterProof freezes the manifest identity, vector set, comparison surface,
   verifier identity, and observed results into a conformance receipt;
5. if the manifest later changes, the historical receipt remains valid for the
   pinned manifest but becomes `STALE` as evidence for the new corpus.

The checked-in `observations.json` is deliberately a fixture, not an
independent predicate-verifier result. Its purpose is to exercise the consumer
contract before an external verifier is attached.

This is an interoperability experiment, not an in-toto endorsement, adoption
claim, or normative extension.
