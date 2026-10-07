"""Generic three-candidate causal replay receipts.

A causal replay compares three distinct candidates under one frozen oracle:

CONTROL -> BAD -> REVERT

The manifest pre-registers the expected observation for each role. CounterProof
only mints a witnessed causal receipt when all observations match those declared
expectations and at least one expectation has the intervention signature
CONTROL == REVERT != BAD.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .receipt import file_sha256

ROLES = ("CONTROL", "BAD", "REVERT")


def _load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        payload = (
            json.loads(text)
            if path.suffix.lower() == ".json"
            else yaml.safe_load(text)
        )
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ValueError(f"could not parse {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def _resolve_local(root: Path, candidate: Path, *, label: str) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay within the causal replay directory") from exc
    return resolved


def _get_path(payload: Any, path: str) -> Any:
    current = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def _expectation_pattern(expected: dict[str, Any]) -> bool:
    return (
        expected["CONTROL"] == expected["REVERT"]
        and expected["BAD"] != expected["CONTROL"]
    )


def build_causal_replay_receipt(manifest_file: Path) -> dict[str, Any]:
    manifest = _load_mapping(manifest_file)
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported causal replay manifest schema_version")

    case = manifest.get("case")
    experiment = manifest.get("experiment")
    oracle = manifest.get("oracle")
    candidates = manifest.get("candidates")
    expectations = manifest.get("expectations")
    observation_root = manifest.get("observation_root")
    identity_path = manifest.get("identity_path")

    if not isinstance(case, str) or not case:
        raise ValueError("causal replay manifest requires a non-empty case")
    if not isinstance(experiment, str) or not experiment:
        raise ValueError("causal replay manifest requires a non-empty experiment")
    if not isinstance(oracle, dict) or not isinstance(oracle.get("id"), str):
        raise ValueError("causal replay manifest requires oracle.id")
    if not isinstance(candidates, dict):
        raise ValueError("causal replay manifest requires candidates")
    if not isinstance(expectations, list) or not expectations:
        raise ValueError("causal replay manifest requires non-empty expectations")
    if observation_root is not None and not isinstance(observation_root, str):
        raise ValueError("observation_root must be a dotted path string")
    if identity_path is not None and not isinstance(identity_path, str):
        raise ValueError("identity_path must be a dotted path string")

    root = manifest_file.parent.resolve()
    loaded: dict[str, dict[str, Any]] = {}
    identities: dict[str, str] = {}
    evidence_meta: dict[str, dict[str, Any]] = {}

    for role in ROLES:
        spec = candidates.get(role)
        if not isinstance(spec, dict):
            raise ValueError(f"causal replay requires candidate {role}")
        identity = spec.get("identity")
        evidence_name = spec.get("evidence")
        if not isinstance(identity, str) or not identity:
            raise ValueError(f"candidate {role} requires a non-empty identity")
        if not isinstance(evidence_name, str) or not evidence_name:
            raise ValueError(f"candidate {role} requires an evidence file")

        evidence_path = _resolve_local(
            root,
            root / evidence_name,
            label=f"candidate {role} evidence",
        )
        payload = _load_mapping(evidence_path)
        if identity_path is not None:
            try:
                observed_identity = _get_path(payload, identity_path)
            except KeyError as exc:
                raise ValueError(
                    f"candidate {role} evidence is missing identity_path "
                    f"{identity_path!r}"
                ) from exc
            if observed_identity != identity:
                raise ValueError(
                    f"candidate {role} identity expected {identity!r}, "
                    f"observed {observed_identity!r}"
                )

        observation = payload
        if observation_root:
            try:
                observation = _get_path(payload, observation_root)
            except KeyError as exc:
                raise ValueError(
                    f"candidate {role} evidence is missing observation_root "
                    f"{observation_root!r}"
                ) from exc
            if not isinstance(observation, dict):
                raise ValueError(
                    f"candidate {role} observation_root must resolve to an object"
                )

        identities[role] = identity
        loaded[role] = observation
        evidence_meta[role] = {
            "path": evidence_path.relative_to(root).as_posix(),
            "sha256": file_sha256(evidence_path),
        }

    if len(set(identities.values())) != len(ROLES):
        raise ValueError(
            "INVALID_EXPERIMENT: CONTROL, BAD, and REVERT identities must be distinct"
        )

    rows: list[dict[str, Any]] = []
    causal_expectations = 0
    all_match = True
    for index, raw in enumerate(expectations):
        if not isinstance(raw, dict):
            raise ValueError(f"expectation {index} must be an object")
        path = raw.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError(f"expectation {index} requires a dotted path")

        expected: dict[str, Any] = {}
        observed: dict[str, Any] = {}
        matches: dict[str, bool] = {}
        for role in ROLES:
            if role not in raw:
                raise ValueError(f"expectation {path!r} requires {role}")
            expected[role] = raw[role]
            try:
                observed[role] = _get_path(loaded[role], path)
            except KeyError as exc:
                raise ValueError(
                    f"candidate {role} observation is missing {path!r}"
                ) from exc
            matches[role] = observed[role] == expected[role]

        causal_pattern = _expectation_pattern(expected)
        causal_expectations += int(causal_pattern)
        row_match = all(matches.values())
        all_match = all_match and row_match
        rows.append(
            {
                "path": path,
                "expected": expected,
                "observed": observed,
                "matches": matches,
                "causal_pattern": causal_pattern,
                "match": row_match,
            }
        )

    if causal_expectations == 0:
        raise ValueError(
            "INVALID_EXPERIMENT: at least one expectation must declare "
            "CONTROL == REVERT != BAD"
        )

    verdict = (
        "WITNESSED_CAUSAL_REPLAY"
        if all_match
        else "INCONCLUSIVE_CAUSAL_REPLAY"
    )
    return {
        "schema_version": 1,
        "case": case,
        "experiment": experiment,
        "oracle": oracle,
        "manifest": {
            "path": manifest_file.name,
            "sha256": file_sha256(manifest_file),
        },
        "candidates": {
            role: {
                "identity": identities[role],
                "evidence": evidence_meta[role],
            }
            for role in ROLES
        },
        "expectations": rows,
        "causal_expectation_count": causal_expectations,
        "verdict": verdict,
        "interpretation": (
            "The BAD candidate uniquely matches the declared intervention effect "
            "and REVERT returns to CONTROL under the same frozen oracle."
            if verdict == "WITNESSED_CAUSAL_REPLAY"
            else "The three-candidate observations do not fully match the "
            "pre-registered causal replay expectations."
        ),
    }


def verify_causal_replay_receipt(
    receipt: dict[str, Any],
    *,
    manifest_file: Path,
) -> list[str]:
    failures: list[str] = []
    try:
        rebuilt = build_causal_replay_receipt(manifest_file)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return [f"causal replay could not be rebuilt: {exc}"]

    if receipt != rebuilt:
        if receipt.get("manifest") != rebuilt.get("manifest"):
            failures.append("causal replay manifest identity does not match")
        for role in ROLES:
            expected = receipt.get("candidates", {}).get(role)
            observed = rebuilt.get("candidates", {}).get(role)
            if expected != observed:
                failures.append(f"candidate {role} evidence identity does not match")
        if receipt.get("expectations") != rebuilt.get("expectations"):
            failures.append("causal replay observations do not match")
        if receipt.get("verdict") != rebuilt.get("verdict"):
            failures.append(
                f"causal replay verdict expected {receipt.get('verdict')!r}, "
                f"observed {rebuilt.get('verdict')!r}"
            )
        if not failures:
            failures.append("causal replay receipt differs from deterministic rebuild")
    return failures


def render_causal_replay_markdown(receipt: dict[str, Any]) -> str:
    lines = [
        f"## Causal replay — {receipt['case']}",
        "",
        f"**Verdict: {receipt['verdict']}**",
        "",
        f"Oracle: `{receipt['oracle']['id']}`",
        "",
        "| observation | CONTROL | BAD | REVERT | causal | match |",
        "|---|---|---|---|---:|---:|",
    ]
    for row in receipt["expectations"]:
        observed = row["observed"]
        lines.append(
            f"| `{row['path']}` | `{observed['CONTROL']}` | "
            f"`{observed['BAD']}` | `{observed['REVERT']}` | "
            f"{row['causal_pattern']} | {row['match']} |"
        )
    lines.extend(["", receipt["interpretation"], ""])
    return "\n".join(lines)
