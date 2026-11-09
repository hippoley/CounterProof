#!/usr/bin/env python3
"""Experimental Outcome Witness -> Intent-to-State Conformance bridge.

This is an interoperability probe, not a CounterProof-owned standard.

Inputs:
- Outcome Witness: external observation / oracle verdict.
- Policy: task-semantic authorized durable effect.

Output:
- PASS: sufficient external evidence and observed effect stays within policy.
- FAIL: sufficient evidence proves a policy/effect mismatch.
- INDETERMINATE: evidence is insufficient to conclude either way.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def _effect_path(intent: Dict[str, Any]) -> str:
    subject = intent.get("subject")
    predicate = intent.get("predicate")
    if not subject or not predicate:
        raise ValueError("witness intent requires subject and predicate")
    return f"{subject}.{predicate}"


def evaluate(witness: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    version = witness.get("version")
    if version != "counterproof.outcome-witness/v0.1":
        raise ValueError(f"unsupported witness version: {version}")

    verdict = witness.get("verdict")
    path = _effect_path(witness.get("intent") or {})
    authorized = (policy.get("authorized_effects") or {}).get(path)

    base = {
        "profile": "counterproof.intent-state-conformance/v0.1-experimental",
        "witness_verdict": verdict,
        "effect_path": path,
        "authorization_present": authorized is not None,
        "evidence_source": (witness.get("observer") or {}).get("source"),
        "action_ref": witness.get("action_ref"),
    }

    if verdict == "INCONCLUSIVE":
        return {
            **base,
            "verdict": "INDETERMINATE",
            "reason": "outcome_witness_inconclusive",
        }

    if verdict not in {"VERIFIED", "CONTRADICTED"}:
        raise ValueError(f"unsupported witness verdict: {verdict}")

    if authorized is None:
        return {
            **base,
            "verdict": "FAIL",
            "reason": "effect_not_authorized",
        }

    observation = witness.get("observation") or {}
    observed_value = observation.get("value")
    if observed_value is None:
        return {
            **base,
            "verdict": "INDETERMINATE",
            "reason": "observed_value_unavailable",
        }

    allowed_values = authorized.get("allowed_values") or []
    if observed_value not in allowed_values:
        return {
            **base,
            "verdict": "FAIL",
            "reason": "observed_value_outside_authorized_contract",
            "observed_value": observed_value,
            "allowed_values": allowed_values,
        }

    if verdict == "CONTRADICTED":
        return {
            **base,
            "verdict": "FAIL",
            "reason": "authoritative_outcome_contradicts_intended_effect",
            "observed_value": observed_value,
        }

    return {
        **base,
        "verdict": "PASS",
        "reason": "verified_effect_within_authorized_contract",
        "observed_value": observed_value,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--witness", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args()

    witness = json.loads(args.witness.read_text(encoding="utf-8"))
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    print(json.dumps(evaluate(witness, policy), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
