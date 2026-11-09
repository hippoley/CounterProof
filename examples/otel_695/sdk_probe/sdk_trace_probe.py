"""Conservative attribution over actual OTel SDK ReadableSpan objects.

This is a consumer experiment, not official instrumentation or a metric schema.
Observed inference consumption is never presented as a global request total.
"""
AGENT_OPS = frozenset(("invoke_agent", "invoke_workflow"))
INFERENCE_OPS = frozenset(("chat", "generate_content", "text_completion", "realtime_inference"))


def _count(attrs, key):
    value = attrs.get(key)
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(f"invalid {key}: expected nonnegative integer")
    return value


def summarize_observed_spans(spans):
    """Nearest-ancestor agent attribution within a single observed trace.

    Agent-level usage may be inclusive and is intentionally not added to
    inference-span usage. Missing spans and remote agents cannot be detected
    exhaustively; completeness must not be inferred from these rows.
    """
    spans = list(spans)
    index = {}
    for span in spans:
        ctx = span.get_span_context()
        key = (ctx.trace_id, ctx.span_id)
        if key in index:
            raise ValueError("duplicate span identity")
        index[key] = span

    agents = {}
    unattributed = [0, 0]
    unknown = 0
    for key, span in index.items():
        attrs = span.attributes or {}
        if attrs.get("gen_ai.operation.name") in AGENT_OPS:
            agents[key] = {
                "name": attrs.get("gen_ai.agent.name", span.name),
                "observed_direct": [0, 0],
                "inference_count": 0,
                "usage_unknown_count": 0,
            }

    for key, span in index.items():
        attrs = span.attributes or {}
        if attrs.get("gen_ai.operation.name") not in INFERENCE_OPS:
            continue
        counts = [_count(attrs, f"gen_ai.usage.{direction}_tokens")
                  for direction in ("input", "output")]
        owner = None
        parent = span.parent
        visited = {key}
        while parent is not None and parent.is_valid:
            ancestor_key = (parent.trace_id, parent.span_id)
            if ancestor_key in visited:
                raise ValueError("cycle in span parent graph")
            visited.add(ancestor_key)
            ancestor = index.get(ancestor_key)
            if ancestor is None:
                break
            if ancestor_key in agents:
                owner = ancestor_key
                break
            parent = ancestor.parent
        target = unattributed if owner is None else agents[owner]["observed_direct"]
        if owner is not None:
            agents[owner]["inference_count"] += 1
        for i, count in enumerate(counts):
            if count is not None:
                target[i] += count
        if None in counts:
            unknown += 1
            if owner is not None:
                agents[owner]["usage_unknown_count"] += 1

    return {
        "agents": list(agents.values()),
        "unattributed_observed": unattributed,
        "inference_usage_unknown_count": unknown,
        "global_complete": False,
        "scope": "observed_sdk_spans_only",
    }
