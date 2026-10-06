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


def test_real_contract_freshness_snapshot_matches_declared_lifecycle():
    snapshots = {
        "https://api.github.com/repos/ublue-os/bluefin/pulls/4539": {
            "base": {"sha": "f2a60b9b6e62880b38b70595f035e7a6ac571bc5"},
            "head": {"sha": "42b32a75fbfb83a316bd3473e80043d551af20da"},
        },
        "https://api.github.com/repos/clash-verge-rev/clash-verge-rev/pulls/8017": {
            "base": {"sha": "dba0f471bf242875e079e8978dc6eac760e06054"},
            "head": {"sha": "2cb071998e2f14d76a5fbc3f4add5973e79cf138"},
        },
        "https://api.github.com/repos/aboutcode-org/scancode.io/pulls/2207": {
            "base": {"sha": "41868632dcaba1ad9b6402d114b169564c08d121"},
            "head": {"sha": "f71185995aee043e2e9acfd31028501f23992aea"},
        },
    }

    observations = resolve_contract_freshness(
        Path("examples/claim_matrix/reality-contracts.yml"),
        fetcher=lambda url: snapshots[url],
    )
    by_id = {item.contract_id: item for item in observations}

    bluefin = by_id["bluefin-4539-oracle-applicability"]
    assert bluefin.freshness is FreshnessStatus.FRESH
    assert bluefin.declared_lifecycle is EvidenceLifecycle.CURRENT
    assert bluefin.suggested_lifecycle is EvidenceLifecycle.CURRENT

    clash = by_id["clash-8017-candidate-bound-behavior"]
    assert clash.freshness is FreshnessStatus.DRIFTED
    assert clash.declared_lifecycle is EvidenceLifecycle.STALE
    assert clash.suggested_lifecycle is EvidenceLifecycle.STALE
    assert clash.live_base_sha == "dba0f471bf242875e079e8978dc6eac760e06054"

    scancode = by_id["scancode-2207-db-backed-behavior"]
    assert scancode.freshness is FreshnessStatus.FRESH
    assert scancode.declared_lifecycle is EvidenceLifecycle.CURRENT
    assert scancode.suggested_lifecycle is EvidenceLifecycle.CURRENT
