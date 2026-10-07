from pathlib import Path

from skill_factory.evolution.external_state_freshness import resolve_external_state_drift


def test_external_state_freshness_detects_pr_issue_and_file_drift(tmp_path: Path):
    state = tmp_path / "external-state.yml"
    state.write_text(
        """
schema_version: 1
observations:
  - id: demo
    sources:
      - url: https://github.com/acme/spec/pull/7
        kind: pull_request
        state: open
        merged: false
        head_sha: old
      - url: https://github.com/acme/spec/issues/9
        kind: issue
        state: open
        updated_at: "2026-10-01T00:00:00Z"
      - url: https://github.com/acme/corpus
        kind: repository_file
        path: MANIFEST.json
        blob_sha: blob-old
""",
        encoding="utf-8",
    )

    def fetcher(url: str):
        if "/pulls/7" in url:
            return {"state": "open", "merged_at": None, "head": {"sha": "new"}}
        if "/issues/9" in url:
            return {"state": "open", "updated_at": "2026-10-02T00:00:00Z"}
        return {"sha": "blob-new"}

    drifts = resolve_external_state_drift(state, fetcher=fetcher)

    assert [(item.field, item.expected, item.observed) for item in drifts] == [
        ("head_sha", "old", "new"),
        ("updated_at", "2026-10-01T00:00:00Z", "2026-10-02T00:00:00Z"),
        ("blob_sha", "blob-old", "blob-new"),
    ]


def test_external_state_freshness_accepts_unchanged_sources(tmp_path: Path):
    state = tmp_path / "external-state.yml"
    state.write_text(
        """
schema_version: 1
observations:
  - id: demo
    sources:
      - url: https://github.com/acme/spec/pull/7
        kind: pull_request
        state: open
        merged: false
        head_sha: same
""",
        encoding="utf-8",
    )

    drifts = resolve_external_state_drift(
        state,
        fetcher=lambda _: {
            "state": "open",
            "merged_at": None,
            "head": {"sha": "same"},
        },
    )

    assert drifts == []
