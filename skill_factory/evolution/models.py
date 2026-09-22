"""Core data model for evidence-backed agent evolution."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

EvidenceVerdict = Literal["positive", "negative", "ambiguous"]
MutationSurface = Literal[
    "skill",
    "prompt",
    "policy",
    "router",
    "memory",
    "tool",
    "eval",
]
ReplayVerdict = Literal["pass", "fail", "infra_error"]


@dataclass(frozen=True)
class Evidence:
    source: str
    kind: str
    verdict: EvidenceVerdict
    confidence: float
    note: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class Hypothesis:
    id: str
    mechanism: str
    target_surface: MutationSurface
    evidence_for: tuple[str, ...] = ()
    evidence_against: tuple[str, ...] = ()
    uncertainty: float = 0.5

    def __post_init__(self) -> None:
        if not 0.0 <= self.uncertainty <= 1.0:
            raise ValueError("uncertainty must be between 0 and 1")


@dataclass(frozen=True)
class ReplayResult:
    case_id: str
    suite: str
    verdict: ReplayVerdict
    baseline_score: float
    candidate_score: float
    note: str = ""

    def __post_init__(self) -> None:
        for label, score in (
            ("baseline_score", self.baseline_score),
            ("candidate_score", self.candidate_score),
        ):
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"{label} must be between 0 and 1")

    @property
    def delta(self) -> float:
        return self.candidate_score - self.baseline_score


@dataclass(frozen=True)
class CandidateMutation:
    id: str
    surface: MutationSurface
    title: str
    hypothesis_id: str
    behavior_diff: str
    artifact_paths: tuple[str, ...] = ()
    replay_results: tuple[ReplayResult, ...] = ()
    risk_flags: tuple[str, ...] = ()
    rollback_ref: str = ""
    activation_scope: str = "global"

    @property
    def valid_replays(self) -> tuple[ReplayResult, ...]:
        return tuple(
            replay for replay in self.replay_results if replay.verdict != "infra_error"
        )

    @property
    def mean_delta(self) -> float:
        valid = self.valid_replays
        if not valid:
            return 0.0
        return sum(replay.delta for replay in valid) / len(valid)

    @property
    def regression_count(self) -> int:
        return sum(
            1
            for replay in self.valid_replays
            if replay.candidate_score < replay.baseline_score
        )

    @property
    def failure_count(self) -> int:
        return sum(1 for replay in self.valid_replays if replay.verdict == "fail")

    @property
    def eligible_for_promotion(self) -> bool:
        valid = self.valid_replays
        return (
            bool(valid)
            and self.failure_count == 0
            and self.mean_delta > 0
            and self.regression_count == 0
            and not self.risk_flags
        )


@dataclass(frozen=True)
class EvolutionPacket:
    packet_id: str
    agent: str
    failure_summary: str
    decision_capsule: str
    outcome_receipt: str
    evidence: tuple[Evidence, ...] = ()
    hypotheses: tuple[Hypothesis, ...] = ()
    candidates: tuple[CandidateMutation, ...] = ()
    selected_candidate_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        hypothesis_ids = {hypothesis.id for hypothesis in self.hypotheses}
        for candidate in self.candidates:
            if candidate.hypothesis_id not in hypothesis_ids:
                raise ValueError(
                    f"candidate {candidate.id} references unknown hypothesis "
                    f"{candidate.hypothesis_id}"
                )
        if self.selected_candidate_id is not None:
            candidate_ids = {candidate.id for candidate in self.candidates}
            if self.selected_candidate_id not in candidate_ids:
                raise ValueError(
                    f"selected_candidate_id {self.selected_candidate_id} does not exist"
                )

    def selected_candidate(self) -> CandidateMutation | None:
        if self.selected_candidate_id is None:
            return None
        return next(
            (
                candidate
                for candidate in self.candidates
                if candidate.id == self.selected_candidate_id
            ),
            None,
        )
