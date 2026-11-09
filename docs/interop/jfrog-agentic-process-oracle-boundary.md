# JFrog Agentic Process Evidence — claim/oracle composition note

**Upstream request:** [CounterProof #131](https://github.com/hippoley/CounterProof/issues/131), where a participant in `jfrog/agentic-process-evidence` explicitly invited a spec PR after clarifying the proposed scope.

**Upstream source pinned:** `jfrog/agentic-process-evidence/spec/agentic-process-evidence.md`, Git blob `f93a12f971a43f0030018c3086a12b05f638270f`, read 2026-11-09.

**Deliverable:** [jfrog-agentic-process-oracle-boundary.patch](jfrog-agentic-process-oracle-boundary.patch). This is a validated context patch that adds a short subsection immediately after **Process result** and before **Development process custom data**. It does **not** modify the JFrog repository, predicate schema, or existing result vocabulary.

The requested boundary is:

1. A process result records what the declared agentic process did and how it ended.
2. Even a signed and re-executed passing test does not establish that the test is sufficient for an unrelated bug/requirement claim.
3. A downstream consumer or policy engine establishes claim-to-oracle relevance and scope separately; process evidence remains composable and narrowly defined.

## Why publish as a patch rather than claim an upstream PR?

The connected GitHub integration returned `403 Resource not accessible by integration` when attempting to create a branch in `jfrog/agentic-process-evidence`. No writable `hippoley/agentic-process-evidence` fork is currently accessible. We therefore preserve a patch with exact source context and invite the upstream contributor/maintainer to apply it or to indicate a permitted fork/PR path. **No upstream submission, approval, or adoption is claimed.**

## Acceptance

The patch should apply to the pinned upstream blob with context matching exactly. No new normative fields are introduced. The note must not claim that all completed processes are correct or that signed evidence itself establishes the authority of the evaluated contract.
