import json
from pathlib import Path

from skill_factory.evolution.measurement_capsule_verify import recompute_batch_merkle_root


FIXTURE=Path("examples/interop/csoai-claim-watch-leaves-2026-10-01.json")


def test_replay_real_csoai_claim_watch_merkle_root_from_public_leaf():
    payload=json.loads(FIXTURE.read_text(encoding="utf-8"))

    result=recompute_batch_merkle_root(payload["leaves"])

    assert result.n_capsules==payload["n"]
    assert result.merkle_root==payload["expected_merkle_root"]


def test_real_leaf_replay_fixture_does_not_claim_capsule_byte_reproduction():
    payload=json.loads(FIXTURE.read_text(encoding="utf-8"))
    boundary=" ".join(payload["claim_boundary"]).lower()

    assert "does not prove" in boundary
    assert "capsule bytes" in boundary
