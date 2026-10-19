#!/usr/bin/env python3
"""Independent, stdlib-only, evidence-bounded AAIF #44 trace relationship reader.

Accepts original Foreman OTLP/HTTP NDJSON (source mode) or the reviewed minimal
projection JSON (offline fixture mode). It does not import any Foreman or AAIF
reconstruction code and never equates trace presence with enforcement or effects.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

DECISION = "gen_ai.tool.call.decision"
OUTCOME = "gen_ai.tool.call.decision.outcome"
CALL = "gen_ai.tool.call.id"
EXECUTION = "gen_ai.agent.execution.id"
TOOL = "gen_ai.tool.name"
APPROVAL = "foreman.approval.id"
SOURCE_BLOB_SHA = "2541dc0f58d34bc113ad2064da9510e444b24504"


def _attrs(xs: list[dict[str, Any]]) -> dict[str, Any]:
    """OTLP attribute decoder; never silently pick a duplicate key."""
    d: dict[str, Any] = {}
    for attr in xs:
        key = attr["key"]
        value = attr["value"]
        if key in d:
            raise ValueError(f"duplicate OTLP attribute {key}")
        kinds = [k for k in ("stringValue", "intValue", "boolValue", "doubleValue") if k in value]
        if len(kinds) != 1:
            raise ValueError(f"ambiguous OTLP attribute {key}")
        d[key] = value[kinds[0]]
    return d


def project_otlp(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lossy projection: only tool decisions and execute_tool spans, plus identity."""
    rows: list[dict[str, Any]] = []
    for document in documents:
        if not isinstance(document, dict):
            raise ValueError("OTLP envelope must be a JSON object")
        payload = document.get("body", document)
        if not isinstance(payload, dict) or not isinstance(payload.get("resourceSpans"), list):
            raise ValueError("OTLP envelope missing resourceSpans array")
        for rs in payload.get("resourceSpans", []):
            service = _attrs(rs.get("resource", {}).get("attributes", [])).get("service.name")
            for ss in rs.get("scopeSpans", []):
                for span in ss.get("spans", []):
                    a = _attrs(span.get("attributes", []))
                    decisions = []
                    for event in span.get("events", []):
                        if event.get("name") != DECISION:
                            continue
                        raw_attrs = _attrs(event.get("attributes", []))
                        # This is an explicitly lossy, privacy-limited projection.
                        # Preserve only fields needed for the documented relationship.
                        relevant = (EXECUTION, CALL, TOOL, OUTCOME, APPROVAL)
                        decisions.append({"t": event.get("timeUnixNano"),
                                          "name": DECISION,
                                          "attrs": {k: raw_attrs[k] for k in relevant if k in raw_attrs}})
                    if decisions or a.get("gen_ai.operation.name") == "execute_tool":
                        rows.append({"service": service, "trace": span.get("traceId"),
                                     "span": span.get("spanId"), "name": span.get("name"),
                                     "operation": a.get("gen_ai.operation.name"),
                                     "execution": a.get(EXECUTION), "call": a.get(CALL),
                                     "simulated": a.get("foreman.run.simulated"),
                                     "start_ns": span.get("startTimeUnixNano"),
                                     "events": decisions})
    return rows


def load_rows(path: Path) -> list[dict[str, Any]]:
    contents = path.read_text(encoding="utf-8")
    if path.suffix == ".ndjson":
        rows = project_otlp([json.loads(line) for line in contents.splitlines() if line.strip()])
    else:
        doc = json.loads(contents)
        if isinstance(doc, dict) and "projection" in doc:
            rows = doc["projection"]
        elif isinstance(doc, dict) and ("resourceSpans" in doc or "body" in doc):
            rows = project_otlp([doc])
        else:
            raise ValueError("input must contain projection or resourceSpans")
    if not isinstance(rows, list) or not rows:
        raise ValueError("no trace records")
    return rows


