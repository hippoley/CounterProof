import json
from pathlib import Path

RECEIPT = (
    Path(__file__).resolve().parents[2]
    / "examples"
    / "claim_matrix"
    / "receipts"
    / "bluefin-4539-flagship-causal.json"
)


def test_frozen_bluefin_flagship_receipt_preserves_source_run_and_oracle_identity():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema_version"] == 2
    assert receipt["receipt_type"] == "FLAGSHIP_CONTROLLED_CAUSAL"
    assert receipt["case"] == "ublue-os/bluefin#4539"
    assert receipt["verdict"] == "WITNESSED_CONTROLLED_CAUSAL"

    assert receipt["source_run"]["workflow_run"] == 37412091382
    assert receipt["source_run"]["workflow_head_sha"] == (
        "8b422a2334a093185bf91e6783e454077eb7cffa"
    )
    assert receipt["oracle_identity"]["test_revision"] == (
        "1c0a23317d420b77396770ae2a8fdf71804cde4e"
    )
    assert receipt["oracle_identity"]["upstream_workflow_revision"] == (
        "a99ca5ea0553f778a74f5d5152fefbbb47d86da4"
    )
    assert receipt["experiment"]["same_oracle_for_all_candidates"] is True



def test_frozen_bluefin_flagship_receipt_preserves_y_yprime_y_signature():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    candidates = receipt["candidates"]

    assert (
        candidates["CONTROL"]["keyring_unit_active"],
        candidates["CONTROL"]["portal_wants_keyring"],
        candidates["CONTROL"]["not_in_initialization"],
    ) == (False, False, False)

    assert (
        candidates["BAD"]["keyring_unit_active"],
        candidates["BAD"]["portal_wants_keyring"],
        candidates["BAD"]["not_in_initialization"],
    ) == (True, True, True)

    assert (
        candidates["REVERT"]["keyring_unit_active"],
        candidates["REVERT"]["portal_wants_keyring"],
        candidates["REVERT"]["not_in_initialization"],
    ) == (False, False, False)

    assert receipt["causal_conclusion"]["pattern"] == (
        "CONTROL_BASELINE -> BAD_DIVERGENCE -> REVERT_RECOVERY"
    )
    assert receipt["causal_conclusion"]["scope"] == "CONTROLLED_CAUSAL"



def test_frozen_bluefin_flagship_receipt_does_not_overclaim_historical_replay():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert receipt["experiment"]["historical_image_status"] == (
        "ORIGINAL_REGISTRY_ARTIFACTS_UNAVAILABLE"
    )
    limitations = receipt["causal_conclusion"]["does_not_claim"]
    assert any("exact replay" in item for item in limitations)
    assert any("user-visible symptom" in item for item in limitations)
