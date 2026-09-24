# Oracle Alignment Matrix — anthropics/claude-code #89404

Source PR: https://github.com/anthropics/claude-code/pull/89404

This is a manual Reality Probe for the case where the submitted test suite and the product's authoritative behavior disagree.

## Evidence sources

- submitted regression suite: `plugins/plugin-dev/skills/agent-development/scripts/validate-agent.test.sh`
- submitted judge: `validate-agent.sh`
- authoritative product probe identified by reviewers: `claude plugin validate`
- reviewer evidence:
  - https://github.com/anthropics/claude-code/pull/89404#issuecomment-5530003497
  - https://github.com/anthropics/claude-code/pull/89404#pullrequestreview-5190939241

## Claim / evidence matrix

| Review claim / failure mode | Submitted regression | Authoritative oracle probe | Oracle alignment | Status |
|---|---|---|---|---|
| Warning/error counters should not abort validation under `set -e` | Suite exercises warning/error paths | Reviewers agree the counter / `|| true` fixes are valid | No contradiction reported for this narrow behavior | **SUPPORTED, oracle not separately challenged** |
| Plugin-dev's own agent fixtures are valid and should exit 0 | Submitted suite expects exit 0 | Reviewers report `claude plugin validate` rejects those fixtures as invalid YAML/frontmatter | **CONTRADICTED** | **REGRESSION CLAIM CONTRADICTED BY PRODUCT ORACLE** |
| Multi-line description extraction fix is protected by the new suite | Submitted suite stays green | Reviewer reports reverting extraction to the original single-line form still leaves 5/5 tests passing while the false `<example>` warning returns | **NOT TESTED BY SUBMITTED ORACLE** | **UNPROVEN** |
| Parser semantics should match what Claude Code itself accepts | `validate-agent.sh` implements its own extraction grammar | Product parser is the stronger source of truth | **MISALIGNED / UNVERIFIED until product probe is incorporated** | **REVIEW REQUIRED** |

## Reviewer-facing conclusion

```text
submitted regression             internally green
product parser on claimed-valid fixtures  REJECT
oracle alignment                 CONTRADICTED
multi-line regression protection UNPROVEN

overall:
do not upgrade red→green submitted-test evidence into product correctness
```

The useful distinction is:

> the submitted judge may distinguish revisions while still disagreeing with the product's authoritative semantics.
