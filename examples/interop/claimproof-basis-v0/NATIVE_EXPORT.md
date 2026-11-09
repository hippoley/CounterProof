# claimproof.basis/v0 native export consumer fixture

This is a **synthetic, schema-conformant consumer fixture**, not a payload captured
from a live ClaimProof process. It follows the published v0 wire schema and
producer example from `Cshearer210/claimproof` commit `2c3be25`.

Pinned producer sources:
- `src/claimproof/basis.py`, Git blob `517215f265f340bd61d1e986908d7b6f1f60a027`
- `src/claimproof/schemas/claimproof.basis.v0.json`, Git blob `698afdd301787416f4f4609f20ec73b974528f4d`
- `tests/test_basis_export.py`, Git blob `edba4ed4a653a95f544a25c5340aab70a3cbf404`

The fixture deliberately uses:
- `identity_kind: git-commit-dirty`;
- an opaque candidate identity that is not a 40-character commit SHA;
- `claim.state: UNKNOWN`;
- an `<absent>` evidence digest.

The consumer must preserve these values rather than coercing a dirty candidate
into a clean commit, rejecting opaque identity, or turning UNKNOWN into HOLDS.

The existing `claim-basis.json` + `handoff.json` fixture remains a historical
v1-store compatibility test. This new fixture exercises the producer's native
`claimproof.basis/v0` export path.

No BASE→HEAD semantics, fix verification, adoption, or merge recommendation is
inferred from this export.
