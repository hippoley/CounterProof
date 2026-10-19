"""Paired Skill evaluation and fail-closed Skills Manager deployment gate.

Explicitly selected runner and manager binaries are the only programs invoked.
No skill scripts are run by this module.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import stat
import shutil
import subprocess
from pathlib import Path
from typing import Any

SCHEMA = "counterproof.skill-gate/v0.1"
SUITE_SCHEMA = "counterproof.skill-suite/v0.1"


class GateError(ValueError):
    """Fail-closed Skill gate error."""


def create_key(path: Path) -> Path:
    """Make a new local attestation key, refusing overwrite and weak permissions."""
    path = path.absolute()
    if path.parent.is_symlink():
        raise GateError("attestation key directory must not be a symlink")
    key = secrets.token_bytes(32)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as exc:
        raise GateError(f"cannot create key: {exc}") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(key)
    except OSError:
        path.unlink(missing_ok=True)
        raise
    return path


def _read_key(path: Path) -> bytes:
    """Require a separate 256-bit local trust anchor, never carried in receipts."""
    if path.is_symlink() or not path.is_file():
        raise GateError("attestation key must be a regular file, not a symlink")
    if os.name != "nt" and stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise GateError("attestation key must not be accessible by group/others")
    key = path.read_bytes()
    if len(key) != 32:
        raise GateError("attestation key must contain exactly 32 bytes")
    return key


def _mac(payload: dict, key: bytes) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def _guard_key_location(key_file: Path, source_path: str) -> None:
    """Do not accidentally package the attestation secret as part of a Skill."""
    key = key_file.resolve(strict=True)
    source = Path(source_path).resolve(strict=True)
    if key == source or source in key.parents:
        raise GateError("attestation key must be outside the managed Skill tree")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: dict) -> str:
    return _sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def _binary(name: str) -> Path:
    found = shutil.which(name)
    if not found:
        raise GateError(f"executable not found: {name}")
    return Path(found).resolve()


def _manager(binary: Path, *args: str) -> dict[str, Any]:
    try:
        done = subprocess.run(
            [str(binary), "--json", "skills", *args],
            capture_output=True, text=True, timeout=35, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GateError(f"Skills Manager invocation failed: {exc}") from exc
    if done.returncode:
        raise GateError(
            f"Skills Manager {args[0]} rejected ({done.returncode}): {done.stderr[:350]}"
        )
    try:
        result = json.loads(done.stdout)
    except json.JSONDecodeError as exc:
        raise GateError("Skills Manager did not return valid JSON") from exc
    if not isinstance(result, dict):
        raise GateError("expected Skills Manager JSON object")
    return result


def _snapshot(directory: Path, *, allow_root_link: bool = False) -> str:
    if directory.is_symlink() and not allow_root_link:
        raise GateError("Skill source root must not be a symlink")
    root = directory.resolve(strict=True)
    if not root.is_dir():
        raise GateError(f"Skill source is not a directory: {directory}")
    entries: list[dict[str, str]] = []
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise GateError(f"nested Skill symlink forbidden: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise GateError(f"non-file in Skill tree: {path}")
        total += path.stat().st_size
        if total > 50 * 1024 * 1024 or len(entries) >= 1000:
            raise GateError("Skill exceeds 50 MiB or 1000 file audit limit")
        entries.append({
            "path": path.relative_to(root).as_posix(),
            "sha256": _sha_file(path),
        })
    if "SKILL.md" not in {item["path"] for item in entries}:
        raise GateError("managed Skill has no SKILL.md")
    return _digest({"files": entries})


def _source(binary: Path, reference: str) -> dict[str, str]:
    detail = _manager(binary, "show", reference)
    for key in ("name", "id", "path"):
        if not isinstance(detail.get(key), str) or not detail[key]:
            raise GateError(f"Skills Manager show lacks {key}")
    path = Path(detail["path"])
    return {
        "name": detail["name"], "id": detail["id"],
        "path": str(path.resolve()),
        "source_type": detail.get("source_type"),
        "source_ref": detail.get("source_ref"),
        "tree_sha256": _snapshot(path),
    }


def _suite(path: Path, source: Path) -> dict:
    resolved = path.resolve(strict=True)
    if resolved == source or source in resolved.parents:
        raise GateError("evaluation suite must live outside managed Skill directory")
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != SUITE_SCHEMA:
        raise GateError("unsupported external evaluation suite schema")
    cases = data.get("cases")
    if not isinstance(cases, list) or len(cases) < 4:
        raise GateError("need at least four independent evaluation cases")
    if len(cases) > 100:
        raise GateError("suite exceeds 100 cases")
    ids = set()
    for case in cases:
        if not isinstance(case, dict) or not all(
            isinstance(case.get(k), str) and case[k]
            for k in ("id", "prompt", "expected_output")
        ):
            raise GateError("every case requires id, prompt, expected_output strings")
        if case["id"] in ids:
            raise GateError("duplicate evaluation case id")
        ids.add(case["id"])
    return data


def evaluate(
    manager_binary: str,
    reference: str,
    suite_path: Path,
    runner_binary: str,
    *,
    key_file: Path,
    min_gain: int = 1,
) -> dict:
    """Execute paired external runner evaluations, binding measured results to content."""
    if min_gain < 1:
        raise GateError("min_gain must be positive")
    key = _read_key(key_file)
    manager = _binary(manager_binary)
    runner = _binary(runner_binary)
    source = _source(manager, reference)
    _guard_key_location(key_file, source["path"])
    suite = _suite(suite_path, Path(source["path"]))
    suite_fingerprint = _sha_file(suite_path.resolve())
    runner_fingerprint = _sha_file(runner)
    manager_fingerprint = _sha_file(manager)
    cases = []
    for case in suite["cases"]:
        result = {
            "id": case["id"],
            "expected_sha256": _sha_bytes(case["expected_output"].strip().encode()),
        }
        for arm in ("baseline", "skill"):
            payload = {
                "schema_version": "counterproof.skill-runner/v0.1",
                "case_id": case["id"], "prompt": case["prompt"], "arm": arm,
                "skill_path": source["path"] if arm == "skill" else None,
            }
            try:
                proc = subprocess.run(
                    [str(runner)], input=json.dumps(payload), text=True,
                    capture_output=True, timeout=45, check=False,
                    env={
                        k: v for k, v in os.environ.items()
                        if k in {"PATH", "HOME", "LANG", "SYSTEMROOT"}
                    },
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise GateError(
                    f"runner failed for {case['id']} ({arm}): {exc}"
                ) from exc
            if proc.returncode:
                raise GateError(
                    f"runner returned {proc.returncode} for {case['id']} ({arm})"
                )
            try:
                observed = json.loads(proc.stdout)
            except json.JSONDecodeError as exc:
                raise GateError("runner did not output JSON") from exc
            if not isinstance(observed, dict) or not isinstance(observed.get("output"), str):
                raise GateError("runner JSON must contain a string output")
            output = observed["output"].strip()
            result[arm] = {
                "pass": output == case["expected_output"].strip(),
                "output_sha256": _sha_bytes(output.encode()),
            }
        cases.append(result)
        if _source(manager, reference) != source:
            raise GateError("managed Skill mutated during paired evaluation")
    if _source(manager, reference) != source:
        raise GateError("managed Skill mutated during paired evaluation")
    if _sha_file(runner) != runner_fingerprint:
        raise GateError("runner executable was replaced during evaluation")
    if _sha_file(manager) != manager_fingerprint:
        raise GateError("manager executable was replaced during evaluation")
    if _sha_file(suite_path.resolve()) != suite_fingerprint:
        raise GateError("external suite changed during evaluation")
    gain = sum(row["skill"]["pass"] and not row["baseline"]["pass"] for row in cases)
    regressions = sum(row["baseline"]["pass"] and not row["skill"]["pass"] for row in cases)
    receipt = {
        "schema_version": SCHEMA, "source": source,
        "suite_sha256": suite_fingerprint,
        "suite_id": suite.get("suite_id", "unnamed"),
        "runner_sha256": runner_fingerprint,
        "runner_path": str(runner),
        "manager_sha256": manager_fingerprint,
        "manager_path": str(manager),
        "case_count": len(cases), "cases": cases,
        "gain_cases": gain, "regression_cases": regressions,
        "min_gain": min_gain,
        "verdict": (
            "PASS_SCOPED" if gain >= min_gain and regressions == 0 else "FAIL"
        ),
        "evidence_scope": "LOCAL_PAIRED_EXPLICIT_RUNNER_AND_EXTERNAL_SUITE",
        "independence": "PATH_SEPARATED_ONLY_AUTHORSHIP_NOT_VERIFIED",
        "production_effect": "UNVERIFIED",
    }
    receipt["receipt_sha256"] = _digest(receipt)
    receipt["attestation_hmac_sha256"] = _mac(receipt, key)
    return receipt


def _checked_receipt(path: Path, key_file: Path) -> dict:
    key = _read_key(key_file)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA:
        raise GateError("invalid gate receipt schema")
    claimed_mac = data.get("attestation_hmac_sha256")
    unsigned = {
        k: v for k, v in data.items() if k != "attestation_hmac_sha256"
    }
    if not isinstance(claimed_mac, str) or not hmac.compare_digest(
        claimed_mac, _mac(unsigned, key)
    ):
        raise GateError("gate receipt attestation failed")
    claimed_digest = unsigned.get("receipt_sha256")
    if (
        not isinstance(claimed_digest, str)
        or claimed_digest != _digest({
            k: v for k, v in unsigned.items() if k != "receipt_sha256"
        })
    ):
        raise GateError("gate receipt digest mismatch")
    cases = data.get("cases")
    if (
        not isinstance(cases, list) or len(cases) < 4
        or data.get("case_count") != len(cases)
    ):
        raise GateError("receipt has insufficient evaluated cases")
    if not all(
        isinstance(case, dict)
        and isinstance(case.get("baseline"), dict)
        and isinstance(case.get("skill"), dict)
        and isinstance(case["baseline"].get("pass"), bool)
        and isinstance(case["skill"].get("pass"), bool)
        for case in cases
    ):
        raise GateError("invalid paired observations")
    gain = sum(x["skill"]["pass"] and not x["baseline"]["pass"] for x in cases)
    regress = sum(x["baseline"]["pass"] and not x["skill"]["pass"] for x in cases)
    if (
        data.get("gain_cases") != gain or data.get("regression_cases") != regress
        or not isinstance(data.get("min_gain"), int) or data["min_gain"] < 1
        or data.get("verdict") != (
            "PASS_SCOPED" if gain >= data["min_gain"] and regress == 0 else "FAIL"
        )
    ):
        raise GateError("receipt verdict inconsistent with observations")
    if data["verdict"] != "PASS_SCOPED":
        raise GateError("evaluation gate did not pass")
    return data


def promote(
    manager_binary: str, reference: str, receipt_path: Path,
    agents: tuple[str, ...], *, key_file: Path,
    suite_path: Path, apply: bool = False,
    confirm_sha256: str | None = None,
) -> dict:
    """Preflight by default; explicit apply must match evaluated content bytes."""
    receipt = _checked_receipt(receipt_path, key_file)
    if _sha_file(suite_path.resolve(strict=True)) != receipt.get("suite_sha256"):
        raise GateError("external evaluation suite changed since evaluation")
    runner_path = Path(receipt.get("runner_path") or "")
    if not runner_path.is_file() or _sha_file(runner_path) != receipt.get("runner_sha256"):
        raise GateError("evaluation runner changed since evaluation")
    if (
        not agents or len(set(agents)) != len(agents)
        or not all(agent and agent.strip() == agent for agent in agents)
    ):
        raise GateError("explicit, unique agent keys required")
    binary = _binary(manager_binary)
    if str(binary) != receipt.get("manager_path") or _sha_file(binary) != receipt.get("manager_sha256"):
        raise GateError("Skills Manager binary changed since evaluation")
    source = _source(binary, reference)
    _guard_key_location(key_file, source["path"])
    if source != receipt.get("source"):
        raise GateError("Skill path, identity or contents changed since evaluation")
    if apply and confirm_sha256 != source["tree_sha256"]:
        raise GateError(
            "apply requires --confirm-sha256 matching the evaluated Skill tree"
        )
    flags = [part for agent in agents for part in ("--agent", agent)]
    preflight = _manager(binary, "deploy", reference, *flags, "--dry-run")
    if (
        preflight.get("ok") is not True
        or preflight.get("dry_run") is not True
        or set(preflight.get("agents", [])) != set(agents)
    ):
        raise GateError("Skills Manager preflight did not confirm every target")
    if not apply:
        return {
            "status": "PREFLIGHT_ONLY", "agents": list(agents),
            "skill_tree_sha256": source["tree_sha256"],
            "changed_pairs": preflight.get("changed_pairs"), "deployed": False,
        }
    if _source(binary, reference) != source:
        raise GateError("Skill source changed after preflight")
    if _sha_file(suite_path.resolve()) != receipt["suite_sha256"]:
        raise GateError("external suite changed after preflight")
    if _sha_file(runner_path) != receipt["runner_sha256"]:
        raise GateError("evaluation runner changed after preflight")
    if _sha_file(binary) != receipt["manager_sha256"]:
        raise GateError("Skills Manager binary changed after preflight")
    # Only mutate previously absent target pairs. A partial upstream write
    # triggers best-effort compensation of those new pairs, never an automatic
    # removal of existing verified deployments.
    from skill_factory.skill_deploy_tx import (
        DeploymentTransactionError, deploy_new_only,
    )

    def source_unchanged() -> bool:
        return (
            _source(binary, reference) == source
            and _sha_file(suite_path.resolve()) == receipt["suite_sha256"]
            and _sha_file(runner_path) == receipt["runner_sha256"]
            and _sha_file(binary) == receipt["manager_sha256"]
        )

    try:
        transaction = deploy_new_only(
            call=_manager, binary=binary, reference=reference, agents=agents,
            digest=source["tree_sha256"], snapshot=_snapshot,
            source_unchanged=source_unchanged,
        )
    except DeploymentTransactionError as exc:
        raise GateError(str(exc)) from exc
    return {
        **transaction,
        "skill_tree_sha256": source["tree_sha256"], "deployed": True,
        "scope": "FILES_AND_MANAGER_STATUS_ONLY;AGENT_BEHAVIOR_UNVERIFIED",
    }
