"""Best-effort compensation for multi-agent Skill deployments.

Only NEW target pairs are mutated. Existing verified deployments are preserved.
A rollback failure is surfaced, never hidden as success.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


class DeploymentTransactionError(ValueError):
    """Raised when deployment is unsafe or incomplete."""


def _agents(call: Callable[..., dict[str, Any]], binary: Path,
            reference: str) -> dict[str, dict[str, Any]]:
    report = call(binary, "status", reference)
    rows = report.get("agents")
    if not isinstance(rows, list):
        raise DeploymentTransactionError("manager status has no agent list")
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("key"), str):
            raise DeploymentTransactionError("invalid agent status entry")
        if row["key"] in output:
            raise DeploymentTransactionError("duplicate agent key in manager status")
        output[row["key"]] = row
    return output


def _verified(row: dict[str, Any] | None, digest: str,
              snapshot: Callable[..., str]) -> bool:
    if not row or row.get("deployed") is not True:
        return False
    path = row.get("target_path")
    if not isinstance(path, str) or not path:
        return False
    try:
        return snapshot(Path(path), allow_root_link=True) == digest
    except (OSError, ValueError):
        return False


def _agent_flags(agents: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(part for key in agents for part in ("--agent", key))


def deploy_new_only(
    *,
    call: Callable[..., dict[str, Any]],
    binary: Path,
    reference: str,
    agents: tuple[str, ...],
    digest: str,
    snapshot: Callable[..., str],
    source_unchanged: Callable[[], bool],
) -> dict[str, Any]:
    """Deploy only missing agents, verify bytes, compensate new pairs on failure.

    Caller must already hold a valid evidence gate and completed a dry run.
    The upstream manager's conflict-preserving undeploy is used for rollback.
    """
    previous = _agents(call, binary, reference)
    pending: list[str] = []
    existing: list[str] = []
    for agent in agents:
        row = previous.get(agent)
        if row is None:
            raise DeploymentTransactionError(f"unknown target agent: {agent}")
        if row.get("deployed") is True:
            if not _verified(row, digest, snapshot):
                raise DeploymentTransactionError(
                    f"existing target drift for {agent}; refused to overwrite"
                )
            existing.append(agent)
        else:
            pending.append(agent)
    if not source_unchanged():
        raise DeploymentTransactionError("Skill changed before deployment")
    if not pending:
        return {
            "status": "VERIFIED_TARGET_BYTES", "agents": list(agents),
            "newly_deployed": [], "previously_deployed": existing,
            "compensation": "NOT_NEEDED",
        }

    wanted = tuple(pending)
    try:
        response = call(binary, "deploy", reference, *_agent_flags(wanted))
        if (
            response.get("ok") is not True
            or response.get("dry_run") is not False
            or set(response.get("agents", [])) != set(wanted)
        ):
            raise DeploymentTransactionError("upstream mutation response incomplete")
        current = _agents(call, binary, reference)
        for agent in agents:
            if not _verified(current.get(agent), digest, snapshot):
                raise DeploymentTransactionError(
                    f"PARTIAL_DEPLOYMENT: target mismatch or missing for {agent}"
                )
        if not source_unchanged():
            raise DeploymentTransactionError("Skill changed while deploying")
        return {
            "status": "VERIFIED_TARGET_BYTES", "agents": list(agents),
            "newly_deployed": pending, "previously_deployed": existing,
            "compensation": "NOT_NEEDED",
        }
    except (DeploymentTransactionError, OSError, ValueError) as error:
        # The external CLI may have applied a subset before returning failure.
        # Only compensate pairs that were NOT deployed beforehand.
        compensation = "NOT_VERIFIED"
        try:
            undone = call(binary, "undeploy", reference, *_agent_flags(wanted))
            after = _agents(call, binary, reference)
            clean = (
                undone.get("ok") is True
                and undone.get("dry_run") is False
                and set(undone.get("agents", [])) == set(wanted)
                and not undone.get("preserved")
                and all(
                    after.get(agent, {}).get("deployed") is not True
                    for agent in wanted
                )
            )
            compensation = "CONFIRMED" if clean else "INCOMPLETE"
        except (OSError, ValueError, DeploymentTransactionError):
            compensation = "INCOMPLETE"
        raise DeploymentTransactionError(
            f"PARTIAL_DEPLOYMENT: {error}; rollback_new_pairs={compensation}; "
            "inspect affected agents before retrying"
        ) from error
