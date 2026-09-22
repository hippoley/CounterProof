"""Compile generic agent traces into reviewable EvoPR packets.

This module intentionally uses deterministic heuristics. It can extract evidence and
propose hypotheses, but it does not claim unique causal attribution.
"""
from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from .models import CandidateMutation, Evidence, EvolutionPacket, Hypothesis, ProbeSpec

NEGATIVE_TYPES = {
    "human_correction",
    "verifier_failure",
    "test_failure",
    "tool_error",
    "undo",
    "retry",
    "compensating_action",
    "failure",
}
POSITIVE_TYPES = {
    "verifier_pass",
    "test_pass",
    "success",
    "reuse",
}
SURFACES = ("skill", "prompt", "policy", "router", "memory", "tool", "eval")


def load_trace(path: Path) -> dict[str, Any]:
    """Load either a JSON trace object or JSONL event stream."""
    path = path.resolve()
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("trace file is empty")

    if path.suffix.lower() == ".jsonl":
        events = [json.loads(line) for line in text.splitlines() if line.strip()]
        if not events:
            raise ValueError("trace JSONL contains no events")
        header = events[0] if events[0].get("type") == "trace_meta" else {}
        if header:
            events = events[1:]
        return {
            "trace_id": header.get("trace_id", path.stem),
            "agent": header.get("agent", "unknown-agent"),
            "task": header.get("task", ""),
            "events": events,
        }

    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise TypeError("trace JSON must be an object")
    if not isinstance(raw.get("events"), list) or not raw["events"]:
        raise ValueError("trace requires a non-empty events list")
    return raw


def _event_source(event: dict[str, Any], index: int) -> str:
    return str(event.get("id") or event.get("source") or f"event-{index:03d}")


def _negative_index(events: list[dict[str, Any]]) -> int:
    for index, event in enumerate(events):
        if event.get("type") in NEGATIVE_TYPES:
            return index
        if event.get("verdict") == "negative":
            return index
    return len(events) - 1


def _decision_index(events: list[dict[str, Any]], failure_index: int) -> int:
    decision_indices = [
        index
        for index, event in enumerate(events[: failure_index + 1])
        if event.get("type") == "decision"
    ]
    if not decision_indices:
        raise ValueError("trace requires at least one decision event before the failure")
    return decision_indices[-1]


def _format_value(value: Any) -> str:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _decision_capsule(decision: dict[str, Any]) -> str:
    keys = (
        "goal",
        "world_state",
        "candidates",
        "selected_action",
        "assumptions",
        "uncertainty",
        "guards",
        "route",
        "memory",
    )
    lines = []
    for key in keys:
        if key in decision:
            lines.append(f"- **{key.replace('_', ' ')}:** {_format_value(decision[key])}")
    if not lines:
        lines.append("- **decision:** " + _format_value(decision))
    return "\n".join(lines)


def _event_note(event: dict[str, Any]) -> str:
    for key in ("note", "text", "message", "summary", "error"):
        if event.get(key):
            return str(event[key])
    return _format_value({k: v for k, v in event.items() if k not in {"type", "id", "ts"}})


def _evidence_from_events(
    events: list[dict[str, Any]],
    decision_index: int,
) -> tuple[Evidence, ...]:
    evidence: list[Evidence] = []
    for index, event in enumerate(events[decision_index + 1 :], start=decision_index + 1):
        kind = str(event.get("type", "event"))
        if kind not in NEGATIVE_TYPES | POSITIVE_TYPES and "verdict" not in event:
            continue

        verdict = event.get("verdict")
        if verdict not in {"positive", "negative", "ambiguous"}:
            verdict = "negative" if kind in NEGATIVE_TYPES else "positive"

        default_confidence = 1.0 if kind in {
            "verifier_failure",
            "verifier_pass",
            "test_failure",
            "test_pass",
        } else 0.9
        confidence = float(event.get("confidence", default_confidence))
        evidence.append(
            Evidence(
                source=_event_source(event, index),
                kind=kind,
                verdict=verdict,
                confidence=confidence,
                note=_event_note(event),
            )
        )
    return tuple(evidence)


def _outcome_receipt(
    events: list[dict[str, Any]],
    decision_index: int,
) -> str:
    lines = []
    for index, event in enumerate(events[decision_index + 1 :], start=decision_index + 1):
        kind = str(event.get("type", "event"))
        if kind in NEGATIVE_TYPES | POSITIVE_TYPES or kind in {"tool_call", "tool_result"}:
            lines.append(
                f"- {_event_source(event, index)} **{kind}** — {_event_note(event)}"
            )
    return "\n".join(lines) if lines else "- No post-decision outcome events were captured."


def _failure_summary(trace: dict[str, Any], events: list[dict[str, Any]], failure_index: int) -> str:
    failure = trace.get("failure")
    if isinstance(failure, dict) and failure.get("summary"):
        return str(failure["summary"])
    if isinstance(failure, str) and failure:
        return failure
    event = events[failure_index]
    note = _event_note(event)
    return note if note else f"Observed {event.get('type', 'failure')} after the selected decision."


