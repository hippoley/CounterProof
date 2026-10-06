from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

from .evidence_lifecycle import EvidenceLifecycle, merge_lifecycle_signals

_GITHUB_PR_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)$"
)


class FreshnessStatus(str, Enum):
    FRESH = "FRESH"
    DRIFTED = "DRIFTED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class FreshnessObservation:
    contract_id: str
    declared_lifecycle: EvidenceLifecycle
    freshness: FreshnessStatus
    suggested_lifecycle: EvidenceLifecycle
    source_pr: str | None
    frozen_base_sha: str | None
    frozen_head_sha: str | None
    live_base_sha: str | None
    live_head_sha: str | None
    reason: str | None


Fetcher = Callable[[str], dict[str, Any]]


def _github_json(url: str) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "CounterProof-Evidence-Freshness",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"freshness probe failed for {url}: {exc}") from exc


def _github_pr_snapshot(source_pr: str, fetcher: Fetcher) -> tuple[str, str]:
    match = _GITHUB_PR_RE.match(source_pr)
    if not match:
        raise ValueError(f"unsupported GitHub PR URL: {source_pr}")
    url = (
        "https://api.github.com/repos/"
        f"{match.group('owner')}/{match.group('repo')}/pulls/{match.group('number')}"
    )
    payload = fetcher(url)
    try:
        return payload["base"]["sha"], payload["head"]["sha"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"invalid GitHub PR payload for {source_pr}") from exc


def _suggest_lifecycle(
    declared: EvidenceLifecycle,
    freshness: FreshnessStatus,
) -> EvidenceLifecycle:
    if freshness is not FreshnessStatus.DRIFTED:
        return declared
    return merge_lifecycle_signals(declared, EvidenceLifecycle.STALE)


def resolve_contract_freshness(
    suite_file: Path,
    *,
    fetcher: Fetcher = _github_json,
) -> list[FreshnessObservation]:
    raw = yaml.safe_load(suite_file.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("contracts"), list):
        raise TypeError("invalid reality contract suite")

    observations: list[FreshnessObservation] = []
    for contract in raw["contracts"]:
        contract_id = contract["id"]
        declared = EvidenceLifecycle(
            contract.get("lifecycle", EvidenceLifecycle.CURRENT.value)
        )
        manifest_path = (suite_file.parent / contract["manifest"]).resolve()
        manifest_raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        source_pr = (
            manifest_raw.get("source_pr")
            if isinstance(manifest_raw, dict)
            else None
        )
        frozen_base = contract.get("expected_base_sha") or (
            manifest_raw.get("base_sha") if isinstance(manifest_raw, dict) else None
        )
        frozen_head = contract.get("expected_head_sha") or (
            manifest_raw.get("head_sha") if isinstance(manifest_raw, dict) else None
        )

        if not source_pr or not _GITHUB_PR_RE.match(source_pr):
            freshness = FreshnessStatus.UNRESOLVED
            observations.append(
                FreshnessObservation(
                    contract_id=contract_id,
                    declared_lifecycle=declared,
                    freshness=freshness,
                    suggested_lifecycle=_suggest_lifecycle(declared, freshness),
                    source_pr=source_pr,
                    frozen_base_sha=frozen_base,
                    frozen_head_sha=frozen_head,
                    live_base_sha=None,
                    live_head_sha=None,
                    reason="no supported live GitHub PR source",
                )
            )
            continue

        try:
            live_base, live_head = _github_pr_snapshot(source_pr, fetcher)
        except (RuntimeError, ValueError) as exc:
            freshness = FreshnessStatus.UNRESOLVED
            observations.append(
                FreshnessObservation(
                    contract_id=contract_id,
                    declared_lifecycle=declared,
                    freshness=freshness,
                    suggested_lifecycle=_suggest_lifecycle(declared, freshness),
                    source_pr=source_pr,
                    frozen_base_sha=frozen_base,
                    frozen_head_sha=frozen_head,
                    live_base_sha=None,
                    live_head_sha=None,
                    reason=str(exc),
                )
            )
            continue

        drift: list[str] = []
        if frozen_base and live_base != frozen_base:
            drift.append("base")
        if frozen_head and live_head != frozen_head:
            drift.append("head")

        freshness = (
            FreshnessStatus.DRIFTED if drift else FreshnessStatus.FRESH
        )
        reason = f"live PR {'/'.join(drift)} candidate drift" if drift else None
        observations.append(
            FreshnessObservation(
                contract_id=contract_id,
                declared_lifecycle=declared,
                freshness=freshness,
                suggested_lifecycle=_suggest_lifecycle(declared, freshness),
                source_pr=source_pr,
                frozen_base_sha=frozen_base,
                frozen_head_sha=frozen_head,
                live_base_sha=live_base,
                live_head_sha=live_head,
                reason=reason,
            )
        )

    return observations
