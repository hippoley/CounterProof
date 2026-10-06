from datetime import datetime, timezone
from pathlib import Path

import pytest

from skill_factory.evolution.claim_matrix import EvidenceScope, OverallClaim
from skill_factory.evolution.evidence_supersession import (
    EvidenceRecord,
    EvidenceRelation,
    claim_polarity,
    resolve_evidence_relation,
)


def _record(
    *,
    id: str,
    claim_key: str = "claim",
    minute: int,
    scope: EvidenceScope = EvidenceScope.BEHAVIOR,
    overall_claim: OverallClaim = OverallClaim.PROVEN,
) -> EvidenceRecord:
    return EvidenceRecord(
        id=id,
        claim_key=claim_key,
        observed_at=datetime(2026, 10, 6, 8, minute, tzinfo=timezone.utc),
        scope=scope,
        overall_claim=overall_claim,
    )


def test_only_directional_claims_have_polarity():
    assert claim_polarity(OverallClaim.PROVEN).value == "SUPPORTS"
    assert claim_polarity(OverallClaim.CONTRADICTED).value == "CONTRADICTS"
    assert (
        claim_polarity(OverallClaim.WITNESSED_SCOPE_INSUFFICIENT).value
        == "INCONCLUSIVE"
    )


def test_newer_equal_or_stronger_same_direction_supersedes():
    old = _record(id="old", minute=1, scope=EvidenceScope.BEHAVIOR)
    new = _record(id="new", minute=2, scope=EvidenceScope.SAFETY)

    result = resolve_evidence_relation(old, new)

    assert result.relation is EvidenceRelation.SUPERSEDES


def test_newer_opposite_direction_conflicts():
    old = _record(id="old", minute=1, overall_claim=OverallClaim.PROVEN)
    new = _record(
        id="new",
        minute=2,
        overall_claim=OverallClaim.CONTRADICTED,
    )

    result = resolve_evidence_relation(old, new)

    assert result.relation is EvidenceRelation.CONFLICTS


def test_inconclusive_evidence_does_not_supersede():
    old = _record(id="old", minute=1)
    new = _record(
        id="new",
        minute=2,
        scope=EvidenceScope.SAFETY,
        overall_claim=OverallClaim.WITNESSED_SCOPE_INSUFFICIENT,
    )

    result = resolve_evidence_relation(old, new)

    assert result.relation is EvidenceRelation.PARALLEL


def test_weaker_same_direction_evidence_stays_parallel():
    old = _record(id="old", minute=1, scope=EvidenceScope.SAFETY)
    new = _record(id="new", minute=2, scope=EvidenceScope.BEHAVIOR)

    result = resolve_evidence_relation(old, new)

    assert result.relation is EvidenceRelation.PARALLEL


def test_different_claims_are_unrelated():
    old = _record(id="old", claim_key="a", minute=1)
    new = _record(id="new", claim_key="b", minute=2)

    result = resolve_evidence_relation(old, new)

    assert result.relation is EvidenceRelation.UNRELATED


def test_supersession_requires_newer_observation():
    old = _record(id="old", minute=2)
    new = _record(id="new", minute=1)

    with pytest.raises(ValueError, match="observed_at later"):
        resolve_evidence_relation(old, new)


def test_graph_marks_superseded_and_conflicting_nodes():
    from skill_factory.evolution.evidence_supersession import build_evidence_graph

    records = [
        _record(id="old-support", minute=1, overall_claim=OverallClaim.PROVEN),
        _record(
            id="middle-conflict",
            minute=2,
            overall_claim=OverallClaim.CONTRADICTED,
        ),
        _record(
            id="new-support",
            minute=3,
            scope=EvidenceScope.SAFETY,
            overall_claim=OverallClaim.PROVEN,
        ),
    ]

    graph = build_evidence_graph(records)
    relations = {
        (item.old_id, item.new_id): item.relation
        for item in graph.relations
    }

    assert (
        relations[("old-support", "middle-conflict")]
        is EvidenceRelation.CONFLICTS
    )
    assert (
        relations[("old-support", "new-support")]
        is EvidenceRelation.SUPERSEDES
    )
    assert (
        relations[("middle-conflict", "new-support")]
        is EvidenceRelation.CONFLICTS
    )
    assert (
        graph.lifecycle_suggestions["old-support"].value
        == "SUPERSEDED"
    )
    assert (
        graph.lifecycle_suggestions["middle-conflict"].value
        == "CONFLICTING"
    )
    assert graph.lifecycle_suggestions["new-support"].value == "CONFLICTING"


def test_load_evidence_graph_and_cli(tmp_path: Path):
    from click.testing import CliRunner

    from skill_factory.evolution.cli import cli
    from skill_factory.evolution.evidence_supersession import load_evidence_graph

    path = tmp_path / "graph.yml"
    path.write_text(
        """
schema_version: 1
evidence:
  - id: old
    claim_key: repo#1:behavior
    observed_at: 2026-10-06T08:01:00+00:00
    scope: BEHAVIOR
    overall_claim: PROVEN
  - id: new
    claim_key: repo#1:behavior
    observed_at: 2026-10-06T08:02:00+00:00
    scope: SAFETY
    overall_claim: PROVEN
""".strip()
        + "\n",
        encoding="utf-8",
    )

    graph = load_evidence_graph(path)
    assert graph.relations[0].relation is EvidenceRelation.SUPERSEDES
    assert graph.lifecycle_suggestions["old"].value == "SUPERSEDED"

    result = CliRunner().invoke(cli, ["evidence-graph", str(path)])
    assert result.exit_code == 0, result.output
    assert "old -> new: SUPERSEDES" in result.output
    assert "old: SUPERSEDED" in result.output


def test_graph_rejects_duplicate_ids():
    from skill_factory.evolution.evidence_supersession import build_evidence_graph

    records = [
        _record(id="duplicate", minute=1),
        _record(id="duplicate", minute=2),
    ]

    with pytest.raises(ValueError, match="ids must be unique"):
        build_evidence_graph(records)
