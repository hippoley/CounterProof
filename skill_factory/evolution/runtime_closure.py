"""Runtime closure evidence evaluation."""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "counterproof.runtime-closure/v0.1"

SUPPORTED_EVENTS = {
    "authority_change_recorded",
    "authority_change_effective",
    "sink_closed",
    "evidence_unavailable",
    "effect_committed",
}


def evaluate_runtime_closure(trace: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(trace, dict):
        raise TypeError("trace must be an object")

    sinks = trace.get("sinks")
    events = trace.get("events")

    if not isinstance(sinks, list) or not sinks:
        raise ValueError("sinks must be a non-empty list")
    if any(not isinstance(sink, str) or not sink for sink in sinks):
        raise ValueError("every sink must be a non-empty string")
    if len(set(sinks)) != len(sinks):
        raise ValueError("sinks must be unique")
    if not isinstance(events, list) or not events:
        raise ValueError("events must be a non-empty list")

    declared = set(sinks)
    seen_seq: set[int] = set()
    ordered_events: list[dict[str, Any]] = []

    for event in events:
        if not isinstance(event, dict):
            raise TypeError("event must be an object")

        seq = event.get("seq")
        kind = event.get("type")
        sink = event.get("sink")

        if not isinstance(seq, int):
            raise TypeError("event seq must be an integer")
        if seq in seen_seq:
            raise ValueError(f"duplicate event seq: {seq}")
        seen_seq.add(seq)

        if kind not in SUPPORTED_EVENTS:
            raise ValueError(f"unsupported runtime closure event type: {kind}")

        if sink is not None and sink not in declared:
            raise ValueError(f"undeclared sink: {sink}")

        ordered_events.append(event)

    ordered_events.sort(key=lambda item: item["seq"])

    recorded_seq: int | None = None
    effective_at: dict[str, int] = {}
    closed_at: dict[str, int] = {}
    unavailable: set[str] = set()
    violations: set[str] = set()

    for event in ordered_events:
        seq = event["seq"]
        kind = event["type"]
        sink = event.get("sink")

        if kind == "authority_change_recorded":
            if recorded_seq is None:
                recorded_seq = seq
            continue

        if kind == "authority_change_effective":
            if not sink:
                raise ValueError("authority_change_effective requires sink")
            if recorded_seq is None or seq <= recorded_seq:
                raise ValueError(
                    "authority_change_effective must follow authority_change_recorded"
                )
            effective_at[sink] = seq
            continue

        if kind == "sink_closed":
            if not sink:
                raise ValueError("sink_closed requires sink")
            effective_seq = effective_at.get(sink)
            if effective_seq is None or seq <= effective_seq:
                raise ValueError(
                    f"sink_closed must follow authority_change_effective for {sink}"
                )
            closed_at[sink] = seq
            continue

        if kind == "evidence_unavailable":
            if not sink:
                raise ValueError("evidence_unavailable requires sink")
            unavailable.add(sink)
            continue

        if kind == "effect_committed":
            if not sink:
                raise ValueError("effect_committed requires sink")
            effective_seq = effective_at.get(sink)
            if effective_seq is not None and seq > effective_seq:
                violations.add(sink)

    closed = set(closed_at)

    if violations:
        verdict = "VIOLATION"
    elif recorded_seq is not None and closed == declared:
        verdict = "CLOSED"
    elif recorded_seq is not None and closed:
        verdict = "PARTIAL"
    else:
        verdict = "UNKNOWN"

    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": verdict,
        "facts": {
            "authority_change_recorded": recorded_seq is not None,
            "effective_sinks": sorted(effective_at),
            "closed_sinks": sorted(closed),
            "evidence_unavailable_sinks": sorted(unavailable),
            "violating_sinks": sorted(violations),
        },
        "non_claims": [
            "Missing sink evidence is not upgraded into closure.",
            "Recorded authority change is not treated as sink-effective change.",
            "Unknown event types are rejected rather than ignored.",
        ],
    }
