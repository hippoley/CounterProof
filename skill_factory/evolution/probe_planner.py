"""Plan the next discriminating probe when EvoPR remains ambiguous."""
from __future__ import annotations

from dataclasses import dataclass

from .discriminate import DiscriminationRun
from .models import EvolutionPacket

SURFACE_PROFILES: dict[str, dict[str, str]] = {
    "policy": {
        "lever": "execution precondition / commit gate",
        "hold": "language, route, memory and tool behavior",
        "positive": "changing the guard should change whether the action can commit",
        "negative": "wording-only changes should not be required for the fix",
    },
    "skill": {
        "lever": "learned instruction / demonstrations",
        "hold": "deterministic policy guard, route and tool contract",
        "positive": "paraphrase and interpretation changes should alter the decision before execution",
        "negative": "a hard policy toggle alone should not be necessary",
    },
    "prompt": {
        "lever": "governing prompt wording",
        "hold": "runtime policy, memory and tool implementation",
        "positive": "instruction wording changes should alter the decision across semantically equivalent cases",
        "negative": "the effect should disappear when the prompt change is removed",
    },
    "router": {
        "lever": "route / workflow selection",
        "hold": "the downstream workflow implementations themselves",
        "positive": "sending the same state through a different route should change the outcome",
        "negative": "changing downstream policy while holding route fixed should be unnecessary",
    },
    "memory": {
        "lever": "retained / invalidated conversational state",
        "hold": "current utterance, policy and route",
        "positive": "clearing stale context should change the decision while legitimate carry-over still works",
        "negative": "the failure should survive when memory is already clean",
    },
    "tool": {
        "lever": "tool schema / wrapper / validation boundary",
        "hold": "upstream intent, policy and route",
        "positive": "the same selected action should succeed only when the tool boundary changes",
        "negative": "the failure should remain upstream if the tool was never reached",
    },
    "eval": {
        "lever": "executable evaluator / regression condition",
        "hold": "agent runtime behavior",
        "positive": "the new evaluator should separate known-bad baseline from known-good candidate",
        "negative": "an evaluator that marks both the same is not diagnostic",
    },
}


@dataclass(frozen=True)
class ProbeSuggestion:
    left_surface: str
    right_surface: str
    title: str
    keep_fixed: str
    vary: str
    left_prediction: str
    right_prediction: str
    falsification_rule: str
    priority: int = 100

    def to_dict(self) -> dict[str, str | int]:
        return {
            "left_surface": self.left_surface,
            "right_surface": self.right_surface,
            "title": self.title,
            "keep_fixed": self.keep_fixed,
            "vary": self.vary,
            "left_prediction": self.left_prediction,
            "right_prediction": self.right_prediction,
            "falsification_rule": self.falsification_rule,
            "priority": self.priority,
        }


def _hypothesis_for(packet: EvolutionPacket, surface: str) -> str:
    for hypothesis in packet.hypotheses:
        if hypothesis.target_surface == surface:
            return hypothesis.mechanism
    return f"{surface} hypothesis"


def plan_next_probes(
    packet: EvolutionPacket,
    run: DiscriminationRun,
) -> tuple[ProbeSuggestion, ...]:
    """Plan pairwise probes only for survivor pairs that remain behaviorally identical."""
    suggestions: list[ProbeSuggestion] = []
    for rank, (left, right) in enumerate(run.unresolved_pairs, start=1):
        left_profile = SURFACE_PROFILES[left]
        right_profile = SURFACE_PROFILES[right]
        left_mechanism = _hypothesis_for(packet, left)
        right_mechanism = _hypothesis_for(packet, right)

        suggestions.append(
            ProbeSuggestion(
                left_surface=left,
                right_surface=right,
                title=f"Separate {left} from {right}",
                keep_fixed=(
                    f"Hold the recorded failure context constant. Keep {left_profile['hold']} "
                    f"and {right_profile['hold']} unchanged except for the named probe axis."
                ),
                vary=(
                    f"Create paired cases that independently toggle {left_profile['lever']} "
                    f"and {right_profile['lever']}. Do not change both in the same case."
                ),
                left_prediction=(
                    f"If {left} is the active mechanism ({left_mechanism}), "
                    f"{left_profile['positive']}; {left_profile['negative']}."
                ),
                right_prediction=(
                    f"If {right} is the active mechanism ({right_mechanism}), "
                    f"{right_profile['positive']}; {right_profile['negative']}."
                ),
                falsification_rule=(
                    "Prefer the case where the two predictions diverge. Falsify a hypothesis "
                    "when its isolated lever changes but the predicted behavior does not, or "
                    "when the rival lever alone explains the fix without regression."
                ),
                priority=100 - rank,
            )
        )

    return tuple(suggestions)


def render_probe_plan(
    suggestions: tuple[ProbeSuggestion, ...],
) -> str:
    lines = ["# EvoPR Next Probe Plan", ""]
    if not suggestions:
        lines.extend(
            [
                "No unresolved survivor pair requires another pairwise probe.",
                "",
            ]
        )
        return "\n".join(lines)

    for index, suggestion in enumerate(suggestions, start=1):
        lines.extend(
            [
                f"## {index}. {suggestion.title}",
                "",
                f"**Keep fixed:** {suggestion.keep_fixed}",
                "",
                f"**Vary:** {suggestion.vary}",
                "",
                f"**{suggestion.left_surface} predicts:** {suggestion.left_prediction}",
                "",
                f"**{suggestion.right_surface} predicts:** {suggestion.right_prediction}",
                "",
                f"**Falsification rule:** {suggestion.falsification_rule}",
                "",
            ]
        )
    lines.extend(
        [
            (
                "> This is an experiment-design suggestion, not an executable test case. "
                "A human or adapter must instantiate it in the target environment."
            ),
            "",
        ]
    )
    return "\n".join(lines)