def _surface_scores(
    decision: dict[str, Any],
    events: list[dict[str, Any]],
    evidence: tuple[Evidence, ...],
) -> dict[str, tuple[float, list[str], str]]:
    scores: dict[str, tuple[float, list[str], str]] = {
        surface: (0.0, [], "") for surface in SURFACES
    }

    def bump(surface: str, score: float, source: str, mechanism: str) -> None:
        current_score, sources, current_mechanism = scores[surface]
        if score > current_score:
            current_mechanism = mechanism
        scores[surface] = (
            min(0.99, current_score + score),
            [*sources, source] if source not in sources else sources,
            current_mechanism,
        )

    selected = str(decision.get("selected_action", "")).lower()
    world_text = _format_value(decision.get("world_state", "")).lower()
    guards_text = _format_value(decision.get("guards", "")).lower()
    route_text = _format_value(decision.get("route", "")).lower()
    memory_text = _format_value(decision.get("memory", "")).lower()
    trace_text = " ".join(_event_note(event).lower() for event in events)

    for index, event in enumerate(events):
        hint = event.get("surface_hint")
        if hint in SURFACES:
            bump(
                str(hint),
                0.8,
                _event_source(event, index),
                f"Explicit trace evidence points to the {hint} surface.",
            )

    if (
        any(token in world_text + guards_text for token in ("provisional", "unvalidated", "false"))
        and any(
            token in selected
            for token in ("execute", "query", "call", "write", "send", "open")
        )
    ):
        bump(
            "policy",
            0.72,
            "decision",
            "Execution proceeded while a precondition or semantic state was still provisional.",
        )

    if any(token in trace_text for token in ("wrong route", "router", "workflow mismatch", "misroute")):
        bump(
            "router",
            0.7,
            "trace",
            "The trace indicates the wrong route or workflow was selected.",
        )

    if any(token in memory_text + trace_text for token in ("stale", "previous target", "old target", "sticky")):
        bump(
            "memory",
            0.68,
            "trace",
            "Stale or sticky context appears to have survived into the decision.",
        )

    if any(token in trace_text for token in ("schema", "tool contract", "api mismatch", "tool error")):
        bump(
            "tool",
            0.72,
            "trace",
            "Tool execution or its contract appears inconsistent with the intended behavior.",
        )

    if any(token in trace_text for token in ("missing test", "eval gap", "coverage gap")):
        bump(
            "eval",
            0.65,
            "trace",
            "The failure escaped because the evaluation surface did not cover the behavior.",
        )

    if any(item.kind == "human_correction" for item in evidence):
        bump(
            "skill",
            0.42,
            "human_correction",
            "A human correction suggests the learned instruction or interpretation may be incomplete.",
        )

    if route_text:
        bump(
            "router",
            0.2,
            "decision",
            "A routing decision was present at the failure point and remains a candidate mechanism.",
        )

    bump(
        "prompt",
        0.16,
        "fallback",
        "The governing instruction may be underspecified; this remains a weak fallback hypothesis.",
    )
    return scores



def _probe_spec(
    probe_id: str,
    hypothesis_id: str,
    surface: str,
    mechanism: str,
) -> ProbeSpec:
    contracts = {
        "policy": (
            "Change only the execution precondition / commit gate.",
            "The original failure disappears while normal cases keep passing.",
            "The failure still occurs with the guard changed, or unrelated cases regress.",
            "Replay at least one normal fast-path case to detect over-blocking.",
        ),
        "skill": (
            "Change only the learned instruction or example set.",
            "Interpretation improves before execution without changing deterministic policy.",
            "The same wrong action survives despite the instruction change.",
            "Replay paraphrases and unaffected intents to detect overfitting.",
        ),
        "prompt": (
            "Change only the governing prompt instruction.",
            "The decision changes in the failing case without tool or policy changes.",
            "The failure survives or unrelated tasks become less reliable.",
            "Replay unrelated tasks that share the same system prompt.",
        ),
        "router": (
            "Change only the route / workflow selection.",
            "The case reaches the workflow containing the needed guard and passes.",
            "The same failure occurs after rerouting, showing the route was not causal.",
            "Replay cases that should remain on the original route.",
        ),
        "memory": (
            "Change only context retention / invalidation behavior.",
            "Removing stale context changes the failing decision while preserving fresh context.",
            "The failure survives with memory cleared or normal multi-turn behavior degrades.",
            "Replay both stale-context and legitimate carry-over cases.",
        ),
        "tool": (
            "Change only the tool contract, wrapper, or validation layer.",
            "The external call becomes valid without changing upstream intent selection.",
            "The failure survives before the tool boundary or another valid tool call breaks.",
            "Replay valid tool calls and malformed inputs.",
        ),
        "eval": (
            "Add only an executable regression check for the observed failure.",
            "The pre-fix behavior fails and the corrected behavior passes deterministically.",
            "The new check cannot distinguish baseline from candidate.",
            "Run the new case with nearby negative and positive controls.",
        ),
    }
    intervention, expected, falsifier, holdout = contracts[surface]
    return ProbeSpec(
        id=probe_id,
        hypothesis_id=hypothesis_id,
        intervention=intervention,
        expected_if_true=expected,
        falsifier=f"{falsifier} Hypothesis: {mechanism}",
        holdout=holdout,
    )


