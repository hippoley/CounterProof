from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def admit_external_execution_receipt(
    receipt_path: Path,
    provenance_path: Path,
    *,
    ledger_path: Path | None = None,
    log_path: Path | None = None,
    context_path: Path | None = None,
) -> dict[str, Any]:
    receipt_bytes = receipt_path.read_bytes()
    receipt_text = receipt_bytes.decode("utf-8")
    receipt = json.loads(receipt_text)
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))

    if receipt.get("schema_version") != 2:
        raise ValueError("external execution receipt must use schema_version 2")
    if receipt.get("disposition") != "reexecuted":
        raise ValueError("external execution receipt must be disposition=reexecuted")

    producer = receipt.get("producer")
    if not isinstance(producer, str) or not producer:
        raise ValueError("producer identity is required")

    repo = receipt.get("repo")
    commit = receipt.get("commit")
    tree = receipt.get("tree")
    command = receipt.get("command")
    output_sha = receipt.get("sha256")
    exit_code = receipt.get("exit_code")

    if not isinstance(repo, str) or not repo:
        raise ValueError("candidate repository is required")
    if not isinstance(commit, str) or not _HEX40.fullmatch(commit):
        raise ValueError("recorded execution commit must be a full git SHA")
    if not isinstance(tree, str) or not _HEX40.fullmatch(tree):
        raise ValueError("recorded execution tree must be a full git SHA")
    if receipt.get("dirty") is not False:
        raise ValueError("current admission requires a clean captured candidate")
    if not isinstance(command, str) or not command.strip():
        raise ValueError("execution command is required")
    if not isinstance(output_sha, str) or not _HEX64.fullmatch(output_sha):
        raise ValueError("output sha256 must be 64 lowercase hex chars")
    if type(exit_code) is not int:
        raise TypeError("exit_code must be an integer")

    p = provenance.get("producer")
    if not isinstance(p, dict):
        raise TypeError("producer provenance must be an object")
    for field in ("repository", "tag", "resolved_commit", "done_gate_sha256"):
        if not isinstance(p.get(field), str) or not p[field]:
            raise ValueError(f"producer provenance {field} is required")

    if not _HEX40.fullmatch(p["resolved_commit"]):
        raise ValueError("producer resolved_commit must be a full git SHA")
    if not _HEX64.fullmatch(p["done_gate_sha256"]):
        raise ValueError("producer done_gate_sha256 must be 64 lowercase hex chars")

    expected_version = p["tag"].lstrip("v")
    if not producer.endswith(f"@{expected_version}"):
        raise ValueError(
            f"receipt producer {producer!r} does not match frozen tag {p['tag']!r}"
        )

    raw_integrity = None
    context = None
    commit_role = "producer_recorded_git_commit"
    if any(value is not None for value in (ledger_path, log_path, context_path)):
        if ledger_path is None or log_path is None or context_path is None:
            raise ValueError(
                "raw-byte admission requires ledger_path, log_path and context_path together"
            )

        ledger_lines = ledger_path.read_text(encoding="utf-8").splitlines()
        if not ledger_lines:
            raise ValueError("producer ledger is empty")
        raw_line = receipt_text.rstrip("\r\n")
        if ledger_lines[-1] != raw_line:
            raise ValueError("receipt bytes do not match the final producer ledger line")

        log_sha = _sha256(log_path)
        if log_sha != output_sha:
            raise ValueError("producer output digest does not match preserved log bytes")

        source_run = provenance.get("source_run") or {}
        ledger_sha = _sha256(ledger_path)
        if source_run.get("ledger_sha256") != ledger_sha:
            raise ValueError("ledger sha256 does not match frozen provenance")
        if source_run.get("log_sha256") != log_sha:
            raise ValueError("log sha256 does not match frozen provenance")

        context = json.loads(context_path.read_text(encoding="utf-8"))
        if context.get("github_ref") != receipt.get("ref"):
            raise ValueError("GitHub event ref does not match producer receipt ref")
        if context.get("github_sha") != commit:
            raise ValueError("GitHub event SHA does not match producer receipt commit")

        if context.get("commit_semantics") == "github_pull_request_merge_preview":
            if context.get("github_event") != "pull_request":
                raise ValueError("merge-preview context must come from a pull_request event")
            head_sha = context.get("pull_request_head_sha")
            base_sha = context.get("pull_request_base_sha")
            if not isinstance(head_sha, str) or not _HEX40.fullmatch(head_sha):
                raise ValueError("pull request head SHA must be a full git SHA")
            if not isinstance(base_sha, str) or not _HEX40.fullmatch(base_sha):
                raise ValueError("pull request base SHA must be a full git SHA")
            if not re.fullmatch(r"refs/pull/[0-9]+/merge", str(receipt.get("ref", ""))):
                raise ValueError("merge-preview context must use refs/pull/N/merge")
            commit_role = "github_pull_request_merge_preview"
        else:
            head_sha = None
            base_sha = None
            commit_role = "workflow_dispatch_checkout"

        raw_integrity = {
            "receipt_matches_final_ledger_line": True,
            "producer_output_digest_matches_log_bytes": True,
            "ledger_sha256": ledger_sha,
            "log_sha256": log_sha,
            "artifact_sha256": source_run.get("artifact_sha256"),
            "workflow_run": source_run.get("workflow_run"),
            "artifact_id": source_run.get("artifact_id"),
        }
    else:
        head_sha = None
        base_sha = None

    candidate = {
        "repository": repo,
        "commit": commit,
        "tree": tree,
        "dirty": False,
        "commit_role": commit_role,
    }
    pull_request = None
    if context is not None and commit_role == "github_pull_request_merge_preview":
        pull_request = {
            "head_sha": head_sha,
            "base_sha": base_sha,
            "merge_preview_sha": commit,
        }

    result = {
        "receipt_type": "EXTERNAL_EXECUTION_EVIDENCE_INPUT",
        "admission": "BOUND_EXECUTION_INPUT",
        "producer": {
            "identity": producer,
            "repository": p["repository"],
            "tag": p["tag"],
            "resolved_commit": p["resolved_commit"],
            "done_gate_sha256": p["done_gate_sha256"],
        },
        "candidate": candidate,
        "execution": {
            "label": receipt.get("label"),
            "command": command,
            "exit_code": exit_code,
            "output_sha256": output_sha,
            "verifier": receipt.get("verifier"),
            "ci": receipt.get("ci"),
            "ref": receipt.get("ref"),
            "commit_role": commit_role,
        },
        "evidence_limits": {
            "receipt_kind": "capture_execution_not_pr_review",
            "authenticity": (
                "unsigned_self_report; GitHub Actions run and artifact provenance "
                "are external context, not a cryptographic signature"
            ),
            "verifier_and_ci": "producer_supplied_labels_not_attestations",
            "commit_semantics": (
                "recorded commit is a GitHub merge preview when refs/pull/N/merge; "
                "PR head and base are separately pinned in pull_request context"
            ),
            "output_integrity": (
                "raw_ledger_and_log_preserved_and_digest_checked"
                if raw_integrity is not None
                else "digest_shape_checked_only; original_log_bytes_not_verified"
            ),
            "claim_scope": "no_base_head_fix_or_merge_claim",
        },
        "semantic_boundary": (
            "This admits externally produced execution evidence only. It does not "
            "establish that the candidate is correct, fixed, mergeable, or that the "
            "executed command is a sufficient oracle for the claim."
        ),
    }
    if pull_request is not None:
        result["pull_request"] = pull_request
    if raw_integrity is not None:
        result["evidence_integrity"] = raw_integrity
    return result
