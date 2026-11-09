# AAIF #44: Goose chat-attempt coverage — experimental consumer probe

This is **not** an AAIF specification, a normative conformance test, or proof of real Goose runtime behavior. It is a small OTLP/JSON reader that demonstrates which exported `chat` spans and **reported** token fields can be interpreted without silently fabricating missing data or declaring a hidden retry absent.

Source reconnaissance: [aaif-goose/goose pinned tree 398165c9376e61157ba9cfdd487ca9622d716955](https://github.com/aaif-goose/goose/blob/398165c9376e61157ba9cfdd487ca9622d716955/crates/goose-agent/src/inference.rs) declares a `chat` span, `gen_ai.request.id`, and `gen_ai.usage.*` fields. A separate [Goose telemetry implementation](https://github.com/aaif-goose/goose/blob/398165c9376e61157ba9cfdd487ca9622d716955/crates/goose/src/agents/gen_ai_telemetry.rs) conditionally records provider-request ID and usage. Presence in source is not proof that any particular exporter produces every field.

Run tests (Python >=3.10, stdlib only):

```sh
python -m unittest discover -s examples/interop/aaif-44-goose-call-coverage -p 'test_*.py' -v
python examples/interop/aaif-44-goose-call-coverage/audit.py examples/interop/aaif-44-goose-call-coverage/sample.otlp.json
```

The reader handles **one OTLP/HTTP JSON trace envelope** containing `resourceSpans / scopeSpans / spans`; it does not fetch a real trace, verify exporter trust, or read logs/events. It only considers spans whose `gen_ai.operation.name` is `chat`.

Outcomes:

- **PASS**: exported chat spans have unique `(traceId, spanId)`, nonempty request IDs and complete nonnegative reported usage. Exact repeat exports of the same span are deduplicated. Reported totals describe **only the visible exported spans**.
- **UNRESOLVED**: no chat span, missing IDs, missing/invalid usage, or one provider request ID appearing on multiple distinct spans. Token totals are `null`, not guessed.
- **FAIL**: two different span payloads claim exactly the same `(traceId, spanId)`.

**Always unknown:** whether two call spans constitute a causal retry of the same logical work; whether a retry happened but was not exported; whether producer usage matches provider billing; whether the tool or external effect succeeded. Model-call retry grouping requires an explicit producer-owned logical-operation correlation, not coincidence of timing, session or names.

This addresses only the **calls and retries** portion of [AAIF Observability #44](https://github.com/aaif/wg-observability-and-traceability/issues/44). The existing #42 test kit and #57 PR cover different relationship and effect-evidence cases. Do not integrate this experimental reader into the released `SpatialRuntime/interop/conformance` Action without maintainers identifying a real consumer and agreeing on scope. Test fixtures are synthetic, not independent Goose capture; a live OTLP export and maintainer review are required before a producer interoperability claim.
