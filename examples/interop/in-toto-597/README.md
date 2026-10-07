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

## Independent published checker handoff

The fixture-only path above is now complemented by a published independently
authored checker record from
[`Rul1an/aee-checker`](https://github.com/Rul1an/aee-checker), pinned at repository
commit `ef8438c4d6651090f0298516663fc03febe432ac`.

CounterProof consumes only the four vector rows that overlap this #597 worked
example. It does not widen the external checker's whole-suite 272/272 claim into
a claim about #597 or about the latest predicate text.

Pinned producer evidence:

- report: `reports/v0.7-rev27-directed-run.json`
- report Git blob: `f74c0652e8dca842cda92e89f39659e26835e008`
- report SHA-256 declared by the producer index:
  `5d0137b3d567df7dd5088b10098ce88b1834940c645af1ba994f5438d4a9a107`
- producer index Git blob:
  `245f670226328724adae333aab790aa083e9204a`
- checker source digest:
  `sha256:5fbe879e9d6a7355d5af8c4ea6f7c055f9289753c69b9336b5ce0a213371b596`

For the four #597 vectors:

```text
normative verdict/result parity  4 / 4

reject reason-code same-name parity
  v2adb...  expected environment-incomplete
             observed required-member-absent

  v341...   expected corpus-manifest-no-attacks
             observed manifest-declares-no-attack
```

That difference is deliberately **not** promoted to a conformance failure.
The #597 manifest declares `verdict` / accepted `result` as normative and
`codes` as measured. This handoff provides a concrete cross-implementation
example of why those surfaces should remain separate.

The external checker also publishes an important scope boundary of its own:
its suiteRevision 27 corpus is pinned to an older predicate specification than
the then-current upstream pull-request head, and an unexercised newer rule is
explicitly not claimed as covered. CounterProof preserves that distinction
rather than turning a historical 272/272 result into timeless conformance.

