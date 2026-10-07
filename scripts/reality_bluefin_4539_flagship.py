#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping

from scripts.reality_bluefin_4539_receipt import build_receipt

FLAGSHIP_SCHEMA_VERSION = 2
FLAGSHIP_RECEIPT_TYPE = "FLAGSHIP_CONTROLLED_CAUSAL"


def _require_success(runtime_results: Mapping[str, str]) -> None:
    missing = [role for role in ("CONTROL", "BAD", "REVERT") if role not in runtime_results]
    if missing:
        raise ValueError(f"MISSING_RUNTIME_RESULT: {missing}")
    bad = {role: value for role, value in runtime_results.items() if value != "success"}
    if bad:
        raise ValueError(
            "RUNTIME_NOT_COMPARABLE: all three candidates must complete the same "
            f"runtime oracle successfully; got {bad}"
        )


def build_flagship_receipt(
    diagnostics_dir: Path,
    *,
    control_image: str,
    bad_image: str,
    revert_image: str,
    oracle_revision: str,
    source_run: int,
    workflow_head_sha: str,
    workflow_url: str,
    runtime_results: Mapping[str, str],
    upstream_workflow_revision: str,
) -> dict:
    _require_success(runtime_results)

    controlled = build_receipt(
        diagnostics_dir,
        control_image=control_image,
        bad_image=bad_image,
        revert_image=revert_image,
        oracle_revision=oracle_revision,
    )
    if controlled["verdict"] != "WITNESSED_CONTROLLED_CAUSAL":
        raise ValueError(
            "CAUSAL_SIGNATURE_NOT_WITNESSED: flagship receipt requires "
            "CONTROL -> BAD -> REVERT Y/Y-prime/Y signature"
        )

    return {
        "schema_version": FLAGSHIP_SCHEMA_VERSION,
        "receipt_type": FLAGSHIP_RECEIPT_TYPE,
        "case": controlled["case"],
        "verdict": controlled["verdict"],
        "experiment": {
            "design": controlled["experiment"],
            "intervention": "historical 30-after-keyring.conf",
            "same_oracle_for_all_candidates": True,
            "historical_image_status": controlled["historical_image_status"],
        },
        "source_run": {
            "workflow_run": int(source_run),
            "workflow_url": workflow_url,
            "workflow_head_sha": workflow_head_sha,
            "workflow_name": "Reality — Bluefin 4539 controlled causal replay",
        },
        "oracle_identity": {
            "runtime": "projectbluefin/testsuite GNOME/QEMU",
            "test_repository": "hippoley/CounterProof",
            "test_revision": oracle_revision,
            "upstream_workflow": "projectbluefin/testsuite/.github/workflows/e2e.yml",
            "upstream_workflow_revision": upstream_workflow_revision,
            "suite": "common",
        },
        "runtime_execution": {
            role: {
                "job_result": runtime_results[role],
                "image": controlled["candidates"][role]["image"],
            }
            for role in ("CONTROL", "BAD", "REVERT")
        },
        "candidates": controlled["candidates"],
        "causal_conclusion": {
            "pattern": "CONTROL_BASELINE -> BAD_DIVERGENCE -> REVERT_RECOVERY",
            "statement": (
                "In the frozen controlled environment, adding the historical "
                "30-after-keyring.conf intervention is sufficient to produce the "
                "observed late-keyring/portal dependency signature, and removing "
                "that exact intervention restores the CONTROL signature."
            ),
            "scope": "CONTROLLED_CAUSAL",
            "does_not_claim": [
                "exact replay of the unavailable May 2026 historical Bluefin images",
                "proof that every user-visible symptom from issue #4683 is reproduced",
                "general causality outside the frozen control environment",
            ],
        },
    }


def render_markdown(receipt: dict) -> str:
    candidates = receipt["candidates"]
    lines = [
        "# CounterProof flagship causal proof",
        "",
        "## Bluefin #4539 — CONTROL -> BAD -> REVERT",
        "",
        f"**Verdict: {receipt['verdict']}**",
        "",
        "CONTROL   baseline signature",
        "   | add historical 30-after-keyring.conf",
        "BAD       divergent keyring/portal signature",
        "   | remove that exact intervention",
        "REVERT    baseline signature restored",
        "",
        "| candidate | runtime | keyring active | portal->keyring | NotInInitialization |",
        "|---|---|---:|---:|---:|",
    ]
    for role in ("CONTROL", "BAD", "REVERT"):
        row = candidates[role]
        runtime = receipt["runtime_execution"][role]["job_result"]
        lines.append(
            f"| {role} | {runtime} | {row['keyring_unit_active']} | "
            f"{row['portal_wants_keyring']} | {row['not_in_initialization']} |"
        )

    lines += [
        "",
        "**Same oracle:** "
        + receipt["oracle_identity"]["runtime"]
        + " @ "
        + receipt["oracle_identity"]["test_revision"],
        "",
        "**Source run:** " + receipt["source_run"]["workflow_url"],
        "",
        "### Causal conclusion",
        "",
        receipt["causal_conclusion"]["statement"],
        "",
        "### Evidence boundary",
        "",
        "- This is a controlled causal replay, not an exact historical-image replay.",
        "- The original May 2026 registry artifacts are unavailable.",
        "- Workflow success means the runtime oracle executed; the behavioral verdict "
        "comes from the candidate signatures above.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("diagnostics_dir", type=Path)
    parser.add_argument("--control-image", required=True)
    parser.add_argument("--bad-image", required=True)
    parser.add_argument("--revert-image", required=True)
    parser.add_argument("--oracle-revision", required=True)
    parser.add_argument("--source-run", type=int, required=True)
    parser.add_argument("--workflow-head-sha", required=True)
    parser.add_argument("--workflow-url", required=True)
    parser.add_argument("--control-runtime-result", required=True)
    parser.add_argument("--bad-runtime-result", required=True)
    parser.add_argument("--revert-runtime-result", required=True)
    parser.add_argument("--upstream-workflow-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    receipt = build_flagship_receipt(
        args.diagnostics_dir,
        control_image=args.control_image,
        bad_image=args.bad_image,
        revert_image=args.revert_image,
        oracle_revision=args.oracle_revision,
        source_run=args.source_run,
        workflow_head_sha=args.workflow_head_sha,
        workflow_url=args.workflow_url,
        runtime_results={
            "CONTROL": args.control_runtime_result,
            "BAD": args.bad_runtime_result,
            "REVERT": args.revert_runtime_result,
        },
        upstream_workflow_revision=args.upstream_workflow_revision,
    )
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.summary:
        args.summary.write_text(render_markdown(receipt), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
