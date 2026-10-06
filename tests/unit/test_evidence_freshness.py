from pathlib import Path

from skill_factory.evolution.evidence_freshness import (
    FreshnessStatus,
    resolve_contract_freshness,
)
from skill_factory.evolution.evidence_lifecycle import EvidenceLifecycle


def _write_suite(tmp_path: Path, *, lifecycle: str = "CURRENT") -> Path:
    (tmp_path / "claims.yml").write_text(
        """
schema_version: 1
title: Freshness
source_pr: https://github.com/example/repo/pull/7
base_sha: frozen-base
head_sha: frozen-head
claims:
  - id: behavior
    claim: behavior
    submitted_test_evidence: UNPROVEN
""".strip()
        + "\n",
        encoding="utf-8",
    )
    suite = tmp_path / "contracts.yml"
    suite.write_text(
        f"""
schema_version: 1
contracts:
  - id: example
    lifecycle: {lifecycle}
    manifest: claims.yml
    expectations: []
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return suite


def test_freshness_resolver_keeps_matching_candidate_current(tmp_path: Path):
    suite = _write_suite(tmp_path)

    observations = resolve_contract_freshness(
        suite,
        fetcher=lambda _: {
            "base": {"sha": "frozen-base"},
            "head": {"sha": "frozen-head"},
        },
    )

    observation = observations[0]
    assert observation.freshness is FreshnessStatus.FRESH
    assert observation.suggested_lifecycle is EvidenceLifecycle.CURRENT
    assert observation.reason is None


def test_freshness_resolver_marks_current_candidate_drift_stale(tmp_path: Path):
    suite = _write_suite(tmp_path)

    observations = resolve_contract_freshness(
        suite,
        fetcher=lambda _: {
            "base": {"sha": "live-base"},
            "head": {"sha": "frozen-head"},
        },
    )

    observation = observations[0]
    assert observation.freshness is FreshnessStatus.DRIFTED
    assert observation.suggested_lifecycle is EvidenceLifecycle.STALE
    assert observation.reason == "live PR base candidate drift"


def test_freshness_resolver_does_not_downgrade_network_failure(tmp_path: Path):
    suite = _write_suite(tmp_path)

    def fail(_: str):
        raise RuntimeError("network unavailable")

    observation = resolve_contract_freshness(suite, fetcher=fail)[0]

    assert observation.freshness is FreshnessStatus.UNRESOLVED
    assert observation.suggested_lifecycle is EvidenceLifecycle.CURRENT
    assert observation.reason == "network unavailable"


def test_freshness_resolver_preserves_stronger_lifecycle_on_drift(tmp_path: Path):
    suite = _write_suite(tmp_path, lifecycle="SUPERSEDED")

    observation = resolve_contract_freshness(
        suite,
        fetcher=lambda _: {
            "base": {"sha": "live-base"},
            "head": {"sha": "live-head"},
        },
    )[0]

    assert observation.freshness is FreshnessStatus.DRIFTED
    assert observation.suggested_lifecycle is EvidenceLifecycle.SUPERSEDED
