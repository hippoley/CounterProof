# Claude Code #89404 — oracle disagreement proof

CounterProof uses this case as a flagship **negative proof boundary**.

The submitted regression suite reports green, but reviewer-supplied evidence shows
that the product's own parser rejects fixtures the submitted validator treats as
valid.

## Candidate identity

- BASE: `8b6ef81f636a7697e5ae2338428fa0b272993845`
- HEAD: `0989f29b0bca412edc58018c462cae7344bb1a2f`

## Submitted judge

`validate-agent.test.sh` reports 5/5 passing.

A reviewer also reproduced that reverting the multi-line description extraction
back to the original single-line form still leaves that suite green while the false
`<example>` warning returns.

That means the submitted judge does not actually guard the claimed multi-line
description behavior.

## Authoritative oracle

Reviewer measurements used the product command:

```text
claude plugin validate --json
```

on Claude Code 2.1.268 and 2.1.270.

The product parser rejected the agent fixtures that the submitted validator test
treated as valid.

Primary external evidence:

- review: https://github.com/anthropics/claude-code/pull/89404#pullrequestreview-5190939241
- inline parser finding: https://github.com/anthropics/claude-code/pull/89404#discussion_r3999827406
- reviewer agreement on product-parser alignment: https://github.com/anthropics/claude-code/pull/89404#issuecomment-5555827628

## CounterProof conclusion

```text
submitted judge       GREEN
authoritative oracle  REJECT
oracle alignment      CONTRADICTED
product-level claim   CONTRADICTED
```

This artifact is intentionally labeled `REVIEWER_SUPPLIED_EXTERNAL_ORACLE`.

CounterProof did **not** independently execute the Claude Code binary for this
publication artifact. The proof is therefore about the documented oracle
contradiction and its provenance, not a claim that CounterProof reproduced the
product runtime itself.

## Why this belongs beside Bluefin

Bluefin demonstrates the positive case:

```text
same oracle
CONTROL == REVERT != BAD
→ causal witness
```

Claude #89404 demonstrates the equally important negative case:

```text
submitted judge green
product oracle rejects
→ do not promote green evidence into product truth
```

Together they define the product boundary more clearly than either example alone.
