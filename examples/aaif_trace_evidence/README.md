# AAIF #44: independent approval-to-execution trace observer (experimental)

**Status:** local evidence adapter; not an accepted AAIF contract, official conformance suite, OTel semantic convention or physical-effect verifier.

This CounterProof experimental module reads [Foreman's public cross-process OTLP/HTTP capture](https://github.com/karank2512/Foreman/blob/2541dc0f58d34bc113ad2064da9510e444b24504/docs/otel-evidence/web-worker-receipt.ndjson). It never imports Foreman/AAIF interpretation code. Rather than building a new trace SDK or competing with [AAIF #42 test-kit PR #57](https://github.com/aaif/wg-observability-and-traceability/pull/57), it audits the missing *approval / execution* part of [AAIF #44](https://github.com/aaif/wg-observability-and-traceability/issues/44), and produces narrow, falsifiable answers.

## Offline reproducibility (Python >= 3.10, stdlib only)

From this repository root:

```sh
python examples/aaif_trace_evidence/reader.py examples/aaif_trace_evidence/foreman-projection.json > /tmp/foreman-approval-observation.json
python -m unittest discover -s tests -p test_aaif_trace_evidence.py -v
# Source-pinned raw capture on the published development branch:
python examples/aaif_trace_evidence/reader.py \
  examples/aaif_trace_evidence/foreman-web-worker-raw.ndjson --verify-foreman-blob
```

The full source capture is also committed to this **development branch** as
`foreman-web-worker-raw.ndjson` with its Foreman source and blob SHA recorded below.
The `--verify-foreman-blob` option hashes the exact bytes using Git's `blob <size>\0<bytes>`
object format, and fails closed if the capture changes. This pinned input is a publicly
published **simulated** Foreman capture, not independent production telemetry.

**Input modes:** OTLP/HTTP NDJSON (one receiver record per line), single OTLP/JSON export,
or checked-in *lossy* projection. The projection retains only relevant decisions,
`execute_tool` spans, source identity, tool call and execution IDs, the Foreman approval ID,
and observed timestamps. It drops checkpoints, runtime-private fields, and unrelated
attributes. The projection is **not** a full-fidelity raw export.

**Verification limits:** the exact raw file is now present on the remote development branch.
Tests run against the fixed projection locally. The raw-file integration test runs only when
that file exists (and prints SKIP otherwise). The pinned raw SHA and projection must match on
any GitHub checkout; there is no need for network or hosted CI to run them. This does not
claim we have run the exact raw Python test in an offline environment without the raw file.

## Fixed evidence and expected results

Pinned Foreman Git blob: `2541dc0f58d34bc113ad2064da9510e444b24504`

Original capture: **6 receiver envelopes, 9 spans, 4 tool-decision events**. The checked-in loss-reduced projection includes 7 relevant span records (including two unrelated `read_dataset` execution spans). These counts were cross-checked against the published file with an independent source-side read.

| Observed proposed call | Expected answer | What **cannot** be claimed |
| --- | --- | --- |
| `require_approval → allow`, same execution ID and call ID, 1 matching `execute_tool` span across worker / web traces | `CORRELATED_ALLOW_EXECUTION` | Not evidence that approval gate is unbypassable, or that an external side effect happened exactly once |
| `require_approval → deny`, same execution ID and call ID, 0 matching `execute_tool` spans | `CORRELATED_DENY_NO_OBSERVED_EXECUTION` | Missing span does **not** prove no actual side effect |
| Unrelated `read_dataset` spans | `UNCONFIRMED` approval relation | Do not infer that unrelated tool calls were approved or denied |

All rows carry `physical_effect: UNKNOWN` and `enforcement_proven: false`. Both runs in the source were in Foreman's **Simulated** mode. The receiver was a custom HTTP endpoint, not a real OTel Collector. These are cross-process records from **one application**, not independently instrumented producers. OTel PR [#535](https://github.com/open-telemetry/semantic-conventions-genai/pull/535) is still a proposed event shape; it is not a published convention.

## Counterexamples / fail-closed behavior

Offline unit tests mutate the pinned excerpt and check:

- Delivery duplication does not double-count identical span identities.
- Changing the content under the same span identity is invalid.
- Arrival order of records does not change answers.
- Distinct second `execute_tool` spans with the same execution/call IDs are contradictions, not duplicates.
- A denied call with a matching observed execution span is contradictory.
- Absent allow or missing execution export yields `UNCONFIRMED` (never a fabricated denial or completion).
- Colliding tool call IDs across different `gen_ai.agent.execution.id` values do not cross-join.
- Mismatched tool names, conflicting terminal decisions, missing IDs and unsupported decision values cannot silently pass.
- **Foreman approval ID mismatches**, even when execution and tool-call IDs match, are contradictions.
- Same-timestamp events with different call IDs or approval IDs are never accidentally deduplicated.
- Timestamp inversions across worker and web **downgrade** correlation to `UNCONFIRMED`; clock order is an unauthenticated diagnostic, not proof of causal order.
- Raw source integrity is independently checked against its Git blob SHA, never inferred from its filename.
- Incomplete approval paths return exit status `1` (review needed), malformed/corrupt source `2`, successful observed relationships `0`. Unrelated tool calls remain `UNCONFIRMED` without failing the run.

**Scope boundary:** source claim is `observed trace relationships`, not conformance, authorization validity, custody/authority, full capture completeness, physical action, or exact-once external effects. The reader uses the source-specific `foreman-web` role for terminal decisions; generalizing to other runtimes needs an explicit source mapping, not a silent default.

## Upstream destination

Relevant tasks are AAIF [#41 contract](https://github.com/aaif/wg-observability-and-traceability/issues/41), [#42 existing test kit](https://github.com/aaif/wg-observability-and-traceability/issues/42), [#44 approvals/effects](https://github.com/aaif/wg-observability-and-traceability/issues/44), and [#45 independent interpretation](https://github.com/aaif/wg-observability-and-traceability/issues/45). Align the expected answer schema with the WG owners **after** they confirm where evidence belongs; do not copy this experimental status enum into an unapproved AAIF schema. No new issue/PR has been created in the WG merely to publish this experiment.

## AAIF #42 / #44 contract alignment (not upstream acceptance)

[PR #57](https://github.com/aaif/wg-observability-and-traceability/pull/57) already supplies
`basis.json` / `records.otlp.json` / `expected.json` for **effect correlation** with a
reference reader and a deliberately naive reader. This prototype supplies a distinct
**approval-to-execution** check against a real source export: proposal decision,
reviewer decision, observed tool span, source process, and an optional scope-specific
approval ID. It does not reinterpret #57's `effect: confirmed` as a physical outcome.

The next upstream contract question is where this additional relation belongs:
#42's test kit, #44's relationship coverage, or the evidence-first register in PR #60.
No new AAIF enum, schema or governance entitlement is asserted.

### Observed vs trusted

- `CORRELATED_ALLOW_EXECUTION`: recorded approval and one matching **observed** execute span.
- `CORRELATED_DENY_NO_OBSERVED_EXECUTION`: recorded denial and **no matching observed** execute span.
- `CONTRADICTED`: explicitly conflicting records or invalid scoped mapping.
- `UNCONFIRMED`: missing or incomparable evidence (including inconsistent clock order).

Neither a `CORRELATED_*` status nor monotonic-looking timestamps prove enforcement,
complete export, external effect, single execution in reality, or clock synchronization.
The source uses proposed OTel fields from #535, not ratified standard conventions.

**Third-party provenance:** the pinned NDJSON is copied from
[Foreman](https://github.com/karank2512/Foreman) (Apache-2.0), original Git blob
`2541dc0f58d34bc113ad2064da9510e444b24504`. This repository keeps an
unchanged source capture plus a separately authored, intentionally lossy projection.