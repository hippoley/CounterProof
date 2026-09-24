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

## Public probes

- [#11 — async_rithmic reviewer usefulness](https://github.com/hippoley/CounterProof/issues/11)
- [#13 — claim boundary on codex-plugin-cc#731](https://github.com/hippoley/CounterProof/issues/13)
- [#15 — when the PR fixes the judge itself](https://github.com/hippoley/CounterProof/issues/15)
- [#16 — when submitted tests disagree with the authoritative oracle](https://github.com/hippoley/CounterProof/issues/16)
- [#17 — bring an agent PR you do not trust](https://github.com/hippoley/CounterProof/issues/17)

## What counts as useful feedback

A maintainer does not need to adopt CounterProof.

The most valuable feedback is one sentence such as:

- “This would save me time if it also showed X.”
- “This does not help because Y is the actual uncertainty.”
- “I would trust this only if the environment / provider / fixture were Z.”
- “This claim should never be called witnessed because ...”

Those responses decide what gets built next.

## Submit a case

If an AI-assisted PR looks plausible but its evidence does not quite earn your trust, add it to:

**[Bring me an agent PR you don't trust →](https://github.com/hippoley/CounterProof/issues/17)**

No CounterProof installation is required.
