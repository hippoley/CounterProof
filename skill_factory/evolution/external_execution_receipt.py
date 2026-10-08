from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def admit_external_execution_receipt(
    receipt_path: Path,
    provenance_path: Path,
) -> dict[str, Any]:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
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
        raise ValueError("candidate commit must be a full git SHA")
    if not isinstance(tree, str) or not _HEX40.fullmatch(tree):
        raise ValueError("candidate tree must be a full git SHA")
    if receipt.get("dirty") is not False:
        raise ValueError("current admission requires a clean captured candidate")
    if not isinstance(command, str) or not command.strip():
        raise ValueError("execution command is required")
    if not isinstance(output_sha, str) or not _HEX64.fullmatch(output_sha):
        raise ValueError("output sha256 must be 64 lowercase hex chars")
    if not isinstance(exit_code, int):
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

    return {
        "receipt_type": "EXTERNAL_EXECUTION_EVIDENCE_INPUT",
        "admission": "BOUND_EXECUTION_INPUT",
        "producer": {
            "identity": producer,
            "repository": p["repository"],
            "tag": p["tag"],
            "resolved_commit": p["resolved_commit"],
            "done_gate_sha256": p["done_gate_sha256"],
        },
        "candidate": {
            "repository": repo,
            "commit": commit,
            "tree": tree,
            "dirty": False,
        },
        "execution": {
            "label": receipt.get("label"),
            "command": command,
            "exit_code": exit_code,
            "output_sha256": output_sha,
            "verifier": receipt.get("verifier"),
            "ci": receipt.get("ci"),
            "ref": receipt.get("ref"),
        },
        "semantic_boundary": (
            "This admits externally produced execution evidence only. It does not "
            "establish that the candidate is correct, fixed, mergeable, or that the "
            "executed command is a sufficient oracle for the claim."
        ),
    }
