# Oracle Alignment Matrix — anthropics/claude-code #89404

Source PR: https://github.com/anthropics/claude-code/pull/89404

This is a manual Reality Probe for a case where the submitted test suite and the product's authoritative behavior disagree.

## Evidence sources

- submitted regression suite: `plugins/plugin-dev/skills/agent-development/scripts/validate-agent.test.sh`
- submitted judge: `validate-agent.sh`
- authoritative product probe identified by reviewers: `claude plugin validate`
- reviewer evidence:
  - https://github.com/anthropics/claude-code/pull/89404#issuecomment-5530003497
  - https://github.com/anthropics/claude-code/pull/89404#pullrequestreview-5190939241

## Claim / evidence matrix

| Review claim / failure mode | Submitted-test evidence | Authoritative oracle probe | Oracle alignment | Overall claim |
|---|---|---|---|---|
| Warning/error counters should not abort validation under `set -e` | **UNPROVEN** — not independently replayed by CounterProof | No separate product-oracle probe for this narrow claim | **UNVERIFIED** | **UNPROVEN** |
| Plugin-dev's own agent fixtures are valid and should exit 0 | Submitted suite expects exit 0, but no independent BASE/HEAD replay was run | Reviewers report `claude plugin validate` rejects those fixtures as invalid YAML/frontmatter | **CONTRADICTED** | **CONTRADICTED by product oracle** |
| Multi-line description extraction is protected by the submitted suite | Reviewer reports the suite still passes when the extraction fix is reverted | Reverting the fix restores the false `<example>` warning | **CONTRADICTED** | **NOT WITNESSED by submitted judge** |

## Reviewer-facing conclusion

```text
counter / set -e behavior
  submitted-test evidence  UNPROVEN
  oracle alignment         UNVERIFIED
  overall                  UNPROVEN

fixture validity
  submitted-test evidence  UNPROVEN
  oracle alignment         CONTRADICTED
  overall                  CONTRADICTED by product oracle

multi-line extraction protection
  submitted-test evidence  NOT WITNESSED
  oracle alignment         CONTRADICTED
  overall                  submitted judge does not protect the product behavior
```

The useful distinction is mechanical: a submitted judge may be internally green while still disagreeing with product truth.
