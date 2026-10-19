---
name: counterproof-pr-proof
description: Use this skill when an AI coding agent claims a bug is fixed or a PR is ready, and a reviewer needs reproducible before-versus-after evidence for the exact changed tests.
version: "0.1.0"
license: apache-2.0
compatibility: Requires Git checkout, local test runner, and optional counterproof CLI
metadata:
  owner: hippoley
  domain: software-verification
  tags: [agent, pull-request, regression, proof, evidence, ci-cost]
---

# CounterProof PR Evidence Skill

## Purpose

Assess whether the same changed test distinguishes the proposed fix from its base revision, and state the exact limits of the evidence. Do not infer a merge recommendation.

## When to use

Use when a coding agent asserts that it fixed a bug, submits a regression test, or shows green CI as proof. Do NOT use when the request is only to write unrelated code, generate a general Skill, or deploy arbitrary third-party Skills.

## Procedure

1. Identify the precise behavioral claim, base revision, proposed revision, and changed test files. Never invent missing commits or observed results.
2. Find the narrowest **local** test command that runs those exact tests; prefer it over broad paid CI. If exact tests cannot be isolated, report that proof will be weaker.
3. If CounterProof is installed, start with `counterproof check` from the candidate repository. Read its status and evidence scope rather than equating exit code 0 with product correctness.
4. With an explicitly approved local test runner and valid base revision, compare HEAD with BASE using the same tests and unchanged judge. Record runner errors as inconclusive, not behavior failures.
5. Preserve artifact references and the tool's verdict, including product-oracle limitations. A passing changed test on both revisions is NOT_WITNESSED, not a successful regression proof.
6. Report the claim, observed candidate identities, oracle/test scope, what was and was not run, and any unverified production behavior. Never fabricate a receipt or third-party adoption.
7. Do not modify repository workflows or trigger GitHub Actions just for a demonstration. `counterproof init` writes CI files and requires a separate, explicitly authorized code change; default to local tests.

## Gotchas

- WITNESSED applies only to the scoped changed-test evidence and observed candidates.
- Infrastructure error, setup failure, missing dependency, or timeout is INCONCLUSIVE unless an independent oracle says otherwise.
- Do not equate CI green, approval, and production correctness.
- Do not execute unknown SKILL.md scripts or transmit secrets.
- Static `counterproof skill inspect` is heuristic and not an independent behavioral evaluation.

## Validation

Include the exact commands, BASE/HEAD identifiers, evidence classification, and any missing oracle. If no executable check ran, say NOT_RUN. Favor negative test cases that could disprove the proposed fix.

## References

- CounterProof CLI: https://github.com/hippoley/CounterProof
- Skill Manager: https://github.com/xingkongliang/skills-manager (separate upstream app, MIT)
