# REA Evidence v2 consumer profile (experimental)

Status: **consumer-profile draft**, not an REA schema replacement.

This profile records the smallest semantic surface a downstream proof/compatibility tool needs from an REA Evidence v2 record. It is based on REA's published Evidence v2 contract and process-capture documentation; it deliberately avoids copying REA's full schema or inventing provider-specific fields.

## Goal

Keep two responsibilities separate:

- **REA**: observe / derive / infer facts about an artifact or execution and preserve evidence provenance.
- **CounterProof behavior witness**: state exactly what compatibility claim is being tested, which evidence supports it, how the candidate is compared, and what remains unproven.

The bridge should therefore consume REA evidence without weakening its authority, confidence, limitations, or identity.

## Required semantic projection

A producer profile MUST preserve the following semantics from REA Evidence v2:

| REA semantic | Behavior witness use |
|---|---|
| stable `evidence_id` | immutable evidence reference |
| artifact identity/hash | subject identity / authority binding |
| provider identity + observed version | provenance |
| operation + normalized parameters | probe identity |
| normalized result | reference observation |
| confidence: observed / derived / inferred | evidence strength |
| authority class | oracle/evidence authority boundary |
| execution environment | replay scope |
| explicit limitations | `does_not_establish` boundary |
| typed source locations, when present | audit trail |

Raw provider output MAY remain external when it is large or sensitive. A witness should reference it by stable evidence identity rather than duplicating it.

## Fail-closed rules

A bridge MUST NOT produce a positive compatibility verdict when:

1. the source Evidence is missing a stable identity;
2. the comparison depends on a field listed as unknown, truncated, redacted, or unavailable;
3. source and candidate were captured under incompatible comparison contracts;
4. the source is inferred but the claim is phrased as directly observed;
5. evidence limitations exclude the behavior being claimed;
6. a required authority/provenance reference is unavailable.

In those cases the result is `UNKNOWN`, not `PASS`.

## Process-capture mapping

For REA process captures, a downstream witness should preserve the distinction between independently observed dimensions (for example terminal, interaction, exit, filesystem, protocol, process, and shim behavior). A match in one dimension must not silently become complete-equivalence.

A useful downstream contract therefore looks like:

```text
REA capture Evidence
  evidence_id
  authority
  confidence
  limitations
  comparison contract
  normalized observations
        |
        v
Behavior witness
  claim
  selected dimensions
  exact comparator
  evidence references
  scope / non-claims
        |
        v
PASS / FAIL / UNKNOWN
```

## Why this is not another Behavioral IR

This profile does not attempt to describe program semantics generally. It is a **proof-boundary adapter**: evidence remains owned by its producer; the witness adds claim scope and verdict semantics for downstream review/CI.

## Interoperability graduation test

This profile should graduate only after a real REA-generated Evidence v2 fixture is consumed end-to-end by a downstream verifier without:

- copying the entire REA envelope;
- weakening REA's limitations/unknowns;
- inventing authority;
- relying on CounterProof-specific internal state.

Until then, this document is an explicit design hypothesis.
