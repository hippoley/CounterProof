# GAC profile validation: reproducible upstream regressions

This is an isolated evidence branch. It **does not modify CounterProof main**, a production VTN, or the ElaadNL upstream repository.

## Verified, 2026-11-04

- Upstream target: [ElaadNL/openadr3-client-gac-compliance](https://github.com/ElaadNL/openadr3-client-gac-compliance), released **3.2.4**, with **openadr3-client 2.4.2**.
- [GitHub Actions evidence](https://github.com/hippoley/CounterProof/actions/runs/41793382781) (Python 3.13):
  - Unmodified release: **9 failed, 4 passed**.
  - Applied bounded candidate correction: **13 passed**.
  - Original upstream GAC 2.0 and 2.1 domain tests: **96 passed**.
  - A reviewable **190-line source diff** against upstream tag 3.2.4 is saved in the run artifact.

## Reproduced failure modes

1. GAC 2.1 and 2.2 only validate the *last interval* for payload count/type/value count; earlier invalid intervals can be accepted.
2. GAC 2.0, 2.1, and 2.2 index empty payload descriptors after identifying invalid cardinality, causing an uncaught IndexError instead of a structured ValidationError.
3. GAC 2.0 already correctly checks **all** intervals. The candidate fix intentionally leaves its interval loop unchanged.

## Files

- [test_regressions.py](test_regressions.py): actual published Pydantic-model integration tests, with 13 parametrized cases.
- [apply_fix.py](apply_fix.py): runner-only candidate correction to installed release, or a source checkout when given its directory as an argument.
- [Workflow](../../.github/workflows/gac-profile-repro.yml): pinned versions, red baseline / green patch comparison, upstream domain suite and patch artifact.

## Upstream contribution status

The current GitHub connector is not authorized to create an upstream Issue or comment (403) and cannot create a fork. **No upstream Issue or PR has been submitted by this branch.**

Follow the upstream [contribution guide](https://github.com/ElaadNL/openadr3-client-gac-compliance/blob/main/CONTRIBUTING.md), including **real-name, real-email DCO signoff**, before submitting. Rebase and rerun tests against latest main rather than treating tag 3.2.4 as current head.

This is a validation correctness issue. We have **not** demonstrated a security exploit or a real-world grid incident.
