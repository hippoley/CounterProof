"""Active discrimination across competing EvoPR mutation hypotheses."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import ReplayResult
from .replay import CommandOutcome, resolve_declared_root, run_command, safe_cwd


@dataclass(frozen=True)
class VariantEvidence:
    surface: str
    replays: tuple[ReplayResult, ...]
    outcomes: tuple[CommandOutcome, ...]

    @property
    def valid_replays(self) -> tuple[ReplayResult, ...]:
        return tuple(item for item in self.replays if item.verdict != "infra_error")

    @property
    def mean_delta(self) -> float:
        valid = self.valid_replays
        if not valid:
            return 0.0
        return sum(item.delta for item in valid) / len(valid)

    @property
    def regression_count(self) -> int:
        return sum(
            1
            for item in self.valid_replays
            if item.candidate_score < item.baseline_score
        )

    @property
    def failure_count(self) -> int:
        return sum(1 for item in self.valid_replays if item.verdict == "fail")

    @property
    def infra_error_count(self) -> int:
        return sum(1 for item in self.replays if item.verdict == "infra_error")

    @property
    def signature(self) -> tuple[str, ...]:
        return tuple(
            "I"
            if item.verdict == "infra_error"
            else ("P" if item.candidate_score >= 1.0 else "F")
            for item in self.replays
        )

    @property
    def status(self) -> str:
        if not self.valid_replays or self.infra_error_count:
            return "inconclusive"
        if self.failure_count or self.regression_count:
            return "falsified"
        if self.mean_delta > 0:
            return "survived"
        return "inconclusive"


@dataclass(frozen=True)
class DiscriminationRun:
    variants: tuple[VariantEvidence, ...]

    @property
    def survivors(self) -> tuple[VariantEvidence, ...]:
        return tuple(item for item in self.variants if item.status == "survived")

    @property
    def discriminated_surface(self) -> str | None:
        survivors = self.survivors
        return survivors[0].surface if len(survivors) == 1 else None

    @property
    def diagnostic_cases(self) -> tuple[str, ...]:
        if not self.variants:
            return ()
        case_ids = [item.case_id for item in self.variants[0].replays]
        diagnostic: list[str] = []
        for index, case_id in enumerate(case_ids):
            outcomes = {
                item.signature[index]
                for item in self.variants
                if index < len(item.signature)
            }
            if len(outcomes) > 1:
                diagnostic.append(case_id)
        return tuple(diagnostic)

    @property
    def unresolved_pairs(self) -> tuple[tuple[str, str], ...]:
        pairs: list[tuple[str, str]] = []
        survivors = self.survivors
        for left_index, left in enumerate(survivors):
            for right in survivors[left_index + 1 :]:
                if left.signature == right.signature:
                    pairs.append((left.surface, right.surface))
        return tuple(pairs)


def run_discrimination_manifest(
    path: Path,
    *,
    surfaces: tuple[str, ...] | None = None,
) -> DiscriminationRun:
    """Run the same cases across multiple candidate mutation variants."""
    path = path.resolve()
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    root = resolve_declared_root(path.parent, str(raw.get("root", ".")))
    default_timeout = float(raw.get("timeout_seconds", 30))
    cases = raw.get("cases", [])
    if not cases:
        raise ValueError("discrimination manifest contains no cases")

    available: set[str] = set()
    for case in cases:
        variants = case.get("variants")
        if not isinstance(variants, dict) or not variants:
            raise ValueError(
                f"case {case.get('case_id', '<unknown>')} requires a non-empty variants object"
            )
        available.update(str(surface) for surface in variants)

    selected = tuple(surfaces or sorted(available))
    missing = [surface for surface in selected if surface not in available]
    if missing:
        raise ValueError(
            "requested discrimination surfaces are unavailable: " + ", ".join(missing)
        )

    variant_results: dict[str, list[ReplayResult]] = {
        surface: [] for surface in selected
    }
    variant_outcomes: dict[str, list[CommandOutcome]] = {
        surface: [] for surface in selected
    }

    for case in cases:
        case_id = str(case["case_id"])
        suite = str(case.get("suite", "discrimination"))
        cwd = safe_cwd(root, str(case.get("cwd", ".")))
        timeout = float(case.get("timeout_seconds", default_timeout))
        common_env = {"EVOPR_CASE_ID": case_id, **case.get("env", {})}

        baseline = run_command(
            list(case["baseline"]),
            cwd=cwd,
            timeout_seconds=timeout,
            env={**common_env, "EVOPR_VARIANT": "baseline"},
        )

        for surface in selected:
            variants = case["variants"]
            if surface not in variants:
                result = ReplayResult(
                    case_id=case_id,
                    suite=suite,
                    verdict="infra_error",
                    baseline_score=baseline.score,
                    candidate_score=0.0,
                    note=f"variant {surface!r} is missing for this case",
                )
                variant_results[surface].append(result)
                continue

            outcome = run_command(
                list(variants[surface]),
                cwd=cwd,
                timeout_seconds=timeout,
                env={**common_env, "EVOPR_VARIANT": surface},
            )
            verdict = (
                "infra_error"
                if outcome.timed_out
                else ("pass" if outcome.returncode == 0 else "fail")
            )
            result = ReplayResult(
                case_id=case_id,
                suite=suite,
                verdict=verdict,
                baseline_score=baseline.score,
                candidate_score=outcome.score,
                note=(
                    f"baseline rc={baseline.returncode}, {surface} rc={outcome.returncode}; "
                    f"{baseline.duration_ms}ms/{outcome.duration_ms}ms"
                ),
            )
            variant_results[surface].append(result)
            variant_outcomes[surface].append(outcome)

    variants = tuple(
        VariantEvidence(
            surface=surface,
            replays=tuple(variant_results[surface]),
            outcomes=tuple(variant_outcomes[surface]),
        )
        for surface in selected
    )
    return DiscriminationRun(variants=variants)


def discrimination_to_dict(run: DiscriminationRun) -> dict[str, Any]:
    return {
        "discriminated_surface": run.discriminated_surface,
        "survivors": [item.surface for item in run.survivors],
        "variants": [
            {
                "surface": item.surface,
                "status": item.status,
                "mean_delta": item.mean_delta,
                "regressions": item.regression_count,
                "failures": item.failure_count,
                "infra_errors": item.infra_error_count,
                "signature": list(item.signature),
                "replays": [
                    {
                        "case_id": replay.case_id,
                        "suite": replay.suite,
                        "verdict": replay.verdict,
                        "baseline_score": replay.baseline_score,
                        "candidate_score": replay.candidate_score,
                        "delta": replay.delta,
                        "note": replay.note,
                    }
                    for replay in item.replays
                ],
            }
            for item in run.variants
        ],
        "diagnostic_cases": list(run.diagnostic_cases),
        "unresolved_pairs": [list(pair) for pair in run.unresolved_pairs],
    }


def render_discrimination_markdown(
    run: DiscriminationRun,
    *,
    mechanisms: dict[str, str] | None = None,
) -> str:
    lines = [
        "# EvoPR Discrimination Matrix",
        "",
        "| Surface | Hypothesis | Status | Mean delta | Regressions | Failures |",
        "|---|---|---|---:|---:|---:|",
    ]
    for item in run.variants:
        mechanism = (mechanisms or {}).get(item.surface, "not supplied")
        lines.append(
            f"| {item.surface} | {mechanism} | **{item.status.upper()}** | "
            f"{item.mean_delta:+.3f} | {item.regression_count} | {item.failure_count} |"
        )

    lines.extend(["", "## Case matrix", ""])
    case_ids: list[str] = []
    for item in run.variants:
        for replay in item.replays:
            if replay.case_id not in case_ids:
                case_ids.append(replay.case_id)

    header = "| Surface | " + " | ".join(case_ids) + " |"
    separator = "|---|" + "|".join("---" for _ in case_ids) + "|"
    lines.extend([header, separator])
    for item in run.variants:
        by_case = {replay.case_id: replay for replay in item.replays}
        cells = []
        for case_id in case_ids:
            replay = by_case.get(case_id)
            if replay is None:
                cells.append("missing")
            else:
                cells.append(
                    f"{replay.verdict} ({replay.baseline_score:.1f}->{replay.candidate_score:.1f})"
                )
        lines.append(f"| {item.surface} | " + " | ".join(cells) + " |")

    lines.extend(["", "## Diagnostic power", ""])
    if run.diagnostic_cases:
        lines.append(
            "Cases that separate at least two candidate behavior signatures: "
            + ", ".join(f"**{case_id}**" for case_id in run.diagnostic_cases)
            + "."
        )
    else:
        lines.append(
            "No case currently separates the tested candidate signatures."
        )
    if run.unresolved_pairs:
        lines.append("")
        lines.append(
            "Unresolved survivor pairs with identical signatures: "
            + ", ".join(
                f"**{left} vs {right}**" for left, right in run.unresolved_pairs
            )
            + ". Add a case where those interventions predict different behavior."
        )

    lines.extend(["", "## Interpretation", ""])
    if run.discriminated_surface:
        lines.append(
            f"Only **{run.discriminated_surface}** survived the current intervention matrix. "
            "This supports that hypothesis relative to the tested alternatives; it does not "
            "establish unique causal truth outside this probe set."
        )
    elif len(run.survivors) > 1:
        labels = ", ".join(item.surface for item in run.survivors)
        lines.append(
            f"Multiple hypotheses survived: **{labels}**. The current cases do not "
            "discriminate between them; add a case where their predicted behaviors differ."
        )
    else:
        lines.append(
            "No tested hypothesis survived. The current candidate set is inadequate or the "
            "probe environment does not reproduce the relevant mechanism."
        )
    lines.append("")
    return "\n".join(lines)
