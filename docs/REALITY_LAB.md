# CounterProof Reality Lab

CounterProof is tested against real AI-assisted pull requests before new proof features are treated as product requirements.

The rule is simple:

> real reviewer uncertainty first; product code second.

## Field cases

| External PR | Reality question | Result | What CounterProof learned |
|---|---|---|---|
| [rundef/async_rithmic#53](https://github.com/rundef/async_rithmic/pull/53) | Does the submitted Claude-written regression actually distinguish the fix from old code? | **WITNESSED** | Same changed test passed on HEAD and failed on BASE. A reviewer-facing receipt is useful when the question is genuinely before/after. |
| [openai/codex-plugin-cc#731](https://github.com/openai/codex-plugin-cc/pull/731) | Do the changed tests prove the original fail-open bug, and do they also answer later reviewer concerns? | **WITNESSED + proof boundary** | The tests prove the original bug, but not later 0600/atomic-write concerns. Green evidence must not silently expand its claim. |
| [openai/codex-plugin-cc#456](https://github.com/openai/codex-plugin-cc/pull/456) | What if the thing being fixed is the test harness/environment isolation itself? | **NOT WITNESSED + REVIEW REQUIRED** | Direct BASE/HEAD reproduction supports the bug, but ordinary witness is withheld because changed test support is part of the fix. |
| [MetrolistGroup/Metrolist#4097](https://github.com/MetrolistGroup/Metrolist/pull/4097) | Does a BASE non-zero exit always count as regression evidence? | **INCONCLUSIVE** | No. The BASE failed during Kotlin test compilation, not at a behavioral assertion. This produced the structured `json-v1` result protocol. |
| [anthropics/claude-code#89404](https://github.com/anthropics/claude-code/pull/89404) | What if the submitted tests are internally green but disagree with the product's authoritative parser? | **Open Reality Probe** | This is the emerging oracle-alignment problem: red→green evidence can still be weak if the judge does not represent product truth. |
| [continuedev/continue#12576](https://github.com/continuedev/continue/pull/12576) | Can CounterProof replay a package-local Vitest regression inside a large JS/TS monorepo? | **[WITNESSED](../reality/continue-12576/WITNESS.md)** | The real PR exposed two product gaps first: `*.vitest.ts` discovery and package-local `core/node_modules` closure. After both fixes, HEAD was 5/5 PASS and BASE was 4/5 PASS, 1 FAIL; the BASE failure directly hits the legacy `tabAutocompleteModel` migration claim. |
| [topoteretes/cognee#5161](https://github.com/topoteretes/cognee/pull/5161) | What if local safety tests pass but a human reviewer reproduces a broader end-to-end failure mode those tests never exercise? | **Human oracle CONTRADICTED** | The vector adapter refusal test is narrow; reviewer evidence shows graph deletion can happen before the refusal propagates. CounterProof records the human reproduction as an external oracle instead of pretending it ran PostgreSQL itself. |
| [vercel/ai#17096](https://github.com/vercel/ai/pull/17096) | What if two newly added tests have different evidentiary value, while a stronger production claim lives outside the test suite? | **[WITNESSED + NOT WITNESSED + UNVERIFIED](../reality/vercel-ai-17096/CLAIM_MATRIX.md)** | Host→bridge sandbox forwarding is red→green; the new schema test passes on BASE and HEAD; real Claude Agent SDK enforcement remains an external production oracle. |
| [crewAIInc/crewAI#7721](https://github.com/crewAIInc/crewAI/pull/7721) | What if CI is green and one submitted regression is genuinely witnessed, but adjacent claims still fail independent probes? | **WITNESSED + claim contradiction** | The env-var noninteractive tracing path is red→green, while an independent HEAD probe shows programmatic `tracing=True` still yields sharing=false; malformed persisted consent also needs review. A single green badge would hide that boundary. |
| [PrefectHQ/prefect#23146](https://github.com/PrefectHQ/prefect/pull/23146) | What if a real regression is witnessed by **existing** tests only under a specific environment? | **NO CHANGED TESTS + environment witness** | Automatic changed-test discovery found 0 tests, but under `TZ=America/Los_Angeles` the same 126 existing tests were BASE 112/126 vs HEAD 126/126. Evidence set and environment can both be first-class proof inputs. |
| [clash-verge-rev/clash-verge-rev#7991](https://github.com/clash-verge-rev/clash-verge-rev/pull/7991) | What if ownership evidence is strong but the production race is not stably reproducible? | **Open Reality Probe** | Ownership / anti-slop review and claim-level proof are complementary. A scoped, honest PR can deserve review while production-causal reproduction remains explicitly absent. |

## Reality-probe status

A cross-reference is **not** adoption. The Lab separates outbound contact from actual external feedback.

### Validated loop

- [#13 — codex-plugin-cc#731 claim boundary](https://github.com/hippoley/CounterProof/issues/13) — **completed**. An external reviewer confirmed the manual matrix shape, reviewed the automated artifact, and said they would use it in review. That feedback produced the merged `claim-matrix` surface.

### External feedback received; follow-up still active

- [#16 — submitted judge vs authoritative oracle](https://github.com/hippoley/CounterProof/issues/16) — external reviewers confirmed the oracle-alignment model and then identified a provenance trust boundary. An external contributor opened [#50](https://github.com/hippoley/CounterProof/pull/50) to harden it; review is still active.
- [#42 — CounterProof as a verifier input to Codex PROVE](https://github.com/hippoley/CounterProof/issues/42) — the PROVE maintainer preferred ordinary REQ-ID Evidence over a new integration protocol. CounterProof implemented that suggestion as a runnable handoff example in [#53](https://github.com/hippoley/CounterProof/pull/53); final maintainer feedback on the example is still pending.

### Waiting for external feedback

These are useful public probes, but **no external response is counted yet**:

- [#11 — async_rithmic reviewer usefulness](https://github.com/hippoley/CounterProof/issues/11)
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