def inspect(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Three-valued observable relationship audit, never an effect/enforcement proof.

    A span may be delivered multiple times: deduplicate ONLY identical span identity
    and content. Same call on distinct span IDs is a second observed execution.
    Same event on distinct parent spans is distinct. No join by trace ID alone.
    """
    decisions: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    executed: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    invalid: list[str] = []
    known_spans: dict[tuple[str, str, str], str] = {}
    seen_events: set[tuple[str, str, str, str, str]] = set()
    all_span_count = 0

    for row in rows:
        service, trace, span = (row.get("service"), row.get("trace"), row.get("span"))
        if not all(isinstance(x, str) and x for x in (service, trace, span)):
            invalid.append("missing resource/span identity")
            continue
        signature = (service, trace, span)
        canonical = json.dumps(row, sort_keys=True, separators=(",", ":"))
        if signature in known_spans:
            if known_spans[signature] != canonical:
                invalid.append("same span identity has inconsistent records")
            continue
        known_spans[signature] = canonical
        all_span_count += 1
        identity = (row.get("execution"), row.get("call"))
        if row.get("operation") == "execute_tool":
            if not all(isinstance(x, str) and x for x in identity):
                invalid.append("execute_tool missing execution/call id")
            else:
                executed[identity].append(row)
        for event in row.get("events", []):
            if event.get("name") != DECISION:
                continue
            a = event.get("attrs", {})
            event_identity = (a.get(EXECUTION), a.get(CALL))
            if not all(isinstance(x, str) and x for x in event_identity):
                invalid.append("decision missing execution/call id")
                continue
            if event_identity[0] != row.get("execution"):
                invalid.append("decision execution id contradicts enclosing span")
                continue
            # Host span may or may not carry a call id (invoke_agent vs tool_call_decision).
            if row.get("call") and row.get("call") != event_identity[1]:
                invalid.append("decision call id contradicts enclosing span")
                continue
            outcome = a.get(OUTCOME)
            if outcome not in {"require_approval", "allow", "deny"}:
                invalid.append(f"unsupported decision outcome: {outcome!r}")
                continue
            # An equal timestamp/outcome does not make two distinct proposed
            # tool calls identical. Include all retained attributes in the key.
            event_sig = (service, trace, span, str(event.get("t")),
                         json.dumps(a, sort_keys=True, separators=(",", ":")))
            if event_sig in seen_events:
                continue
            seen_events.add(event_sig)
            decisions[event_identity].append({"outcome": outcome, "service": service,
                                              "trace": trace, "span": span,
                                              "tool": a.get(TOOL), "approval_id": a.get(APPROVAL),
                                              "t": event.get("t")})

    answers = []
    for execution, call in sorted(decisions.keys() | executed.keys()):
        key = (execution, call)
        events = decisions.get(key, [])
        spans = executed.get(key, [])
        states = [e["outcome"] for e in events]
        bad = []
        name_values = set(e["tool"] for e in events if e["tool"])
        for s in spans:
            # The tool operation is owned by worker in the inspected Foreman capture.
            if s.get("name", "").startswith("execute_tool "):
                name_values.add(s["name"].removeprefix("execute_tool "))
        if len(name_values) > 1:
            bad.append("tool name disagreement")
        # Foreman-specific mapping: the approval ID links worker pause and web
        # response. A shared tool-call ID with two different approval IDs is
        # not proof that the proposed action was authorized.
        approval_ids = {e["approval_id"] for e in events if e["approval_id"]}
        if len(approval_ids) > 1:
            bad.append("approval id disagreement")
        if any(not isinstance(e["approval_id"], str) or not e["approval_id"]
               for e in events):
            bad.append("approval id missing")
        if any(not isinstance(e["tool"], str) or not e["tool"] for e in events):
            bad.append("decision tool name missing")
        if any(s.get("name") != f"execute_tool {next(iter(name_values), None)}"
               for s in spans if name_values):
            bad.append("execute span tool name missing or inconsistent")
        if "allow" in states and "deny" in states:
            bad.append("contradictory terminal decisions")
        if "deny" in states and spans:
            bad.append("execution span despite observed deny")
        if len(spans) > 1:
            bad.append("multiple distinct execution spans for same call")
        if states.count("require_approval") > 1 or states.count("allow") > 1 or states.count("deny") > 1:
            bad.append("duplicate distinct approval decisions")
        if any(e["outcome"] == "allow" and e["service"] != "foreman-web" for e in events):
            bad.append("allow was not exported by Foreman web process")
        if any(e["outcome"] == "deny" and e["service"] != "foreman-web" for e in events):
            bad.append("deny was not exported by Foreman web process")
        # Cross-process timestamps are a *diagnostic*, not trusted causality:
        # hosts can have skewed clocks and there is no authenticated global clock.
        # Inversion therefore downgrades correlation to UNKNOWN instead of
        # presenting causal order as established or declaring a protocol breach.
        time_uncertain = False
        def nanos(value):
            try:
                if value is None or not str(value).isdigit():
                    return None
                return int(value)
            except (TypeError, ValueError):
                return None
        pending = [nanos(e["t"]) for e in events if e["outcome"] == "require_approval"]
        terminals = [nanos(e["t"]) for e in events if e["outcome"] in {"allow", "deny"}]
        starts = [nanos(s.get("start_ns")) for s in spans]
        comparable = bool(pending and terminals and
                          None not in (pending[0], terminals[0]))
        if comparable and terminals[0] < pending[0]:
            time_uncertain = True
        if "allow" in states and starts:
            comparable = comparable and starts[0] is not None
            if comparable and starts[0] < terminals[0]:
                time_uncertain = True
        clock_status = ("OBSERVED_INVERSION" if time_uncertain else
                        "OBSERVED_CONSISTENT" if comparable else "NOT_COMPARABLE")
        if bad:
            verdict = "CONTRADICTED"
        elif not time_uncertain and states.count("require_approval") == 1 and states.count("allow") == 1 and len(spans) == 1:
            verdict = "CORRELATED_ALLOW_EXECUTION"
        elif not time_uncertain and states.count("require_approval") == 1 and states.count("deny") == 1 and not spans:
            verdict = "CORRELATED_DENY_NO_OBSERVED_EXECUTION"
        else:
            verdict = "UNCONFIRMED"
        answers.append({"execution_id": execution, "tool_call_id": call,
                        "tool": next(iter(name_values), None),
                        "decisions": sorted(states, key={"require_approval": 0, "allow": 1, "deny": 1}.get),
                        "observed_execution_spans": len(spans), "observed_services": sorted({e["service"] for e in events} | {s["service"] for s in spans}),
                        "observed_trace_ids": sorted({e["trace"] for e in events} | {s["trace"] for s in spans}),
                        "verdict": verdict, "reasons": bad,
                        "clock_order_uncertain": time_uncertain,
                        "clock_order_status": clock_status,
                        "enforcement_proven": False, "physical_effect": "UNKNOWN"})
    return {"schema": "counterproof.aaif-approval-observer.v0.1",
            "evidence_boundary": "Correlates exported simulated Foreman spans and decisions only; cannot prove gate enforcement, real tool side effects, provider behavior or independent producers.",
            "parsed_unique_spans_in_projection": all_span_count,
            "invalid_inputs": invalid, "results": answers}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Foreman raw OTLP/HTTP .ndjson or checked projection .json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-foreman-blob", action="store_true",
                        help="require the exact pinned upstream raw NDJSON Git blob SHA")
    opts = parser.parse_args(argv)
    try:
        if opts.verify_foreman_blob:
            if opts.input.suffix != ".ndjson":
                raise ValueError("source SHA check requires raw NDJSON, not a projection")
            content = opts.input.read_bytes()
            digest = hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest()
            if digest != SOURCE_BLOB_SHA:
                raise ValueError(f"Foreman source blob changed: {digest}")
        result = inspect(load_rows(opts.input))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if opts.output:
        opts.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 1 if result["invalid_inputs"] or any(r["verdict"] in {"CONTRADICTED", "UNCONFIRMED"}
                                          and r["decisions"] for r in result["results"]) else 0

if __name__ == "__main__":
    raise SystemExit(main())