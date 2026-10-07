# Cross-verifier conformance note: in-toto #597 × aee-checker

## Observation

CounterProof consumed the four worked-example vectors from the conformance
manifest proposed in `in-toto/attestation#597` and compared them with the
published directed run from the independently authored
`Rul1an/aee-checker`.

The statement bytes are identical on both sides of the handoff.

Result:

```text
normative verdict/result parity: 4 / 4
same-name reject reason-code parity: 0 / 2
```

The two reject decisions agree semantically while using different local reason
labels:

```text
v2adb319fc7515885
  manifest: environment-incomplete
  checker:  required-member-absent

v3418101227718535
  manifest: corpus-manifest-no-attacks
  checker:  manifest-declares-no-attack
```

## Why this matters

The #597 manifest separates normative comparison fields
(`verdict`, and `result` where applicable) from measured diagnostics
(`codes`). This cross-implementation result gives a concrete reason to keep
those surfaces separate: implementations can agree on the conformance decision
while using different diagnostic vocabularies.

CounterProof therefore records reason-code differences without promoting them
to a normative divergence.

## Provenance

- in-toto #597 frozen head:
  `8c8d21c4908cff5b5c241e7fce32d342975216f9`
- aee-checker repository snapshot:
  `ef8438c4d6651090f0298516663fc03febe432ac`
- aee-checker source digest:
  `sha256:5fbe879e9d6a7355d5af8c4ea6f7c055f9289753c69b9336b5ce0a213371b596`
- checker-local run sequence: `27`
- corpus-side suite revision for the same run: `28`
- corpus commit before history rewrite:
  `94c163c8e4d9b52a7056c63bc489932329d42a42`
- corpus commit after history rewrite:
  `e98de66d7296c4eb01abc38b6aee0b51b0c87a8e`
- checker report SHA-256:
  `5d0137b3d567df7dd5088b10098ce88b1834940c645af1ba994f5438d4a9a107`

The four overlapping statement Git blobs are recorded in
`observations-rul1an-rev27.json` and are byte-identical between #597 and the
checker corpus.

## Non-claims

This note does not claim:

- that CounterProof implements the AEE predicate;
- that the checker's whole-suite parity figure is a result about #597;
- that reason-code names are normative;
- that the pinned corpus covers later predicate rules;
- in-toto endorsement, adoption, or certification.

The useful claim is narrower: one independently authored checker produced the
same normative decisions for the four identical worked-example statement bytes,
and CounterProof can bind that observation to exact producer and corpus
provenance without erasing measured diagnostic differences.
