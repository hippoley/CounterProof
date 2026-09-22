"""Machine-readable truth table for EvoPR capabilities."""
from __future__ import annotations


CAPABILITIES: tuple[dict[str, str], ...] = (
    {
        "id": "packet-model",
        "name": "Evolution Packet data model",
        "status": "tested",
        "evidence": "Unit tests construct evidence, hypotheses, mutations, replay results, and packets.",
        "limitation": "Decision Capsule and Outcome Receipt are currently free-form strings.",
    },
    {
        "id": "promotion-gate",
        "name": "Promotion gate from replay evidence",
        "status": "tested",
        "evidence": "Unit tests verify positive delta + zero regressions + zero risk flags.",
        "limitation": "The default gate is intentionally simple and does not weight evidence confidence.",
    },
    {
        "id": "behavior-pr",
        "name": "Behavior PR Markdown renderer",
        "status": "tested",
        "evidence": "CLI smoke test renders examples/evolution_pr.json into reviewable Markdown.",
        "limitation": "It renders a review artifact; it does not yet open a GitHub pull request automatically.",
    },
    {
        "id": "packaged-install",
        "name": "Clean wheel install and packaged playground",
        "status": "tested",
        "evidence": "CI builds a wheel, installs it in a fresh virtualenv, runs the CLI, and serves the packaged frontend.",
        "limitation": "This proves packaging and startup, not compatibility with every third-party agent stack.",
    },
    {
        "id": "command-replay",
        "name": "Deterministic baseline/candidate command replay",
        "status": "tested",
        "evidence": "CI executes real subprocess pairs from examples/replay_suite.json and checks outcomes.",
        "limitation": "It is command-based replay, not yet a captured world-state/time-travel runtime.",
    },
    {
        "id": "mutation-surfaces",
        "name": "Multiple mutation surfaces",
        "status": "partial",
        "evidence": "The data model accepts skill, prompt, policy, router, memory, tool, and eval surfaces.",
        "limitation": "EvoPR does not yet apply each mutation surface to a live agent automatically.",
    },
    {
        "id": "evidence-semantics",
        "name": "Evidence types and confidence",
        "status": "partial",
        "evidence": "Evidence kind/verdict/confidence are represented and confidence bounds are validated.",
        "limitation": "Different evidence kinds are not yet assigned calibrated weights in causal selection.",
    },
    {
        "id": "rollback-contract",
        "name": "Rollback reference and activation scope",
        "status": "partial",
        "evidence": "Mutation objects store and render rollback_ref and activation_scope.",
        "limitation": "No runtime rollback executor or activation enforcer exists yet.",
    },
    {
        "id": "playground",
        "name": "Interactive causal playground",
        "status": "demo",
        "evidence": "site/ supports hypothesis selection, branch visualization, replay display, promote/rollback state.",
        "limitation": "Browser replay values are demo fixtures; Promote/Rollback only change local UI state.",
    },
    {
        "id": "trace-ingestion",
        "name": "Automatic PR / review / CI / agent-trace ingestion",
        "status": "planned",
        "evidence": "Roadmap only.",
        "limitation": "Users must currently prepare an Evolution Packet or replay manifest explicitly.",
    },
    {
        "id": "causal-selector",
        "name": "Automatic causal hypothesis generation and falsification",
        "status": "planned",
        "evidence": "Roadmap only.",
        "limitation": "Current hypotheses are supplied by the user/example data.",
    },
    {
        "id": "world-fork",
        "name": "Captured counterfactual world forks",
        "status": "planned",
        "evidence": "Roadmap only.",
        "limitation": "Command replay can compare executions, but does not snapshot and restore arbitrary worlds.",
    },
    {
        "id": "github-change-control",
        "name": "Automatic Evolution PR open / merge / revert",
        "status": "planned",
        "evidence": "Roadmap only.",
        "limitation": "No GitHub automation is wired into the EvoPR runtime yet.",
    },
    {
        "id": "online-rollout",
        "name": "Shadow / canary / automatic rollback",
        "status": "planned",
        "evidence": "Roadmap only.",
        "limitation": "No online traffic router is implemented.",
    },
)


def capability_report() -> dict[str, object]:
    counts: dict[str, int] = {}
    for item in CAPABILITIES:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {
        "schema_version": 1,
        "capabilities": [dict(item) for item in CAPABILITIES],
        "summary": counts,
    }
