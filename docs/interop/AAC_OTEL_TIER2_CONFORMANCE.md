# AAC OpenTelemetry tier-2 independent consumer experiment

Status: experimental.

Target: `draft-palanisamy-scitt-aac-otel-00`, published 2026-10-02.

The draft currently lists one known implementation for this extension:
`action-state-group/capsule-emit`. It also says the registry structure for
tier-2 conformance artifacts is not yet specified, while publishing the
positive and must-fail vectors needed for such a profile.

CounterProof therefore implements a separate consumer from the draft text
instead of importing `capsule-emit`.

## What is checked

- both currently permitted JSON placements are recognized;
- trace/span identifiers are lower-case hex with exact lengths;
- clear `tracestate` is refused for extension-level trust;
- semconv values are default-deny and the draft's content-bearing values are
  never admitted;
- `semconv.source` must pin the GenAI semantic-conventions source;
- clear resource attributes are restricted to the draft's closed subset;
- invalid extension data becomes `INFORMATIONAL_ONLY`, and never changes the
  surrounding Agent Action Capsule base verdict;
- correlated same-producer telemetry is never counted as independent
  corroboration.

## Why this is a higher-value interop node

This extension joins two still-moving ecosystems: SCITT Agent Action Capsules
and OpenTelemetry GenAI semantic conventions. A second independently written
consumer can expose ambiguous wording or accidental producer assumptions while
the tier-2 conformance registry is still explicitly TBD.

## Independent-consumer finding

The draft's Section 9 says its positive vector must be accepted and must reproduce the same `capsule_id` under JCS binding. The published vector currently contains only the extension block, without a complete base Capsule or an expected `capsule_id`.

That means this experiment can independently test the extension's admission semantics, but it cannot claim that the published vector alone makes the `capsule_id` reproducibility requirement executable. A complete frozen Capsule + expected identifier, or an explicit statement that binding is exercised only by tier-1 CPB vectors, would close that gap.

An attempt to file this narrowly against the reference implementation repository was blocked by the current GitHub integration permission (HTTP 403). This is therefore **handoff-ready but not externally delivered** and must not be counted as author feedback.

## Non-claims

This is not an IETF Working Group adoption claim, not OpenTelemetry
registration of `aac.capsule_id`, and not evidence that Action State Group
depends on CounterProof.

Promotion requires an external author/maintainer to review, consume, cite, or
request the conformance result.
