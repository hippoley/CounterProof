# Gramps #2484 — executed challenge / repair triad

This case is the second executed three-state proof published by CounterProof, but it
is intentionally **not** labeled CONTROL / BAD / REVERT.

The actual experiment was:

```text
CONTROL
BASE schema + original BASE fixture
→ PASS

CHALLENGE
BASE schema + submitted HEAD fixture
→ FAIL

REPAIR
HEAD schema + submitted HEAD fixture
→ PASS
```

All three states used the same RelaxNG validation path in CounterProof trusted run
[#36224298359](https://github.com/hippoley/CounterProof/actions/runs/36224298359).

## Exact candidates

- BASE: `48e067ced96ad83b7498587ea1562c2d327b41aa`
- HEAD: `faee7435ebb7ddcc5522b83028eddae5a5ef39e3`

Runtime:

```text
Python 3.12.14
lxml 6.1.3
lxml.etree.RelaxNG.validate
```

The CHALLENGE state failed with schema-level errors including:

```text
RELAXNG_ERR_ELEMNAME: Expecting element attribute, got dateval
RELAXNG_ERR_EXTRACONTENT: Element event has extra content: dateval
```

The HEAD schema accepted that exact submitted fixture.

## Why the guard matters

If only these two rows existed:

```text
BASE + submitted fixture → FAIL
HEAD + submitted fixture → PASS
```

the result would already be a valid BASE→HEAD regression witness.

The third state adds a useful control:

```text
BASE + original fixture → PASS
```

That shows BASE was not generically incapable of validating Gramps example data.
The new submitted fixture specifically exposed schema support missing on BASE, and
the HEAD schema repaired that exposed failure.

## Machine verdict

```text
WITNESSED_CHALLENGE_REPAIR
```

This does **not** claim a revert experiment. The intervention axes are fixture
challenge and schema repair, so calling the third state REVERT would be misleading.

- [Machine receipt](../../examples/claim_matrix/receipts/gramps-2484-triad.json)
- [Claim matrix](../../examples/claim_matrix/gramps-2484.yml)
- [Source run](https://github.com/hippoley/CounterProof/actions/runs/36224298359)
