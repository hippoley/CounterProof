"""Synthetic OTel #695 attribution oracle (not instrumentation or normative metric naming)."""
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Invocation:
    invocation_id: str
    parent_id: str | None
    input_tokens: int
    output_tokens: int
    remote_child_unreported: bool = False

    def __post_init__(self):
        if min(self.input_tokens, self.output_tokens) < 0:
            raise ValueError("token counts must be nonnegative")


def attributed(invocations: Iterable[Invocation]):
    nodes = list(invocations)
    by_id = {n.invocation_id: n for n in nodes}
    if len(by_id) != len(nodes):
        raise ValueError("duplicate invocation id")
    children = {n.invocation_id: [] for n in nodes}
    for n in nodes:
        if n.parent_id is not None:
            if n.parent_id not in by_id:
                raise ValueError("unknown parent")
            children[n.parent_id].append(n.invocation_id)
    visiting, finished = set(), {}

    def visit(node_id):
        if node_id in visiting:
            raise ValueError("cycle in invocation graph")
        if node_id in finished:
            return finished[node_id]
        visiting.add(node_id)
        n = by_id[node_id]
        total_in, total_out = n.input_tokens, n.output_tokens
        complete = not n.remote_child_unreported
        for child_id in children[node_id]:
            (c_in, c_out), c_complete = visit(child_id)
            total_in += c_in
            total_out += c_out
            complete = complete and c_complete
        visiting.remove(node_id)
        finished[node_id] = ((total_in, total_out), complete)
        return finished[node_id]

    for node_id in by_id:
        visit(node_id)
    return {
        n.invocation_id: {
            "direct": (n.input_tokens, n.output_tokens),
            "known_total": finished[n.invocation_id][0],
            "total_complete": finished[n.invocation_id][1],
            "root": n.parent_id is None,
        }
        for n in nodes
    }


def direct_sum(rows):
    return tuple(sum(r["direct"][i] for r in rows.values()) for i in (0, 1))


def root_total_sum(rows):
    roots = [r for r in rows.values() if r["root"]]
    if not all(r["total_complete"] for r in roots):
        raise ValueError("root total incomplete (unreported remote usage)")
    return tuple(sum(r["known_total"][i] for r in roots) for i in (0, 1))
