# CounterProof Reality Lab

CounterProof is tested against real AI-assisted pull requests before new proof features are treated as product requirements.

The rule is simple:

> real reviewer uncertainty first; product code second.

## Field cases

| External PR | Reality question | Result | What CounterProof learned |
|---|---|---|---|
| [rundef/async_rithmic#53](https://github.com/rundef/async_rithmic/pull/53) | Does the submitted Claude-written regression actually distinguish the fix from old code? | **WITNESSED, but reviewer need not met** | Same changed test passed on HEAD and failed on BASE, but the maintainer said their real uncertainty was production reproduction, backward compatibility, and risk to existing users. The witness was technically valid without being decision-useful. |
| [openai/codex-plugin-cc#731](https://github.com/openai/codex-plugin-cc/pull/731) | Do the changed tests prove the original fail-open bug, and do they also answer later reviewer concerns? | **WITNESSED + proof boundary** | The tests prove the original bug, but not later 0600/atomic-write concerns. Green evidence must not silently expand its claim. |
| [openai/codex-plugin-cc#456](https://github.com/openai/codex-plugin-cc/pull/456) | What if the thing being fixed is the test harness/environment isolation itself? | **NOT WITNESSED + REVIEW REQUIRED** | Direct BASE/HEAD reproduction supports the bug, but ordinary witness is withheld because changed test support is part of the fix. |
| [MetrolistGroup/Metrolist#4097](https://github.com/MetrolistGroup/Metrolist/pull/4097) | Does a BASE non-zero exit always count as regression evidence? | **INCONCLUSIVE** | No. The BASE failed during Kotlin test compilation, not at a behavioral assertion. This produced the structured `json-v1` result protocol. |
| [anthropics/claude-code#89404](https://github.com/anthropics/claude-code/pull/89404) | What if the submitted tests are internally green but disagree with the product's authoritative parser? | **[ORACLE CONTRADICTED](../reality/claude-code-89404/ORACLE_DISAGREEMENT.md)** | Reviewer-supplied product-oracle evidence shows `claude plugin validate --json` rejects fixtures the submitted validator accepts, while the submitted suite can remain 5/5 green even when the multi-line extraction behavior regresses. CounterProof publishes this as an external-oracle contradiction, not as an independently executed Claude runtime replay. |
| [continuedev/continue#12576](https://github.com/continuedev/continue/pull/12576) | Can CounterProof replay a package-local Vitest regression inside a large JS/TS monorepo? | **[WITNESSED](../reality/continue-12576/WITNESS.md)** | The real PR exposed two product gaps first: `*.vitest.ts` discovery and package-local `core/node_modules` closure. After both fixes, HEAD was 5/5 PASS and BASE was 4/5 PASS, 1 FAIL; the BASE failure directly hits the legacy `tabAutocompleteModel` migration claim. |
| [topoteretes/cognee#5161](https://github.com/topoteretes/cognee/pull/5161) | What if local safety tests pass but a human reviewer reproduces a broader end-to-end failure mode those tests never exercise? | **Human oracle CONTRADICTED** | The vector adapter refusal test is narrow; reviewer evidence shows graph deletion can happen before the refusal propagates. CounterProof records the human reproduction as an external oracle instead of pretending it ran PostgreSQL itself. |
| [vercel/ai#17096](https://github.com/vercel/ai/pull/17096) | What if two newly added tests have different evidentiary value, while a stronger production claim lives outside the test suite? | **[WITNESSED + NOT WITNESSED + UNVERIFIED](../reality/vercel-ai-17096/CLAIM_MATRIX.md)** | Host→bridge sandbox forwarding is red→green; the new schema test passes on BASE and HEAD; real Claude Agent SDK enforcement remains an external production oracle. |
| [crewAIInc/crewAI#7721](https://github.com/crewAIInc/crewAI/pull/7721) | What if CI is green and one submitted regression is genuinely witnessed, but adjacent claims still fail independent probes? | **WITNESSED + claim contradiction** | The env-var noninteractive tracing path is red→green, while an independent HEAD probe shows programmatic `tracing=True` still yields sharing=false; malformed persisted consent also needs review. A single green badge would hide that boundary. |
| [PrefectHQ/prefect#23146](https://github.com/PrefectHQ/prefect/pull/23146) | What if a real regression is witnessed by **existing** tests only under a specific environment? | **NO CHANGED TESTS + environment witness** | Automatic changed-test discovery found 0 tests, but under `TZ=America/Los_Angeles` the same 126 existing tests were BASE 112/126 vs HEAD 126/126. Evidence set and environment can both be first-class proof inputs. |
| [clash-verge-rev/clash-verge-rev#7991](https://github.com/clash-verge-rev/clash-verge-rev/pull/7991) | What if ownership evidence is strong but the production race is not stably reproducible? | **Open Reality Probe** | Ownership / anti-slop review and claim-level proof are complementary. A scoped, honest PR can deserve review while production-causal reproduction remains explicitly absent. |
| [mydcc/cachy-app#2279](https://github.com/mydcc/cachy-app/pull/2279) | Can CounterProof supply the before-state evidence another verifier correctly refuses to infer from current-head green CI? | **[WITNESSED](../reality/cachy-app-2279-red-green.md)** | The exact submitted XSS component test was HEAD 3/3 PASS and BASE 2 FAIL / 1 PASS when transplanted unchanged. This turns a historical red-first clause from prose into candidate-bound execution evidence without claiming the whole requirement is proven. |
| [gramps-project/gramps#2484](https://github.com/gramps-project/gramps/pull/2484) | What if the reviewer asks “did this fail before?” but the PR changes the fixture rather than the existing test file? | **[WITNESSED CHALLENGE / REPAIR TRIAD](../reality/gramps-2484/TRIAD_PROOF.md), no adoption** | Trusted run #36224298359 executed three states under the same RelaxNG oracle: BASE+original fixture PASS, BASE+submitted fixture FAIL, HEAD+submitted fixture PASS. CounterProof publishes this as a challenge/repair triad rather than mislabeling it CONTROL/BAD/REVERT. The original reviewer later said the question was curiosity rather than a request for additional evidence. |
| [clash-verge-rev/clash-verge-rev#8017](https://github.com/clash-verge-rev/clash-verge-rev/pull/8017) | Does a focused submitted regression prove the user-facing fix, or only the new implementation contract? | **WITNESSED_BEHAVIOR after implementation-coupled test** | The submitted test was only implementation-coupled, so a second [trusted behavior replay](https://github.com/hippoley/CounterProof/actions/runs/36391467118) injected the same API-neutral probe into exact BASE and HEAD and called the production `Config::apply_all_and_save_file()` path. With no staged draft, BASE replaced `verge.yaml` (inode + mtime changed) while HEAD left it untouched; with a staged draft, both candidates still saved the change. The user-facing exit-write claim is therefore witnessed without depending on the new `Draft::apply() -> bool` API. |
| [mem0ai/mem0#7183](https://github.com/mem0ai/mem0/pull/7183) | What happens when executable evidence is already strong but the maintainer still cannot merge? | **Evidence independently confirmed; merge still blocked** | The maintainer independently reproduced BASE failures / HEAD passes and verified that the new tests bite the implementation. The remaining blockers were cross-language scope, an overlapping PR, and issue-closure semantics. CounterProof can reduce evidence uncertainty, but it does not replace scope/ownership/product decisions. |
| [ublue-os/bluefin#4539](https://github.com/ublue-os/bluefin/pull/4539) | What if a real lab check passes because it proves the configuration exists, while the user-visible login/session invariant is never exercised? | **WITNESSED implementation delta; behavior/safety scope insufficient** | The merge-time lab check verified the drop-in file and systemd ordering, but a later keyring-unlock regression triggered revert #4685. Current projectbluefin/testsuite now has real GNOME-session portal health checks, yet no Secret/keyring/PAM-specific guard was found. This case produced explicit evidence scope semantics: `IMPLEMENTATION < BEHAVIOR < SAFETY`. |
| [aboutcode-org/scancode.io#2207](https://github.com/aboutcode-org/scancode.io/pull/2207) | Can an AI-assisted PR whose author could not run the Django suite still supply claim-relevant executable evidence? | **[WITNESSED behavior delta](../reality/scancode-2207/MAINTAINER_HANDOFF.md)** | [Trusted replay](https://github.com/hippoley/CounterProof/actions/runs/36373412716) used ScanCode.io's own PostgreSQL/Django CI environment. The exact submitted test passed on HEAD and failed on BASE with `CommandError: ... input_location`, directly reproducing issue #2203's user-visible requirement rather than failing on setup or a new implementation-only API. The linked handoff compresses the receipt into a reviewer-facing before/after summary. |

## Reality-probe status

A cross-reference is **not** adoption. The Lab separates outbound contact from actual external feedback.

### Validated loop

- [#13 — codex-plugin-cc#731 claim boundary](https://github.com/hippoley/CounterProof/issues/13) — **completed**. An external reviewer confirmed the manual matrix shape, reviewed the automated artifact, and said they would use it in review. That feedback produced the merged `claim-matrix` surface.
- [#42 — CounterProof as a verifier input to Codex PROVE](https://github.com/hippoley/CounterProof/issues/42) — **completed interoperability boundary**. The PROVE maintainer chose ordinary REQ-ID Evidence, rejected a new packet/adapter, and later clarified stale-evidence semantics: affected evidence must be rerun; demonstrably unrelated changes can permit scoped reuse only with an established dependency boundary and recorded reason. CounterProof captured those rules in the runnable handoff without expanding into orchestration.

### Demand-side probes

- [gradle/gradle #39129](https://github.com/gradle/gradle/pull/39129) — **NOT_WITNESSED before reviewer intervention**. [Trusted replay](https://github.com/hippoley/CounterProof/actions/runs/36371344832) ran the exact submitted test on the PR HEAD and transplanted it unchanged onto the exact PR BASE; both passed. The test may encode a useful historical invariant, but it does not establish a candidate delta or identify which historical fix it covers. This matches the maintainer's later concern that the test “may or may not cover a specific fix.” Repository history also shows the fixed-point/simplification line has explicit fixes tied to #32945, while the PR description originally linked the test to #28962 without identifying a fixing commit.
- [Gradle #39129](https://github.com/gradle/gradle/pull/39129) — **NOT_WITNESSED as a candidate delta; claim provenance mismatch exposed before review.** The PR changes only `NormalizingExcludeFactoryTest.groovy`; no production file changes. Its submitted test passes on PR HEAD, so replaying the same test onto the exact PR BASE cannot establish a fix introduced by this PR. The historical linkage is also weaker than the PR description implied: #28962 reports a Gradle 8.7 dependency-resolution deadlock, while the fixed-point/simplification implementation touched by the test has an explicit later fix chain for [#32945](https://github.com/gradle/gradle/issues/32945), including commit `ceaa5c7` ("Fix exclude simplification logic", `Fixes #32945`). The Gradle maintainer later closed the PR because the test may or may not cover a specific fix. This is a strong demand-side example where claim/evidence binding could have been challenged before human review.

These cases test whether CounterProof reduces **maintainer review cost**, not whether neighboring verification projects agree with its semantics.

- [Bluefin #4539 / #4685](https://github.com/ublue-os/bluefin/pull/4539) — **active oracle-scope probe.** The historical pre-merge lab check genuinely witnessed the configuration delta but did not exercise the Secret portal or safe PAM/keyring startup path; the change was reverted after a user-visible regression. Current `projectbluefin/testsuite` has QEMU + real GNOME-session portal checks, but no Secret/keyring-specific guard was found. CounterProof #96 and PR #97 are testing whether making evidence depth machine-readable prevents a shallow green check from silently proving a deeper claim.
- [clash-verge-rev #8017](https://github.com/clash-verge-rev/clash-verge-rev/pull/8017) — **behavior-level execution is now complete.** The first replay exposed that the submitted regression was only implementation-coupled. A second candidate-neutral replay then exercised the production exit-save path directly: no staged draft caused an observable file replacement on BASE but no write on HEAD, while staged changes were still persisted on both. Verdict: **WITNESSED_BEHAVIOR**. Reviewer usefulness feedback is still pending; an attempted upstream follow-up is currently blocked by connector 403 and is not counted as negative feedback.
- [mem0 #7183](https://github.com/mem0ai/mem0/pull/7183) — useful negative boundary. The maintainer manually performed strong before/after verification, yet review remained blocked by scope and competing implementation concerns. Evidence triage is only one slice of review cost.
- [ScanCode.io #2207](https://github.com/aboutcode-org/scancode.io/pull/2207) — **strong positive evidence-side case; handoff artifact complete, upstream delivery blocked by connector permissions.** CounterProof replayed the exact submitted test in ScanCode.io's own PostgreSQL/Python CI shape: HEAD PASS; BASE FAIL because the old CLI still requires `input_location`. The reviewer-facing [handoff artifact](../reality/scancode-2207/MAINTAINER_HANDOFF.md) is now complete. An outbound comment attempt on 2026-10-07 returned GitHub integration `403 Resource not accessible by integration`; this is **not maintainer feedback** and is not counted as a negative adoption signal. Follow-up is tracked in [#129](https://github.com/hippoley/CounterProof/issues/129).

### External feedback received; follow-up still active

- [#16 — submitted judge vs authoritative oracle](https://github.com/hippoley/CounterProof/issues/16) — external reviewers confirmed the oracle-alignment model and identified a provenance trust boundary. An external contributor proposed hardening in [#50](https://github.com/hippoley/CounterProof/pull/50), but that PR closed unmerged. CounterProof therefore does not count it as adopted; the compatible oracle-source requirement is being carried forward against current main in [#133](https://github.com/hippoley/CounterProof/pull/133).

### Waiting for external feedback

These are useful public probes, but **no external response is counted yet**:

- [#15 — when the PR fixes the judge itself](https://github.com/hippoley/CounterProof/issues/15)
- [#20 — ownership evidence vs production reproduction](https://github.com/hippoley/CounterProof/issues/20)
- [#22 — independent Continue #12576 witness](https://github.com/hippoley/CounterProof/issues/22)
- [#28 — CrewAI #7721 claim/evidence boundary](https://github.com/hippoley/CounterProof/issues/28)
- [#30 — human-review concerns replayed on Prefect #22698](https://github.com/hippoley/CounterProof/issues/30)
- [#32 — existing-test + environment evidence on Prefect #23146](https://github.com/hippoley/CounterProof/issues/32)
- [#40 — PR-Agent artifact handoff](https://github.com/hippoley/CounterProof/issues/40)
- [#45 — Cognee #5161 human-oracle contradiction](https://github.com/hippoley/CounterProof/issues/45)
- [#46 — Mem0 #6516 evidence-workflow interview](https://github.com/hippoley/CounterProof/issues/46)
- [#48 — Vercel AI #17096 mixed evidence boundary](https://github.com/hippoley/CounterProof/issues/48)
- [#64 — claimproof runtime receipt vs candidate-bound PR evidence](https://github.com/hippoley/CounterProof/issues/64) — outbound boundary probe only. Current claimproof receipts are session-local command + exit-code evidence; the open question is whether that ephemerality is intentional or whether a reusable candidate-bound export belongs upstream.
- [PRTruth #361 — BASE→HEAD receipt as historical evidence](https://github.com/eissasoubhi/PRTruth/issues/361) — external interop probe. CounterProof has now supplied one executable Batch 29 witness; maintainer feedback on whether it fits PRTruth's existing evidence-plugin contract is still pending.
- [Qwen Code #9124 — stale approve-on-green execution evidence](https://github.com/QwenLM/qwen-code/issues/9124) — direct upstream comment. CounterProof contributed one concrete boundary: evidence freshness should track the evidence-producing surface, not only changed test filenames. No response/adoption counted yet.
- [AWS AI-DLC #854 — review-ladder execution-evidence boundary](https://github.com/awslabs/aidlc-workflows/issues/854#issuecomment-5861863962) — direct upstream comment posted by `hippoley`. Asks whether BASE→HEAD execution semantics belong inside the multi-lane review ladder or should stay external. No upstream response counted yet.
- [AVERA #12 — experimental `avera.check/v0` interoperability](https://github.com/mikheil-galoian/avera/issues/12) — **external maintainer response received; v0 landed upstream; downstream consumption under validation.** The AVERA maintainer explicitly wanted downstream reuse, opened the v0 field draft, then merged [AVERA #14](https://github.com/mikheil-galoian/avera/pull/14) with a frozen example and digest contract. CounterProof [#134](https://github.com/hippoley/CounterProof/pull/134) pins that upstream example and independently checks envelope digest + JUnit input-byte hashes while preserving AVERA verdict semantics. This is an interoperability implementation signal, not CounterProof adoption or a merge endorsement.
- [#82 — agent-done-or-not receipt handoff](https://github.com/hippoley/CounterProof/issues/82) — outbound maintainer probe. Tests whether current-candidate proof-of-done receipts should be reusable as upstream evidence for BASE→HEAD reviewer verification.
- [KiroCrew #13456 — computed-vs-published verdict boundary](https://github.com/kirodotdev/KiroCrew/issues/13456#issuecomment-5861866169) — direct upstream comment posted by `hippoley`. Proposes an explicit publication-state / `INCOMPLETE` distinction when a verdict was computed but never reached the authoritative slot. No maintainer response to the proposal counted yet.

### Closed probes with negative / no-adoption feedback

- [#11 — async_rithmic reviewer usefulness](https://github.com/hippoley/CounterProof/issues/11) — **completed, negative usefulness signal**. The maintainer said the review blocker was production reproduction and backward-compatibility risk, not whether the submitted regression was red on BASE. Do not add features around this case.
- [#71 — retrospective Gramps reviewer usefulness](https://github.com/hippoley/CounterProof/issues/71) — **completed, no adoption signal**. The replay exposed a real product gap and produced explicit test + support-file replay, but the original reviewer said the question was curiosity and had no additional evidence request.

### Open intake

- [#17 — bring an agent PR you do not trust](https://github.com/hippoley/CounterProof/issues/17) — anyone can submit a public PR plus the claim that still feels under-evidenced.

## What reviewers have asked for

The first substantive external reviewer feedback changed the design target.

In [Reality Probe #13](https://github.com/hippoley/CounterProof/issues/13), reviewer `sylvesterkaczmarek` said the separation between a witnessed property and still-unproven review concerns was materially useful. The requested output shape was a compact **claim / evidence matrix** containing:

- review claim or failure mode;
- exact test(s);
- BASE result;
- HEAD result;
- whether the test oracle was independently checked;
- status such as `WITNESSED`, `CONTRADICTED`, or `UNPROVEN`;
- a short assertion / failure excerpt for witnessed properties.

In [Reality Probe #16](https://github.com/hippoley/CounterProof/issues/16), the same reviewer asked for **oracle alignment** to stay separate from ordinary red→green replay:

```text
submitted regression  BASE fail / HEAD pass
authoritative oracle  accept / reject
oracle alignment      aligned / contradicted / unverified
claim status          proven / contradicted / unproven
```

Those requests were first tested as manual matrices against the exact PRs that produced the feedback. After the reviewer confirmed the shape a second time, the smallest mechanical version was merged in [#38](https://github.com/hippoley/CounterProof/pull/38):

```bash
counterproof claim-matrix claims.yml
```

The command still refuses to invent the hard parts. Claims and oracle authority remain explicit human/upstream inputs. CounterProof validates the evidence vocabulary and mechanically derives the claim boundary.

Current axes:

```text
submitted-test evidence  WITNESSED / NOT_WITNESSED / UNPROVEN
oracle alignment         ALIGNED / CONTRADICTED / UNVERIFIED
```

This is the Reality Lab contract: **human review feedback becomes a probe before it becomes product code, and merged code is not treated as validation until it returns to the reviewer.**

## What counts as useful feedback

A maintainer does not need to adopt CounterProof.

The most valuable feedback is one sentence such as:

- “This would save me time if it also showed X.”
- “This does not help because Y is the actual uncertainty.”
- “I would trust this only if the environment / provider / fixture were Z.”
- “This claim should never be called witnessed because ...”

Those responses decide what gets built next.

## Neighboring systems are not competitors by default

CounterProof does not need to replace AI-slop gates, automated code review, CI, or maintainer judgment.

For example, clash-verge-rev's AI-slop review asks whether a contribution shows enough **ownership and problem understanding** to deserve maintainer attention. CounterProof asks a later question: **what does the submitted evidence actually prove?**

Those can compose:

```text
ownership gate
      ↓
claim / evidence boundary
      ↓
human review
```

The Reality Lab will prefer integrations and evidence handoffs over inventing another score for work another tool already does well.

## Evidence is not permission

CounterProof evidence never overrides a repository's contribution policy.

Some projects explicitly allow AI as a coding aid while requiring the human contributor to write their own issue, PR and review communication, understand the work, and avoid autonomous-agent contributions. Astral's public [AI policy](https://github.com/astral-sh/.github/blob/main/AI_POLICY.md) is one concrete example.

CounterProof should help a human reviewer inspect evidence **inside the community's rules**, not act as a technical argument for bypassing those rules.

A useful ordering is:

```text
community contribution policy
        ↓
ownership / intake gate
        ↓
claim / evidence boundary
        ↓
human review
```

## Submit a case

If an AI-assisted PR looks plausible but its evidence does not quite earn your trust, add it to:

**[Bring me an agent PR you don't trust →](https://github.com/hippoley/CounterProof/issues/new?template=reality-probe.yml)**

No CounterProof installation is required.


> An oracle can execute and still be uninterpretable. If a declared fixture or environment prerequisite is missing, record `PRECONDITION_MISSING`; do not promote that run to `ALIGNED` or `CONTRADICTED`.
