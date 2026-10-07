import pytest

from skill_factory.evolution.evidence_lifecycle import (
    EvidenceLifecycle,
    merge_lifecycle_signals,
    resolve_effective_lifecycle,
    validate_lifecycle_transition,
)


@pytest.mark.parametrize(
    ("previous", "current"),
    [
        (EvidenceLifecycle.CURRENT, EvidenceLifecycle.CURRENT),
        (EvidenceLifecycle.CURRENT, EvidenceLifecycle.STALE),
        (EvidenceLifecycle.CURRENT, EvidenceLifecycle.CONFLICTING),
        (EvidenceLifecycle.CURRENT, EvidenceLifecycle.SUPERSEDED),
        (EvidenceLifecycle.STALE, EvidenceLifecycle.SUPERSEDED),
        (EvidenceLifecycle.CONFLICTING, EvidenceLifecycle.SUPERSEDED),
        (EvidenceLifecycle.SUPERSEDED, EvidenceLifecycle.SUPERSEDED),
    ],
)
def test_allowed_lifecycle_transitions(previous, current):
    validate_lifecycle_transition(previous, current)


@pytest.mark.parametrize(
    ("previous", "current"),
    [
        (EvidenceLifecycle.SUPERSEDED, EvidenceLifecycle.CURRENT),
        (EvidenceLifecycle.SUPERSEDED, EvidenceLifecycle.STALE),
        (EvidenceLifecycle.STALE, EvidenceLifecycle.CURRENT),
        (EvidenceLifecycle.CONFLICTING, EvidenceLifecycle.CURRENT),
    ],
)
def test_lifecycle_does_not_silently_move_backwards(previous, current):
    with pytest.raises(ValueError, match="invalid evidence lifecycle transition"):
        validate_lifecycle_transition(previous, current)


@pytest.mark.parametrize(
    ("signals", "expected"),
    [
        ((EvidenceLifecycle.CURRENT, EvidenceLifecycle.STALE), EvidenceLifecycle.STALE),
        (
            (EvidenceLifecycle.STALE, EvidenceLifecycle.CONFLICTING),
            EvidenceLifecycle.CONFLICTING,
        ),
        (
            (EvidenceLifecycle.CONFLICTING, EvidenceLifecycle.SUPERSEDED),
            EvidenceLifecycle.SUPERSEDED,
        ),
        (
            (
                EvidenceLifecycle.CURRENT,
                EvidenceLifecycle.STALE,
                EvidenceLifecycle.CONFLICTING,
                EvidenceLifecycle.SUPERSEDED,
            ),
            EvidenceLifecycle.SUPERSEDED,
        ),
    ],
)
def test_lifecycle_signal_precedence(signals, expected):
    assert merge_lifecycle_signals(*signals) is expected


def test_lifecycle_signal_merge_requires_input():
    with pytest.raises(ValueError, match="at least one"):
        merge_lifecycle_signals()


def test_effective_lifecycle_merges_declared_freshness_and_graph():
    assert (
        resolve_effective_lifecycle(
            EvidenceLifecycle.CURRENT,
            freshness_signal=EvidenceLifecycle.STALE,
            graph_signal=EvidenceLifecycle.SUPERSEDED,
        )
        is EvidenceLifecycle.SUPERSEDED
    )


def test_effective_lifecycle_preserves_conflict_when_freshness_unresolved():
    assert (
        resolve_effective_lifecycle(
            EvidenceLifecycle.STALE,
            graph_signal=EvidenceLifecycle.CONFLICTING,
        )
        is EvidenceLifecycle.CONFLICTING
    )


def test_effective_lifecycle_report_merges_graph_signal(tmp_path):
    from skill_factory.evolution.effective_lifecycle import (
        resolve_effective_contract_lifecycles,
    )
    from skill_factory.evolution.evidence_freshness import (
        FreshnessObservation,
        FreshnessStatus,
    )

    (tmp_path / "claims.yml").write_text(
        """
schema_version: 1
title: Effective lifecycle
source_pr: https://github.com/example/repo/pull/1
claims:
  - id: behavior
    claim: behavior
    tests:
      - exact behavior test
    base_result: FAIL
    head_result: PASS
    submitted_test_evidence: WITNESSED
    evidence_scope: BEHAVIOR
    required_scope: BEHAVIOR
    oracle_applicability: APPLICABLE
    oracle_alignment: ALIGNED
    oracle_probe: authoritative behavior oracle
    oracle_source_url: https://oracle-source.example.test/test-evidence
    oracle_source_url: https://oracle-source.example.test/evidence-lifecycle
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "suite.yml").write_text(
        """
schema_version: 1
contracts:
  - id: example
    lifecycle: CURRENT
    evidence_id: old
    manifest: claims.yml
    expectations: []
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "graph.yml").write_text(
        """
schema_version: 1
evidence:
  - id: old
    claim_key: example:behavior
    observed_at: 2026-10-06T08:01:00+00:00
    scope: BEHAVIOR
    overall_claim: PROVEN
  - id: new
    claim_key: example:behavior
    observed_at: 2026-10-06T08:02:00+00:00
    scope: SAFETY
    overall_claim: PROVEN
""".strip()
        + "\n",
        encoding="utf-8",
    )
    freshness = [
        FreshnessObservation(
            contract_id="example",
            declared_lifecycle=EvidenceLifecycle.CURRENT,
            freshness=FreshnessStatus.DRIFTED,
            suggested_lifecycle=EvidenceLifecycle.STALE,
            source_pr="https://github.com/example/repo/pull/1",
            frozen_base_sha="base",
            frozen_head_sha="head",
            live_base_sha="new-base",
            live_head_sha="head",
            reason="live PR base candidate drift",
        )
    ]

    observed = resolve_effective_contract_lifecycles(
        tmp_path / "suite.yml",
        graph_file=tmp_path / "graph.yml",
        freshness_observations=freshness,
    )[0]

    assert observed.freshness_signal is EvidenceLifecycle.STALE
    assert observed.graph_signal is EvidenceLifecycle.SUPERSEDED
    assert observed.effective is EvidenceLifecycle.SUPERSEDED
