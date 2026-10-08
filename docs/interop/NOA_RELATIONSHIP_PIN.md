# Pinned NOA observer-relationship semantics

This fixture pins the public conformance semantics used by CounterProof's first
external Evidence Relationship adapter.

Upstream:

- repository: `NordenSoft/noa-mandate-core`
- commit: `eacb93ce72c7ba00ecd0d5d4477ad2d6f4e4d3c9`
- generator:
  `packages/rail-x402/conformance/gen-settlement-evidence-vectors.mjs`

The upstream generator currently fixes cases for:

- `SAME_ADMINISTRATIVE_PARTY`
- `SAME_SIGNING_KEY`

CounterProof consumes those as overlap evidence only.

This pin is intentionally asymmetric: it protects against semantic *upgrade*.
It does not claim that NOA depends on CounterProof, that NOA has endorsed this
mapping, or that the two projects share a common conformance suite.

If upstream changes the public result contract, this fixture should be reviewed
against the new upstream commit before being updated.
