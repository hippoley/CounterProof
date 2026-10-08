import json
from pathlib import Path

from skill_factory.evolution.evidence_relationship import (
    from_noa_settlement_result,
)


PIN=Path("examples/interop/noa-observer-relationship-pin-v0.1.json")


def _result(case):
    return {
        "observerRelationship":case["observerRelationship"],
        "observerRelationshipSource":case["observerRelationshipSource"],
        "trustPolicyHash":"sha256:"+"a"*64,
        "registrySnapshotHash":"sha256:"+"b"*64,
    }


def test_pinned_noa_relationship_semantics_remain_conservatively_consumable():
    payload=json.loads(PIN.read_text(encoding="utf-8"))

    assert payload["upstream"]["repository"]=="NordenSoft/noa-mandate-core"
    assert len(payload["upstream"]["commit"])==40

    for case in payload["cases"]:
        envelope=from_noa_settlement_result(_result(case))

        assert envelope["relationship_class"]==case["expected_relationship_class"]
        assert (
            envelope["facts"]["same_credential"]["state"]
            ==case["expected_same_credential"]
        )
        assert (
            envelope["facts"]["same_administrative_party"]["state"]
            ==case["expected_same_administrative_party"]
        )


def test_noa_pin_contains_no_independent_positive_class():
    payload=json.loads(PIN.read_text(encoding="utf-8"))

    assert all(
        case["expected_relationship_class"]!="INDEPENDENT"
        for case in payload["cases"]
    )
