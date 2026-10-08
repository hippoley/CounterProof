import pytest

from skill_factory.evolution.evidence_relationship import (
    from_noa_settlement_result,
    from_windowpilot_object_observation,
    merge_relationship_envelopes,
)


def _noa(relationship):
    return {
        "observerRelationship":relationship,
        "observerRelationshipSource":"VERIFIER_DERIVED",
        "trustPolicyHash":"sha256:"+"a"*64,
        "registrySnapshotHash":"sha256:"+"b"*64,
    }


def _windowpilot():
    return {
        "schema_version":"windowpilot-object-observation/v0.1",
        "observation_id":"obs-1",
        "observation_sha256":"c"*64,
        "observer":{
            "control_domain":"window-contact-sensor",
        },
        "effecting_control_domain":"cwds-ca01-controller",
        "separation":{
            "declared_distinct_control_domains":True,
            "independence_proven":False,
        },
    }


def test_noa_same_key_maps_to_known_overlap_without_org_claim():
    envelope=from_noa_settlement_result(_noa("SAME_SIGNING_KEY"))

    assert envelope["relationship_class"]=="KNOWN_OVERLAP"
    assert envelope["facts"]["same_credential"]["state"]=="TRUE"
    assert envelope["facts"]["same_administrative_party"]["state"]=="UNKNOWN"
    assert envelope["facts"]["separate_authoring_party"]["state"]=="UNKNOWN"


def test_noa_same_admin_party_preserves_distinct_key_but_overlap():
    envelope=from_noa_settlement_result(
        _noa("SAME_ADMINISTRATIVE_PARTY")
    )

    assert envelope["facts"]["same_credential"]["state"]=="FALSE"
    assert envelope["facts"]["same_administrative_party"]["state"]=="TRUE"
    assert envelope["relationship_class"]=="KNOWN_OVERLAP"


def test_noa_unknown_stays_unknown():
    envelope=from_noa_settlement_result(_noa("UNKNOWN"))

    assert envelope["relationship_class"]=="UNKNOWN"
    assert all(
        fact["state"]=="UNKNOWN"
        for fact in envelope["facts"].values()
    )


def test_noa_rejects_self_declared_relationship():
    payload=_noa("SAME_SIGNING_KEY")
    payload["observerRelationshipSource"]="PRODUCER_ASSERTED"

    with pytest.raises(ValueError,match="VERIFIER_DERIVED"):
        from_noa_settlement_result(payload)


def test_windowpilot_distinct_domains_do_not_become_independence():
    envelope=from_windowpilot_object_observation(_windowpilot())

    assert envelope["relationship_class"]=="DECLARED_SEPARATION_ONLY"
    assert (
        envelope["facts"]["distinct_declared_control_domain"]["state"]
        =="TRUE"
    )
    assert envelope["facts"]["same_administrative_party"]["state"]=="UNKNOWN"
    assert envelope["facts"]["separate_authoring_party"]["state"]=="UNKNOWN"


def test_windowpilot_refuses_upstream_independence_claim_in_v01():
    artifact=_windowpilot()
    artifact["separation"]["independence_proven"]=True

    with pytest.raises(ValueError,match="proven independence"):
        from_windowpilot_object_observation(artifact)


def test_merge_never_upgrades_declared_separation_to_independence():
    merged=merge_relationship_envelopes(
        from_noa_settlement_result(_noa("UNKNOWN")),
        from_windowpilot_object_observation(_windowpilot()),
    )

    assert merged["relationship_class"]=="DECLARED_SEPARATION_ONLY"
    assert merged["facts"]["separate_authoring_party"]["state"]=="UNKNOWN"
    assert merged["facts"]["distinct_independence_group"]["state"]=="UNKNOWN"


def test_merge_preserves_known_overlap_over_declared_separation():
    merged=merge_relationship_envelopes(
        from_noa_settlement_result(_noa("SAME_ADMINISTRATIVE_PARTY")),
        from_windowpilot_object_observation(_windowpilot()),
    )

    assert merged["relationship_class"]=="KNOWN_OVERLAP"
    assert merged["facts"]["same_administrative_party"]["state"]=="TRUE"
