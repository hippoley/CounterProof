import json
from pathlib import Path

import pytest

from skill_factory.evolution.claimproof_basis_handoff import load_claimproof_native_export


def _export(tmp_path, **changes):
    payload = {
        "schema_version": "claimproof.basis/v0",
        "producer": {"name": "claimproof", "component": "basis"},
        "claim": {
            "id": "auth-refactor-done",
            "state": "HOLDS",
            "text": "auth refactor done",
            "recorded": "2026-10-12T00:00:00Z",
        },
        "evidence": [{"ref": "src/auth.py", "digest": "7e4f919c16b0b188", "kind": "file"}],
        "candidate": {
            "repository": "owner/repo",
            "identity": "opaque-dirty-tree-identity",
            "identity_kind": "git-commit-dirty",
        },
        "measured_at": "2026-10-12T00:01:00Z",
    }
    payload.update(changes)
    path = tmp_path / "export.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_native_claimproof_export_keeps_opaque_candidate(tmp_path):
    admitted = load_claimproof_native_export(_export(tmp_path))
    assert admitted["admission"] == "BOUND_INPUT"
    assert admitted["candidate"]["identity_kind"] == "git-commit-dirty"
    assert admitted["candidate"]["identity"] == "opaque-dirty-tree-identity"
    assert "not independent verification" in admitted["semantic_boundary"]


@pytest.mark.parametrize("state", ["REOPENED", "UNKNOWN", "RETIRED"])
def test_native_claimproof_export_never_upgrades_nonholding_states(tmp_path, state):
    claim = {"id": "x", "state": state}
    admitted = load_claimproof_native_export(_export(tmp_path, claim=claim))
    assert admitted["claim"]["state"] == state


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"schema_version": "claimproof.basis/v1"}, "schema"),
        ({"candidate": {"repository": "owner/repo"}}, "candidate.identity"),
        ({"claim": {"id": "x", "state": "VERIFIED"}}, "claim.state"),
        ({"evidence": []}, "nonempty evidence"),
        ({"evidence": [{"ref": "x", "digest": "bad", "kind": "file"}]}, "evidence.digest"),
    ],
)
def test_native_claimproof_export_fails_closed(tmp_path, changes, message):
    with pytest.raises((ValueError, TypeError), match=message):
        load_claimproof_native_export(_export(tmp_path, **changes))


def test_pinned_native_v0_fixture_validates_against_upstream_schema():
    import jsonschema

    fixture_dir = Path("examples/interop/claimproof-basis-v0")
    payload = json.loads(
        (fixture_dir / "native-export-dirty-candidate.json").read_text(encoding="utf-8")
    )
    schema = json.loads(
        (fixture_dir / "claimproof.basis.v0.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(payload, schema)


def test_pinned_native_v0_fixture_preserves_dirty_identity_and_unknown_state():
    fixture_dir = Path("examples/interop/claimproof-basis-v0")
    path = fixture_dir / "native-export-dirty-candidate.json"
    admitted = load_claimproof_native_export(path)

    assert admitted["candidate"]["identity_kind"] == "git-commit-dirty"
    assert admitted["candidate"]["identity"].endswith("+dirty.89abcdef01234567")
    assert admitted["claim"]["state"] == "UNKNOWN"
    assert admitted["evidence"][1]["digest"] == "<absent>"