def _candidate_diff(surface: str, decision: dict[str, Any], mechanism: str) -> str:
    selected = _format_value(decision.get("selected_action", "unknown"))
    before = f"BEFORE\nselected_action = {selected}"
    after_map = {
        "policy": "require the missing precondition before the selected action can commit",
        "skill": "apply a targeted learned instruction before choosing the action",
        "prompt": "make the governing instruction explicit before action selection",
        "router": "route the case through the workflow that owns the missing guard",
        "memory": "invalidate stale context before the next decision is formed",
        "tool": "enforce the tool contract before the call reaches the external system",
        "eval": "turn the observed failure into an executable regression check",
    }
    after = after_map[surface]
    return f"{before}\n\nAFTER\n{after}\n\nHYPOTHESIS\n{mechanism}"


def compile_trace(trace: dict[str, Any]) -> EvolutionPacket:
    """Compile a generic trace into a packet with heuristic candidate hypotheses."""
    events = trace["events"]
    failure_index = _negative_index(events)
    decision_index = _decision_index(events, failure_index)
    decision = events[decision_index]
    evidence = _evidence_from_events(events, decision_index)
    scores = _surface_scores(decision, events, evidence)

    ranked = [
        (surface, score, sources, mechanism)
        for surface, (score, sources, mechanism) in scores.items()
        if score > 0
    ]
    ranked.sort(key=lambda item: item[1], reverse=True)
    ranked = ranked[:4]

    hypotheses: list[Hypothesis] = []
    probes: list[ProbeSpec] = []
    candidates: list[CandidateMutation] = []
    for index, (surface, score, sources, mechanism) in enumerate(ranked, start=1):
        hypothesis_id = f"H{index}"
        candidate_id = f"C{index}"
        uncertainty = max(0.01, min(0.99, 1.0 - score))
        hypotheses.append(
            Hypothesis(
                id=hypothesis_id,
                mechanism=mechanism,
                target_surface=surface,
                evidence_for=tuple(sources),
                uncertainty=uncertainty,
            )
        )
        probes.append(
            _probe_spec(
                probe_id=f"P{index}",
                hypothesis_id=hypothesis_id,
                surface=surface,
                mechanism=mechanism,
            )
        )
        candidates.append(
            CandidateMutation(
                id=candidate_id,
                surface=surface,
                title=f"Probe {surface}: {mechanism}",
                hypothesis_id=hypothesis_id,
                behavior_diff=_candidate_diff(surface, decision, mechanism),
                rollback_ref=f"{surface}:previous",
                activation_scope=str(trace.get("activation_scope", "case-family")),
            )
        )

    trace_id = str(trace.get("trace_id", "trace"))
    task = str(trace.get("task", ""))
    return EvolutionPacket(
        packet_id=f"evo-{trace_id}",
        agent=str(trace.get("agent", "unknown-agent")),
        failure_summary=_failure_summary(trace, events, failure_index),
        decision_capsule=_decision_capsule(decision),
        outcome_receipt=_outcome_receipt(events, decision_index),
        evidence=evidence,
        hypotheses=tuple(hypotheses),
        probes=tuple(probes),
        candidates=tuple(candidates),
        metadata={
            "source_trace_id": trace_id,
            "source_task": task,
            "compiler": "trace-heuristic-v0.1",
            "attribution": (
                "heuristic hypotheses only; replay can test a mutation but does not prove unique causality"
            ),
        },
    )


def select_candidate(
    packet: EvolutionPacket,
    *,
    surface: str | None = None,
) -> EvolutionPacket:
    """Select a candidate explicitly by surface, or use the compiler's top-ranked hypothesis."""
    candidates = packet.candidates
    if surface is not None:
        candidates = tuple(candidate for candidate in candidates if candidate.surface == surface)
        if not candidates:
            available = ", ".join(candidate.surface for candidate in packet.candidates)
            raise ValueError(f"no candidate for surface {surface!r}; available: {available}")

    if not candidates:
        raise ValueError("compiled trace produced no candidate hypotheses")
    return replace(packet, selected_candidate_id=candidates[0].id)


def packet_to_dict(packet: EvolutionPacket) -> dict[str, Any]:
    """Serialize an EvolutionPacket into the JSON shape accepted by evopr build."""
    return asdict(packet)
