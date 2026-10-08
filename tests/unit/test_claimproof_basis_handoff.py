from pathlib import Path

import pytest

from skill_factory.evolution.claimproof_basis_handoff import (
    load_claimproof_basis_handoff,
)


FIXTURE = Path("examples/interop/claimproof-basis-v0")


def test_claimproof_basis_handoff_binds_native_store_to_candidate():
    receipt = load_claimproof_basis_handoff(FIXTURE / "handoff.json")

    assert receipt["receipt_type"] == "CLAIMPROOF_DURABLE_BASIS_INPUT"
    assert receipt["admission"] == "BOUND_INPUT"
    assert receipt["claim_count"] == 1
    assert receipt["candidate"] == {
        "repository": "owner/repo",
        "identity": "example-candidate-identity",
    }
    assert receipt["claim_basis"]["git_blob"] == (
        "a5d81663d84d6643bbb759cf52ac59a5dd14d37e"
    )
    assert receipt["producer"]["basis_source_blob"] == (
        "f22f599d8b77077bfabbc95d031f12f68a088e0a"
    )
    assert "fix verified" not in str(receipt).lower()


def test_claimproof_basis_handoff_rejects_substituted_store(tmp_path: Path):
    handoff = (FIXTURE / "handoff.json").read_text(encoding="utf-8")
    basis = (FIXTURE / "claim-basis.json").read_text(encoding="utf-8")

    (tmp_path / "handoff.json").write_text(handoff, encoding="utf-8")
    (tmp_path / "claim-basis.json").write_text(
        basis.replace("the targeted regression suite passes", "different claim"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="claim basis identity mismatch"):
        load_claimproof_basis_handoff(tmp_path / "handoff.json")


def test_claimproof_basis_handoff_requires_candidate_identity(tmp_path: Path):
    handoff = (FIXTURE / "handoff.json").read_text(encoding="utf-8")
    handoff = handoff.replace(
        '"identity": "example-candidate-identity"',
        '"identity": ""',
    )
    (tmp_path / "handoff.json").write_text(handoff, encoding="utf-8")
    (tmp_path / "claim-basis.json").write_text(
        (FIXTURE / "claim-basis.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="candidate.identity is required"):
        load_claimproof_basis_handoff(tmp_path / "handoff.json")
