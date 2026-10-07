from pathlib import Path

import yaml


LEDGER = Path("examples/claim_matrix/external-evidence-ledger.yml")


def test_external_evidence_ledger_preserves_recognition_boundaries():
    value = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    records = {item["id"]: item for item in value["records"]}

    avera = records["avera-first-consumer"]
    assert avera["status"] == "THIRD_PARTY_NAMED_ROLE"
    assert avera["durable_value"] == {
        "external_naming": True,
        "producer_owned_artifact": True,
        "executable_interop": True,
    }
    assert "adoption" not in avera["status"].lower()
    assert any(
        source.get("git_blob_sha") == "9b54097e0933363b9a8113fce07821d131825ec3"
        for source in avera["external_sources"]
    )

    execsurface = records["execsurface-zero-assistance-trial"]
    assert execsurface["status"] == "EXTERNAL_EVIDENCE_SUBMITTED_QUALIFICATION_PENDING"
    assert execsurface["durable_value"]["externally_owned_intake"] is True
    assert execsurface["durable_value"]["preserved_first_result"] is True
    assert execsurface["durable_value"]["qualification_complete"] is False
    assert execsurface["observed_result"]["status"] == "TRIAL_CAPTURE_COMPLETE_UNQUALIFIED"
    assert "qualified external evidence" in execsurface["non_claims"]
