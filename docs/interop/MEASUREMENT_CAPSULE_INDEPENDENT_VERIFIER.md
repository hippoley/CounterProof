# Independent SCITT Measurement Capsule verifier

Status: experimental.

This module implements the identifier and batch-integrity parts of
`draft-templeman-scitt-measurement-capsule-00` from the public text.

It does **not** import or call the CSOAI prototype builder/verifier.

Implemented:

- RFC 8785 JCS canonicalization using the independent Trail of Bits
  `rfc8785` package;
- `capsule_id = SHA-256(JCS(capsule without capsule_id))`;
- exact-JCS stored-line verification;
- draft Section 7.1 no-decision/no-authority surface checks;
- digest-only `sources` admission;
- preservation of `UNCHECKABLE` as a measurement state;
- RFC 9162 Merkle Tree Hash using:
  - leaf hash `SHA-256(0x00 || capsule_id_bytes)`;
  - node hash `SHA-256(0x01 || left || right)`;
  - capsule ids sorted in ascending byte order;
  - duplicate refusal;
- expected root/count verification for a published batch.

Not implemented:

- COSE_Sign1;
- SCITT Transparency Service registration/Receipt verification;
- OpenTimestamps or Rekor verification;
- measurement-instrument correctness;
- CSOAI-specific per-kind semantic vocabularies beyond the generic draft rules.

## External experiment target

The draft's Section 13 defines a success outcome where an implementation by
another party, written from the text, recomputes identifiers and roots of a
published batch.

This verifier is intended to attempt exactly that outcome.

At the time this code was added, the public draft/index were readable but the
raw `capsules.jsonl.gz` / `leaves.json` batch bytes were not retrievable
through the current automation environment. Therefore this repository must not
claim the Section 13 outcome until a real published batch is supplied and the
root matches.

## Claim boundary

A successful Merkle recomputation proves only that the supplied capsule bytes
bind to the supplied root under the draft algorithm. It does not prove that the
measurements are true, independent, unbiased, authorised, or endorsed by SCITT
or the IETF.
