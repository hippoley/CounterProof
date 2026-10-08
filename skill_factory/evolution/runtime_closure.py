"""Runtime closure evidence evaluation."""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "counterproof.runtime-closure/v0.1"


def evaluate_runtime_closure(trace: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(trace, dict):
        raise TypeError("trace must be an object")

    sinks = trace.get("sinks")
    events = trace.get("events")
    if not isinstance(sinks, list) or not sinks:
        raise ValueError("sinks must be a non-empty list")
    if not isinstance(events, list):
        raise TypeError("events must be a list")

    declared = set(sinks)
    recorded = False
    effective: set[str] = set()
    closed: set[str] = set()
    unavailable: set[str] = set()
    violations: set[str] = set()

    for event in sorted(events, key=lambda item: item.get("seq", 0)):
        if not isinstance(event, dict):
            raise TypeError("event must be an object")

        kind = event.get("type")
        sink = event.get("sink")

        if sink is not None and sink not in declared:
            raise ValueError(f"undeclared sink: {sink}")

        if kind == "authority_change_recorded":
            recorded = True
        elif kind == "authority_change_effective":
            if not sink:
                raise ValueError("authority_change_effective requires sink")
            effective.add(sink)
        elif kind == "sink_closed":
            if not sink:
                raise ValueError("sink_closed requires sink")
            closed.add(sink)
        elif kind == "evidence_unavailable":
            if not sink:
                raise ValueError("evidence_unavailable requires sink")
            unavailable.add(sink)
        elif kind == "effect_committed":
            if not sink:
                raise ValueError("effect_committed requires sink")
            if sink in effective:
                violations.add(sink)

    if violations:
        verdict = "VIOLATION"
    elif closed == declared:
        verdict = "CLOSED"
    elif closed:
        verdict = "PARTIAL"
    else:
        verdict = "UNKNOWN"

    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": verdict,
        "facts": {
            "authority_change_recorded": recorded,
            "effective_sinks": sorted(effective),
            "closed_sinks": sorted(closed),
            "evidence_unavailable_sinks": sorted(unavailable),
            "violating_sinks": sorted(violations),
        },
        "non_claims": [
            "Missing sink evidence is not upgraded into closure.",
            "Recorded authority change is not treated as sink-effective change.",
        ],
    }
