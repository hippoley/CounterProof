import json
from pathlib import Path

import pytest

from skill_factory.evolution.causal_replay import (
    build_causal_replay_receipt,
    verify_causal_replay_receipt,
)


def _write_evidence(
    path: Path,
    *,
    identity: str,
    failed: bool,
    count: int,
) -> None:
    path.write_text(
        json.dumps(
            {
                "candidate": identity,
                "snapshot": {
                    "failed": failed,
                    "count": count,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_manifest(tmp_path: Path) -> Path:
    _write_evidence(
        tmp_path / "control.json",
        identity="control-sha",
        failed=False,
        count=0,
    )
    _write_evidence(
        tmp_path / "bad.json",
        identity="bad-sha",
        failed=True,
        count=3,
    )
    _write_evidence(
        tmp_path / "revert.json",
        identity="revert-sha",
        failed=False,
        count=0,
    )
    manifest = tmp_path / "causal.yml"
    manifest.write_text(
        """
schema_version: 1
case: example/repo#123
experiment: CONTROL -> BAD -> REVERT
oracle:
  id: example-runtime-oracle
  revision: oracle-sha
identity_path: candidate
observation_root: snapshot
candidates:
  CONTROL:
    identity: control-sha
    evidence: control.json
  BAD:
    identity: bad-sha
    evidence: bad.json
  REVERT:
    identity: revert-sha
    evidence: revert.json
expectations:
  - path: failed
    CONTROL: false
    BAD: true
    REVERT: false
  - path: count
    CONTROL: 0
    BAD: 3
    REVERT: 0
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return manifest


def test_causal_replay_witnesses_control_bad_revert_pattern(tmp_path: Path):
    manifest = _write_manifest(tmp_path)

    receipt = build_causal_replay_receipt(manifest)

    assert receipt["verdict"] == "WITNESSED_CAUSAL_REPLAY"
    assert receipt["causal_expectation_count"] == 2
    assert receipt["candidates"]["CONTROL"]["identity"] == "control-sha"
    assert receipt["candidates"]["BAD"]["evidence"]["sha256"]
    assert receipt["expectations"][0]["observed"] == {
        "CONTROL": False,
        "BAD": True,
        "REVERT": False,
    }


def test_causal_replay_is_inconclusive_when_revert_does_not_recover(tmp_path: Path):
    manifest = _write_manifest(tmp_path)
    _write_evidence(
        tmp_path / "revert.json",
        identity="revert-sha",
        failed=True,
        count=3,
    )

    receipt = build_causal_replay_receipt(manifest)

    assert receipt["verdict"] == "INCONCLUSIVE_CAUSAL_REPLAY"
    assert receipt["expectations"][0]["match"] is False


def test_causal_replay_requires_distinct_candidate_identities(tmp_path: Path):
    manifest = _write_manifest(tmp_path)
    text = manifest.read_text(encoding="utf-8").replace(
        "identity: revert-sha",
        "identity: control-sha",
    ).replace(
        "candidate: revert-sha",
        "candidate: control-sha",
    )
    manifest.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="identities must be distinct"):
        build_causal_replay_receipt(manifest)


def test_causal_replay_requires_a_real_intervention_signature(tmp_path: Path):
    manifest = _write_manifest(tmp_path)
    text = manifest.read_text(encoding="utf-8")
    text = text.replace("BAD: true", "BAD: false")
    text = text.replace("BAD: 3", "BAD: 0")
    manifest.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="CONTROL == REVERT != BAD"):
        build_causal_replay_receipt(manifest)


def test_causal_replay_rejects_evidence_path_escape(tmp_path: Path):
    suite = tmp_path / "suite"
    suite.mkdir()
    outside = tmp_path / "outside.json"
    _write_evidence(outside, identity="control-sha", failed=False, count=0)
    manifest = _write_manifest(suite)
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "evidence: control.json",
            "evidence: ../outside.json",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must stay within the causal replay directory"):
        build_causal_replay_receipt(manifest)


def test_causal_replay_rejects_evidence_identity_mismatch(tmp_path: Path):
    manifest = _write_manifest(tmp_path)
    _write_evidence(
        tmp_path / "bad.json",
        identity="different-bad",
        failed=True,
        count=3,
    )

    with pytest.raises(ValueError, match="candidate BAD identity expected"):
        build_causal_replay_receipt(manifest)


def test_causal_replay_verifier_rejects_evidence_tamper(tmp_path: Path):
    manifest = _write_manifest(tmp_path)
    receipt = build_causal_replay_receipt(manifest)

    payload = json.loads((tmp_path / "bad.json").read_text(encoding="utf-8"))
    payload["note"] = "artifact changed without changing observed oracle fields"
    (tmp_path / "bad.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    failures = verify_causal_replay_receipt(
        receipt,
        manifest_file=manifest,
    )

    assert any("candidate BAD evidence identity" in item for item in failures)


def test_causal_replay_verifier_accepts_deterministic_rebuild(tmp_path: Path):
    manifest = _write_manifest(tmp_path)
    receipt = build_causal_replay_receipt(manifest)

    assert verify_causal_replay_receipt(
        receipt,
        manifest_file=manifest,
    ) == []
