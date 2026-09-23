"""Render a GitHub-friendly Counterproof report from an EvolutionPacket."""
from __future__ import annotations

from .models import CandidateMutation, EvolutionPacket


def _status(candidate: CandidateMutation) -> str:
    if candidate.eligible_for_promotion:
        return "PROMOTE"
    if candidate.failure_count or candidate.regression_count:
        return "REJECT"
    return "HOLD"


def render_evolution_pr(packet: EvolutionPacket) -> str:
    selected = packet.selected_candidate()
    lines: list[str] = [
        f"# Counterproof — {packet.packet_id}",
        "",
        "> Your agent changed. Show the proof.",
        "",
        f"**Agent:** {packet.agent}",
        f"**Failure:** {packet.failure_summary}",
        "",
    ]

    if packet.metadata:
        lines.extend(
            [
                "## Provenance",
                "",
                *[
                    f"- **{key.replace('_', ' ')}:** {value}"
                    for key, value in packet.metadata.items()
                    if value
                ],
                "",
            ]
        )

    lines.extend(
        [
            "## 1. Decision Capsule",
            "",
            packet.decision_capsule,
            "",
            "## 2. Outcome Receipt",
            "",
            packet.outcome_receipt,
            "",
            "## 3. Causal hypotheses",
            "",
            "| ID | Target | Mechanism | Uncertainty |",
            "|---|---|---|---:|",
        ]
    )
    for hypothesis in packet.hypotheses:
        lines.append(
            f"| {hypothesis.id} | {hypothesis.target_surface} | "
            f"{hypothesis.mechanism} | {hypothesis.uncertainty:.2f} |"
        )

    if packet.probes:
        lines.extend(
            [
                "",
                "## 3b. Discriminating probes",
                "",
                "| Probe | Hypothesis | Intervention | Supports if | Falsified if | Holdout |",
                "|---|---|---|---|---|---|",
            ]
        )
        for probe in packet.probes:
            lines.append(
                f"| {probe.id} | {probe.hypothesis_id} | {probe.intervention} | "
                f"{probe.expected_if_true} | {probe.falsifier} | "
                f"{probe.holdout or 'not-set'} |"
            )

    lines.extend(
        [
            "",
            "## 4. Candidate mutations",
            "",
            "| Candidate | Surface | Mean delta | Regressions | Failures | Risk | Gate |",
            "|---|---|---:|---:|---:|---|---|",
        ]
    )
    for candidate in packet.candidates:
        risks = ", ".join(candidate.risk_flags) if candidate.risk_flags else "none"
        lines.append(
            f"| {candidate.id}: {candidate.title} | {candidate.surface} | "
            f"{candidate.mean_delta:+.3f} | {candidate.regression_count} | "
            f"{candidate.failure_count} | {risks} | **{_status(candidate)}** |"
        )

    if selected is not None:
        lines.extend(
            [
                "",
                "## 5. Selected behavior change",
                "",
                f"### {selected.title}",
                "",
                selected.behavior_diff,
                "",
                f"**Activation scope:** {selected.activation_scope}",
                f"**Rollback ref:** {selected.rollback_ref or 'not-set'}",
                "",
                "### Replay matrix",
                "",
                "| Case | Suite | Baseline | Candidate | Delta | Verdict |",
                "|---|---|---:|---:|---:|---|",
            ]
        )
        for replay in selected.replay_results:
            lines.append(
                f"| {replay.case_id} | {replay.suite} | "
                f"{replay.baseline_score:.3f} | {replay.candidate_score:.3f} | "
                f"{replay.delta:+.3f} | {replay.verdict} |"
            )
        lines.extend(
            [
                "",
                "### Promotion decision",
                "",
                (
                    "Eligible for promotion."
                    if selected.eligible_for_promotion
                    else "Not eligible for automatic promotion."
                ),
            ]
        )

    lines.extend(
        [
            "",
            "## 6. Evidence semantics",
            "",
            (
                "Human corrections, verifier outcomes, retries, undo, silence, and "
                "infrastructure failures are not equivalent signals. Infrastructure "
                "failures are excluded from behavioral regression counting."
            ),
            "",
            "## 7. Target lifecycle (roadmap)",
            "",
            (
                "observe -> attribute -> mutate -> controlled replay -> holdout -> "
                "shadow/canary -> promote or rollback"
            ),
            "",
            (
                "Only the stages marked as tested by evopr audit should be treated as "
                "implemented runtime behavior."
            ),
            "",
        ]
    )
    return "\n".join(lines)
