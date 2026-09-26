# Contributing to CounterProof

CounterProof grows from real review uncertainty, not from a feature wishlist.

The highest-value contribution is often **not code**.

## Choose a contribution path

CounterProof is currently learning from three different kinds of contribution. They are intentionally separate because each one protects a different proof boundary.

### Reviewer / evidence-semantics partner

You do **not** need to write code.

Bring a real review artifact and tell us where the output would make you believe more than the evidence supports, where it omits a concern you would still check manually, or which provenance would save you from repeating work.

The preferred loop is:

```text
real PR
  -> manual claim/evidence artifact
  -> human reviewer says usable / misleading / missing X
  -> smallest mechanical implementation
  -> the reviewer checks the automated artifact again
```

This is how the claim/evidence matrix and oracle-alignment vocabulary were shaped. A reviewer rejecting bad semantics is a first-class contribution.

### Adversarial evidence contributor

Attack the admission boundary.

Useful contributions construct a minimal case where a receipt or manifest could claim more than its underlying evidence warrants, for example:

- declaring `WITNESSED` without an actual BASE-fail / HEAD-pass transition;
- attaching an `ALIGNED` or `CONTRADICTED` oracle state without auditable provenance;
- reusing evidence after the candidate commit changed;
- changing the test harness or fixture that acts as the judge;
- supplying a green command that never exercised the claimed behavior.

Prefer a focused regression fixture over a broad parser, framework, or policy implementation. CounterProof should validate the proof boundary it owns and leave unrelated standards to existing libraries.

### Evidence consumer / integration partner

Try to consume an existing CounterProof artifact **before** proposing a new SDK, adapter, packet type, or approval layer.

A useful integration experiment answers:

```text
What decision does the downstream tool already own?
What exact CounterProof evidence would reduce uncertainty?
Can the existing report be attached without changing either project's authority?
What field is actually missing after one real handoff?
```

CounterProof classifies evidence scope. A downstream controller, reviewer UI, or policy engine keeps its own decision authority.

If an existing format is enough, the correct contribution may be an acceptance example and no new runtime code.

These are contribution surfaces, not promises of permanent module boundaries. Real review failures can change them.

## 1. Bring a PR you do not trust

If you are reviewing an AI-assisted pull request and the evidence feels weaker than the claim, submit it through the Reality Probe intake:

**https://github.com/hippoley/CounterProof/issues/new?template=reality-probe.yml**

Good cases sound like:

- “The agent says tests pass, but would this test fail before the fix?”
- “The test is green, but the PR changed the test harness too.”
- “CI is green, but the live provider / product parser disagrees.”
- “The bug only reproduces under a specific environment.”
- “The submitted tests prove the original bug, but not the review concern.”
- “A compile/setup failure is being mistaken for behavioral evidence.”

You do not need to install CounterProof first.

A useful submission can be as small as:

```text
PR:
Claim I do not trust:
What would convince me:
```

## 2. Report a proof mistake

CounterProof would rather say **INCONCLUSIVE** than manufacture confidence.

Please open an issue if you find a case where it:

- says **WITNESSED** even though BASE never reached the tested behavior;
- says **CLEAN** even though the PR changed evidence-producing machinery;
- misses a real changed regression test;
- cannot replay the relevant package-local test environment;
- expands a narrow witness into a broader correctness claim;
- disagrees with an authoritative product oracle.

Include the external PR or minimal repository if possible. Real public cases are especially valuable because fixes can be verified against the exact failure that exposed them.

## 3. Help with a Reality Probe

The public field log lives in:

**[docs/REALITY_LAB.md](docs/REALITY_LAB.md)**

A Reality Probe should preserve these boundaries:

1. **Claim** — what exact behavior is being asserted?
2. **Evidence** — which test / command / oracle exercises it?
3. **Before** — what happens on the exact BASE?
4. **After** — what happens on the exact HEAD?
5. **Integrity** — did the PR change the judge, fixture, CI, or support machinery?
6. **Boundary** — what remains contradicted, inconclusive, or unproven?

Do not turn “BASE fail / HEAD pass” into “the PR is correct.”

## 4. Code contributions

Fork the repository and create a focused branch.

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run:

```bash
ruff check .
pytest
```

For changes to Regression Witness or Proof Integrity, add a behavior-level test that demonstrates the failure mode before the fix.

If a real external PR triggered the change, link it in the PR description and re-run the exact case when practical.

## 5. Evidence semantics are part of the API

A CounterProof change is not complete merely because CI is green.

When touching evidence semantics, explicitly state whether the change affects:

- `WITNESSED`
- `NOT WITNESSED`
- `INCONCLUSIVE`
- `REVIEW REQUIRED`
- claim / evidence boundaries
- oracle alignment

Compatibility should never silently weaken a proof threshold.

## 6. Social norm

CounterProof is meant to help reviewers and contributors, not spam them.

When using Reality Probes with another project:

- bring new evidence, not a generic project pitch;
- keep claims narrower than the evidence;
- respect the project's review decision;
- avoid duplicate cross-references or repeated mentions;
- one honest “this does not help because …” is valuable product feedback.

That feedback is welcome even if you never use CounterProof again.
