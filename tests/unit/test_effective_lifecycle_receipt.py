import json
from pathlib import Path

from click.testing import CliRunner

from skill_factory.evolution import cli as cli_module
from skill_factory.evolution.effective_lifecycle import EffectiveLifecycleObservation
from skill_factory.evolution.evidence_lifecycle import EvidenceLifecycle


def test_reality_lifecycle_writes_pass_receipt(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        cli_module,
        "resolve_effective_contract_lifecycles",
        lambda *args, **kwargs: [
            EffectiveLifecycleObservation(
                contract_id="example",
                evidence_id=None,
                declared=EvidenceLifecycle.CURRENT,
                freshness_signal=None,
                graph_signal=None,
                effective=EvidenceLifecycle.CURRENT,
                freshness_reason=None,
            )
        ],
    )
    suite = tmp_path / "suite.yml"
    suite.write_text("schema_version: 1\ncontracts: []\n", encoding="utf-8")
    output = tmp_path / "lifecycle.json"

    result = CliRunner().invoke(
        cli_module.cli,
        ["reality-lifecycle", str(suite), "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 2
    assert payload["status"] == "PASS"
    assert payload["mismatch_count"] == 0
    assert payload["observations"][0]["effective"] == "CURRENT"
    assert payload["inputs"]["suite_git_blob_sha"]
    assert payload["execution"]["git_sha"] is None


def test_reality_lifecycle_writes_receipt_before_mismatch_failure(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        cli_module,
        "resolve_effective_contract_lifecycles",
        lambda *args, **kwargs: [
            EffectiveLifecycleObservation(
                contract_id="drifted",
                evidence_id="evidence-1",
                declared=EvidenceLifecycle.CURRENT,
                freshness_signal=EvidenceLifecycle.STALE,
                graph_signal=EvidenceLifecycle.SUPERSEDED,
                effective=EvidenceLifecycle.SUPERSEDED,
                freshness_reason="live PR base candidate drift",
            )
        ],
    )
    suite = tmp_path / "suite.yml"
    suite.write_text("schema_version: 1\ncontracts: []\n", encoding="utf-8")
    output = tmp_path / "lifecycle.json"

    result = CliRunner().invoke(
        cli_module.cli,
        ["reality-lifecycle", str(suite), "--output", str(output)],
    )

    assert result.exit_code != 0
    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "UPDATE_REQUIRED"
    assert payload["mismatch_count"] == 1
    assert payload["observations"][0]["declared"] == "CURRENT"
    assert payload["observations"][0]["freshness_signal"] == "STALE"
    assert payload["observations"][0]["graph_signal"] == "SUPERSEDED"
    assert payload["observations"][0]["effective"] == "SUPERSEDED"
    assert payload["observations"][0]["freshness"]["reason"] == (
        "live PR base candidate drift"
    )
