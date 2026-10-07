from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

_PR_RE = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/pull/(\d+)$")
_ISSUE_RE = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/issues/(\d+)$")
_REPO_RE = re.compile(r"^https://github\.com/([^/]+)/([^/]+)$")


@dataclass(frozen=True)
class ExternalStateDrift:
    observation_id: str
    source_url: str
    field: str
    expected: Any
    observed: Any


def _github_json(url: str) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "CounterProof-External-State-Freshness",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"external-state probe failed for {url}: {exc}") from exc


def _record(
    drifts: list[ExternalStateDrift],
    *,
    observation_id: str,
    source_url: str,
    field: str,
    expected: Any,
    observed: Any,
) -> None:
    if expected != observed:
        drifts.append(
            ExternalStateDrift(
                observation_id=observation_id,
                source_url=source_url,
                field=field,
                expected=expected,
                observed=observed,
            )
        )


def resolve_external_state_drift(
    state_file: Path,
    *,
    fetcher=_github_json,
) -> list[ExternalStateDrift]:
    raw = yaml.safe_load(state_file.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("observations"), list):
        raise TypeError("invalid external-state manifest")

    drifts: list[ExternalStateDrift] = []
    for observation in raw["observations"]:
        observation_id = observation["id"]
        for source in observation.get("sources", []):
            url = source["url"]
            kind = source["kind"]

            if kind == "pull_request":
                match = _PR_RE.match(url)
                if not match:
                    raise ValueError(f"unsupported pull request URL: {url}")
                api = (
                    f"https://api.github.com/repos/{match.group(1)}/{match.group(2)}"
                    f"/pulls/{match.group(3)}"
                )
                payload = fetcher(api)
                if "state" in source:
                    _record(
                        drifts,
                        observation_id=observation_id,
                        source_url=url,
                        field="state",
                        expected=source["state"],
                        observed=payload.get("state"),
                    )
                if "merged" in source:
                    _record(
                        drifts,
                        observation_id=observation_id,
                        source_url=url,
                        field="merged",
                        expected=source["merged"],
                        observed=bool(payload.get("merged_at")),
                    )
                if "head_sha" in source:
                    _record(
                        drifts,
                        observation_id=observation_id,
                        source_url=url,
                        field="head_sha",
                        expected=source["head_sha"],
                        observed=(payload.get("head") or {}).get("sha"),
                    )
                continue

            if kind == "issue":
                match = _ISSUE_RE.match(url)
                if not match:
                    raise ValueError(f"unsupported issue URL: {url}")
                api = (
                    f"https://api.github.com/repos/{match.group(1)}/{match.group(2)}"
                    f"/issues/{match.group(3)}"
                )
                payload = fetcher(api)
                for field in ("state", "updated_at"):
                    if field in source:
                        _record(
                            drifts,
                            observation_id=observation_id,
                            source_url=url,
                            field=field,
                            expected=source[field],
                            observed=payload.get(field),
                        )
                continue

            if kind == "repository_file":
                match = _REPO_RE.match(url)
                if not match:
                    raise ValueError(f"unsupported repository URL: {url}")
                path = source.get("path")
                if not path:
                    raise ValueError(f"repository_file source missing path: {url}")
                api = (
                    f"https://api.github.com/repos/{match.group(1)}/{match.group(2)}"
                    f"/contents/{path}"
                )
                payload = fetcher(api)
                _record(
                    drifts,
                    observation_id=observation_id,
                    source_url=url,
                    field="blob_sha",
                    expected=source["blob_sha"],
                    observed=payload.get("sha"),
                )
                continue

            raise ValueError(f"unsupported external-state source kind: {kind}")

    return drifts
