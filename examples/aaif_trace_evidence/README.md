# AAIF #44: independent approval-to-execution trace observer (experimental)

**Status:** local evidence adapter; not an accepted AAIF contract, official conformance suite, OTel semantic convention or physical-effect verifier.

This CounterProof experimental module reads [Foreman's public cross-process OTLP/HTTP capture](https://github.com/karank2512/Foreman/blob/2541dc0f58d34bc113ad2064da9510e444b24504/docs/otel-evidence/web-worker-receipt.ndjson). It never imports Foreman/AAIF interpretation code. Rather than building a new trace SDK or competing with [AAIF #42 test-kit PR #57](https://github.com/aaif/wg-observability-and-traceability/pull/57), it audits the missing *approval / execution* part of [AAIF #44](https://github.com/aaif/wg-observability-and-traceability/issues/44), and produces narrow, falsifiable answers.

## Offline reproducibility (Python >= 3.10, stdlib only)

From this repository root:

```sh
python examples/aaif_trace_evidence/reader.py examples/aaif_trace_evidence/foreman-projection.json > /tmp/foreman-approval-observation.json
python -m unittest discover -s tests -p test_aaif_trace_evidence.py -v
```

Or supply the unmodified, pinned upstream OTLP capture after downloading it yourself from the source URL:

```sh
python examples/aaif_trace_evidence/reader.py /path/to/web-worker-receipt.ndjson
```

**Input modes:** official OTLP/JSON envelopes (NDJSON, one HTTP record per line), single OTLP/JSON export, or the checked-in source-derived *lossy* projection. The projection intentionally preserves only decision events, `execute_tool` spans, execution ID, call ID, source service and trace/span identity. It omits unrelated checkpoints and numerous vendor-only attributes. It is **not** the raw Foreman file and the tests here do not claim that the raw file was downloaded and executed. To reproduce from source, download the source and run the original NDJSON through the reader; compare the projected relationships.

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

**Scope boundary:** source claim is `observed trace relationships`, not conformance, authorization validity, custody/authority, full capture completeness, physical action, or exact-once external effects. The reader uses the source-specific `foreman-web` role for terminal decisions; generalizing to other runtimes needs an explicit source mapping, not a silent default.

## Upstream destination

Relevant tasks are AAIF [#41 contract](https://github.com/aaif/wg-observability-and-traceability/issues/41), [#42 existing test kit](https://github.com/aaif/wg-observability-and-traceability/issues/42), [#44 approvals/effects](https://github.com/aaif/wg-observability-and-traceability/issues/44), and [#45 independent interpretation](https://github.com/aaif/wg-observability-and-traceability/issues/45). Align the expected answer schema with the WG owners **after** they confirm where evidence belongs; do not copy this experimental status enum into an unapproved AAIF schema. No new issue/PR has been created in the WG merely to publish this experiment.