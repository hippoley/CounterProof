"""Active discrimination across competing Counterproof mutation hypotheses."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import ReplayResult
from .replay import (
    CommandOutcome,
    interpret_command_outcome,
    resolve_declared_root,
    run_command,
    safe_cwd,
    structured_probe_result_to_dict,
)


@dataclass(frozen=True)
class VariantEvidence:
    surface: str
    replays: tuple[ReplayResult, ...]
    outcomes: tuple[CommandOutcome | None, ...]
    predictions: tuple[str | None, ...] = ()
    roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.predictions and len(self.predictions) != len(self.replays):
            raise ValueError("predictions must align one-to-one with replays")
        if self.roles and len(self.roles) != len(self.replays):
            raise ValueError("roles must align one-to-one with replays")
        invalid_roles = set(self.roles) - {"fitness", "diagnostic"}
        if invalid_roles:
            raise ValueError(
                "roles must be fitness or diagnostic: "
                + ", ".join(sorted(invalid_roles))
            )

    @property
    def valid_replays(self) -> tuple[ReplayResult, ...]:
        return tuple(item for item in self.replays if item.verdict != "infra_error")

    @property
    def normalized_roles(self) -> tuple[str, ...]:
        if self.roles:
            return self.roles
        return tuple("fitness" for _ in self.replays)

    @property
    def fitness_replays(self) -> tuple[ReplayResult, ...]:
        return tuple(
            replay
            for replay, role in zip(
                self.replays,
                self.normalized_roles,
                strict=False,
            )
            if role == "fitness" and replay.verdict != "infra_error"
        )

    @property
    def diagnostic_replays(self) -> tuple[ReplayResult, ...]:
        return tuple(
            replay
            for replay, role in zip(
                self.replays,
                self.normalized_roles,
                strict=False,
            )
            if role == "diagnostic" and replay.verdict != "infra_error"
        )

    @property
    def fitness_infra_error_count(self) -> int:
        return sum(
            1
            for replay, role in zip(
                self.replays,
                self.normalized_roles,
                strict=False,
            )
            if role == "fitness" and replay.verdict == "infra_error"
        )

    @property
    def mean_delta(self) -> float:
        valid = self.fitness_replays
        if not valid:
            return 0.0
        return sum(item.delta for item in valid) / len(valid)

    @property
    def regression_count(self) -> int:
        return sum(
            1
            for item in self.fitness_replays
            if item.candidate_score < item.baseline_score
        )

    @property
    def failure_count(self) -> int:
        return sum(1 for item in self.fitness_replays if item.verdict == "fail")

    @property
    def infra_error_count(self) -> int:
        return sum(1 for item in self.replays if item.verdict == "infra_error")

    @property
    def signature(self) -> tuple[str, ...]:
        return tuple(
            "I"
            if item.verdict == "infra_error"
            else ("P" if item.verdict == "pass" else "F")
            for item in self.replays
        )

    @property
    def expected_signature(self) -> tuple[str, ...]:
        return tuple(
            "P" if prediction == "pass" else ("F" if prediction == "fail" else "?")
            for prediction in self.predictions
        )

    @property
    def prediction_coverage(self) -> int:
        return sum(prediction is not None for prediction in self.predictions)

    @property
    def prediction_mismatch_count(self) -> int:
        mismatches = 0
        for replay, prediction in zip(self.replays, self.predictions, strict=False):
            if prediction is None or replay.verdict == "infra_error":
                continue
            actual = replay.verdict
            if actual != prediction:
                mismatches += 1
        return mismatches

    @property
    def prediction_status(self) -> str:
        if not self.predictions or self.prediction_coverage == 0:
            return "unregistered"
        if self.prediction_mismatch_count:
            return "contradicted"
        if self.prediction_coverage < len(self.replays):
            return "partial"
        if self.infra_error_count:
            return "inconclusive"
        return "supported"

    @property
    def status(self) -> str:
        if self.fitness_infra_error_count:
            return "inconclusive"
        if not self.fitness_replays:
            return "diagnostic-only" if self.diagnostic_replays else "inconclusive"
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
    def has_preregistered_predictions(self) -> bool:
        return any(item.prediction_coverage > 0 for item in self.variants)

    @property
    def eligible_survivors(self) -> tuple[VariantEvidence, ...]:
        survivors = self.survivors
        if not self.has_preregistered_predictions:
            return survivors
        return tuple(
            item for item in survivors if item.prediction_status == "supported"
        )

    @property
    def prediction_blocked_survivors(self) -> tuple[VariantEvidence, ...]:
        eligible = {item.surface for item in self.eligible_survivors}
        return tuple(
            item for item in self.survivors if item.surface not in eligible
        )

    @property
    def discriminated_surface(self) -> str | None:
        survivors = self.eligible_survivors
        return survivors[0].surface if len(survivors) == 1 else None

    @property
    def selection_state(self) -> str:
        if self.discriminated_surface:
            return "unique-survivor"
        if len(self.eligible_survivors) > 1:
            return "ambiguous"
        if self.prediction_blocked_survivors:
            return "prediction-blocked"
        if any(item.status == "diagnostic-only" for item in self.variants):
            return "diagnostic-only"
        return "no-survivor"

    @property
    def declared_diagnostic_cases(self) -> tuple[str, ...]:
        if not self.variants:
            return ()
        first = self.variants[0]
        return tuple(
            replay.case_id
            for replay, role in zip(
                first.replays,
                first.normalized_roles,
                strict=False,
            )
            if role == "diagnostic"
        )

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
    def preregistered_diagnostic_cases(self) -> tuple[str, ...]:
        if not self.variants:
            return ()
        case_ids = [item.case_id for item in self.variants[0].replays]
        diagnostic: list[str] = []
        for index, case_id in enumerate(case_ids):
            expected = {
                item.expected_signature[index]
                for item in self.variants
                if index < len(item.expected_signature)
                and item.expected_signature[index] != "?"
            }
            if len(expected) > 1:
                diagnostic.append(case_id)
        return tuple(diagnostic)

    @property
    def unresolved_pairs(self) -> tuple[tuple[str, str], ...]:
        pairs: list[tuple[str, str]] = []
        survivors = self.eligible_survivors
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
    default_protocol = str(raw.get("result_protocol", "exit-code"))
    if default_protocol not in {"exit-code", "json-v1"}:
        raise ValueError(f"unknown result protocol: {default_protocol}")
    manifest_status = str(raw.get("status", "ready"))
    if manifest_status != "ready":
        raise ValueError(
            f"discrimination manifest status is {manifest_status!r}; review it and set status='ready' before execution"
        )
    adapter = raw.get("adapter")
    if adapter is not None and (
        not isinstance(adapter, list)
        or not adapter
        or not all(isinstance(part, str) and part for part in adapter)
    ):
        raise ValueError("adapter must be a non-empty argv list")
    if adapter and str(adapter[0]).startswith("TODO_"):
        raise ValueError(
            "probe adapter placeholder has not been replaced; configure a real adapter before execution"
        )
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
    variant_outcomes: dict[str, list[CommandOutcome | None]] = {
        surface: [] for surface in selected
    }
    variant_predictions: dict[str, list[str | None]] = {
        surface: [] for surface in selected
    }
    variant_roles: dict[str, list[str]] = {
        surface: [] for surface in selected
    }

    for case in cases:
        case_id = str(case["case_id"])
        suite = str(case.get("suite", "discrimination"))
        role = str(case.get("role", "fitness"))
        if role not in {"fitness", "diagnostic"}:
            raise ValueError(
                f"invalid role for case {case_id!r}: {role!r}; expected fitness or diagnostic"
            )
        cwd = safe_cwd(root, str(case.get("cwd", ".")))
        timeout = float(case.get("timeout_seconds", default_timeout))
        protocol = str(case.get("result_protocol", default_protocol))
        if protocol not in {"exit-code", "json-v1"}:
            raise ValueError(f"unknown result protocol: {protocol}")
        common_env = {
            "COUNTERPROOF_CASE_ID": case_id,
            "COUNTERPROOF_CASE_ID": case_id,
            **case.get("env", {}),
        }
        if "payload" in case:
            case_json = json.dumps(
                case["payload"],
                ensure_ascii=False,
                sort_keys=True,
            )
            common_env["COUNTERPROOF_CASE_JSON"] = case_json
            common_env["COUNTERPROOF_CASE_JSON"] = case_json

        baseline_spec = case.get("baseline", adapter)
        if baseline_spec is None:
            raise ValueError(
                f"case {case_id!r} requires baseline argv or a top-level adapter"
            )
        if isinstance(baseline_spec, dict):
            baseline_argv = list(baseline_spec["argv"])
        else:
            baseline_argv = list(baseline_spec)

        baseline = run_command(
            baseline_argv,
            cwd=cwd,
            timeout_seconds=timeout,
            env={
                **common_env,
                "COUNTERPROOF_VARIANT": "baseline",
                "COUNTERPROOF_VARIANT": "baseline",
            },
        )
        baseline_behavior = interpret_command_outcome(
            baseline,
            protocol=protocol,
        )

        for surface in selected:
            variants = case["variants"]
            if surface not in variants:
                variant_predictions[surface].append(None)
                variant_roles[surface].append(role)
                variant_outcomes[surface].append(None)
                result = ReplayResult(
                    case_id=case_id,
                    suite=suite,
                    verdict="infra_error",
                    baseline_score=baseline_behavior.score,
                    candidate_score=0.0,
                    note=f"variant {surface!r} is missing for this case",
                )
                variant_results[surface].append(result)
                continue

            variant_spec = variants[surface]
            if isinstance(variant_spec, list):
                argv = list(variant_spec)
                expectation = None
            elif isinstance(variant_spec, dict):
                variant_argv = variant_spec.get("argv", adapter)
                if variant_argv is None:
                    raise ValueError(
                        f"variant {surface!r} in case {case_id!r} requires argv or a top-level adapter"
                    )
                argv = list(variant_argv)
                expectation = variant_spec.get("expect")
                if expectation not in {None, "pass", "fail"}:
                    raise ValueError(
                        f"invalid expectation for {surface!r} in case {case_id!r}: "
                        f"{expectation!r}"
                    )
            else:
                raise TypeError(
                    f"variant {surface!r} in case {case_id!r} must be argv or object"
                )

            variant_predictions[surface].append(expectation)
            variant_roles[surface].append(role)
            outcome = run_command(
                argv,
                cwd=cwd,
                timeout_seconds=timeout,
                env={
                    **common_env,
                    "COUNTERPROOF_VARIANT": surface,
                    "COUNTERPROOF_VARIANT": surface,
                },
            )
            behavior = interpret_command_outcome(
                outcome,
                protocol=protocol,
            )
            result = ReplayResult(
                case_id=case_id,
                suite=suite,
                verdict=behavior.verdict,
                baseline_score=baseline_behavior.score,
                candidate_score=behavior.score,
                note=(
                    f"protocol={protocol}; baseline rc={baseline.returncode}, "
                    f"{surface} rc={outcome.returncode}; "
                    f"{baseline.duration_ms}ms/{outcome.duration_ms}ms; "
                    f"{surface}={behavior.note}"
                ),
            )
            variant_results[surface].append(result)
            variant_outcomes[surface].append(outcome)

    variants = tuple(
        VariantEvidence(
            surface=surface,
            replays=tuple(variant_results[surface]),
            outcomes=tuple(variant_outcomes[surface]),
            predictions=tuple(variant_predictions[surface]),
            roles=tuple(variant_roles[surface]),
        )
        for surface in selected
    )
    return DiscriminationRun(variants=variants)


def discrimination_to_dict(run: DiscriminationRun) -> dict[str, Any]:
    return {
        "discriminated_surface": run.discriminated_surface,
        "survivors": [item.surface for item in run.survivors],
        "eligible_survivors": [item.surface for item in run.eligible_survivors],
        "prediction_blocked_survivors": [
            item.surface for item in run.prediction_blocked_survivors
        ],
        "selection_state": run.selection_state,
        "has_preregistered_predictions": run.has_preregistered_predictions,
        "variants": [
            {
                "surface": item.surface,
                "status": item.status,
                "mean_delta": item.mean_delta,
                "regressions": item.regression_count,
                "failures": item.failure_count,
                "infra_errors": item.infra_error_count,
                "fitness_case_count": len(item.fitness_replays),
                "diagnostic_case_count": len(item.diagnostic_replays),
                "roles": list(item.normalized_roles),
                "signature": list(item.signature),
                "expected_signature": list(item.expected_signature),
                "prediction_status": item.prediction_status,
                "prediction_coverage": item.prediction_coverage,
                "prediction_mismatches": item.prediction_mismatch_count,
                "probe_results": [
                    structured_probe_result_to_dict(outcome.probe_result)
                    if outcome is not None
                    else None
                    for outcome in item.outcomes
                ],
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
        "preregistered_diagnostic_cases": list(run.preregistered_diagnostic_cases),
        "declared_diagnostic_cases": list(run.declared_diagnostic_cases),
        "unresolved_pairs": [list(pair) for pair in run.unresolved_pairs],
    }


def render_discrimination_markdown(
    run: DiscriminationRun,
    *,
    mechanisms: dict[str, str] | None = None,
) -> str:
    lines = [
        "# Counterproof Discrimination Matrix",
        "",
        "| Surface | Hypothesis | Runtime | Prediction | Mean delta | Regressions | Failures |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for item in run.variants:
        mechanism = (mechanisms or {}).get(item.surface, "not supplied")
        lines.append(
            f"| {item.surface} | {mechanism} | **{item.status.upper()}** | "
            f"**{item.prediction_status.upper()}** | {item.mean_delta:+.3f} | "
            f"{item.regression_count} | {item.failure_count} |"
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

    if run.declared_diagnostic_cases:
        lines.extend(
            [
                "",
                "## Case roles",
                "",
                (
                    "Diagnostic cases may intentionally produce a pre-registered FAIL. "
                    "They contribute to hypothesis discrimination but are excluded from "
                    "fitness failure/regression counting and cannot by themselves promote "
                    "a mutation."
                ),
                "",
                "Declared diagnostic cases: "
                + ", ".join(
                    f"**{case_id}**" for case_id in run.declared_diagnostic_cases
                )
                + ".",
            ]
        )

    lines.extend(["", "## Prediction registration", ""])
    if run.has_preregistered_predictions:
        lines.append(
            "Intervention outcomes were pre-registered where the manifest supplied "
            "an expected PASS/FAIL result. Selection requires a surviving intervention "
            "to have fully supported registered predictions."
        )
        if run.preregistered_diagnostic_cases:
            lines.append("")
            lines.append(
                "Cases with different pre-registered predictions: "
                + ", ".join(
                    f"**{case_id}**" for case_id in run.preregistered_diagnostic_cases
                )
                + "."
            )
    else:
        lines.append(
            "No pre-registered predictions were supplied. Runtime comparison is still "
            "useful, but causal interpretation has weaker protection against post-hoc stories."
        )

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
    elif len(run.eligible_survivors) > 1:
        labels = ", ".join(item.surface for item in run.eligible_survivors)
        lines.append(
            f"Multiple hypotheses survived: **{labels}**. The current cases do not "
            "discriminate between them; add a case where their predicted behaviors differ."
        )
    elif run.selection_state == "diagnostic-only":
        lines.append(
            "The current experiment is diagnostic-only. Its expected PASS/FAIL outcomes "
            "can test predictions, but it cannot by itself justify mutation promotion."
        )
    elif run.prediction_blocked_survivors:
        blocked = ", ".join(
            item.surface for item in run.prediction_blocked_survivors
        )
        lines.append(
            f"Runtime survivor(s) **{blocked}** were blocked from selection because "
            "their pre-registered predictions were contradicted, partial, or inconclusive."
        )
    else:
        lines.append(
            "No tested hypothesis survived. The current candidate set is inadequate or the "
            "probe environment does not reproduce the relevant mechanism."
        )
    lines.append("")
    return "\n".join(lines)
