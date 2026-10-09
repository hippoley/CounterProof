import hashlib

import pytest
import rfc8785

from skill_factory.evolution.measurement_capsule_verify import (
    AUTHORITY_NONE,
    MeasurementCapsuleError,
    recompute_batch_merkle_root,
    recompute_capsule_id,
    verify_capsule,
    verify_jsonl_batch,
)


def _capsule(subject, state="MEASURED"):
    capsule={
        "schema":"csoai.measurement-capsule/0.2",
        "kind":"measurement.public_signal",
        "subject_id":subject,
        "claim":{"statement":"published value equals observed value"},
        "declared":{"value":"1"},
        "observed":{"value":"1"},
        "differential":{"equal":True},
        "sources":{"declared_sha256":"a"*64,"observed_sha256":"b"*64},
        "measurement_state":state,
        "authority_state":AUTHORITY_NONE,
        "effect_reference":None,
        "observed_at":"2026-10-08T00:00:00Z",
        "correction_pointer":None,
        "limitations":["synthetic draft-level verifier test only"],
        "capsule_id":"",
    }
    capsule["capsule_id"]=recompute_capsule_id(capsule)
    return capsule


def test_capsule_id_uses_rfc8785_with_capsule_id_excluded():
    capsule=_capsule("example:one")
    without=dict(capsule)
    without.pop("capsule_id")
    expected=hashlib.sha256(rfc8785.dumps(without)).hexdigest()

    assert capsule["capsule_id"]==expected
    assert verify_capsule(capsule).capsule_id==expected


def test_exact_jcs_line_is_required_when_stored_line_is_supplied():
    capsule=_capsule("example:one")
    canonical=rfc8785.dumps(capsule)+b"\n"

    assert verify_capsule(capsule,stored_line=canonical).stored_line_matches_jcs

    pretty=(__import__("json").dumps(capsule,indent=2)+"\n").encode()
    with pytest.raises(MeasurementCapsuleError,match="exact JCS"):
        verify_capsule(capsule,stored_line=pretty)


def test_unc_checkable_is_preserved_as_measurement_state():
    capsule=_capsule("example:one",state="UNCHECKABLE")

    result=verify_capsule(capsule)

    assert result.capsule_id==capsule["capsule_id"]


def test_decision_like_member_is_rejected():
    capsule=_capsule("example:one")
    capsule["declared"]["approval"]="APPROVED"
    capsule["capsule_id"]=recompute_capsule_id(capsule)

    with pytest.raises(MeasurementCapsuleError,match="forbidden"):
        verify_capsule(capsule)


def test_sources_must_be_digests_not_urls_or_free_text():
    capsule=_capsule("example:one")
    capsule["sources"]["source"]="https://example.com/raw-evidence"
    capsule["capsule_id"]=recompute_capsule_id(capsule)

    with pytest.raises(MeasurementCapsuleError,match="non-digest"):
        verify_capsule(capsule)


def test_rfc9162_single_leaf_root_has_leaf_domain_separator():
    leaf="11"*32
    expected=hashlib.sha256(b"\x00"+bytes.fromhex(leaf)).hexdigest()

    assert recompute_batch_merkle_root([leaf]).merkle_root==expected


def test_rfc9162_two_leaf_root_has_node_domain_separator():
    first="11"*32
    second="22"*32
    left=hashlib.sha256(b"\x00"+bytes.fromhex(first)).digest()
    right=hashlib.sha256(b"\x00"+bytes.fromhex(second)).digest()
    expected=hashlib.sha256(b"\x01"+left+right).hexdigest()

    assert recompute_batch_merkle_root([second,first]).merkle_root==expected


def test_duplicate_capsule_ids_are_rejected():
    leaf="11"*32

    with pytest.raises(MeasurementCapsuleError,match="duplicate"):
        recompute_batch_merkle_root([leaf,leaf])


def test_jsonl_batch_requires_sorted_canonical_lines_and_expected_root():
    first=_capsule("example:a")
    second=_capsule("example:b")
    capsules=sorted([first,second],key=lambda item:item["capsule_id"])
    lines=[rfc8785.dumps(item)+b"\n" for item in capsules]
    expected=recompute_batch_merkle_root(
        [item["capsule_id"] for item in capsules]
    )

    result=verify_jsonl_batch(
        lines,
        expected_merkle_root=expected.merkle_root,
        expected_n_capsules=2,
    )

    assert result==expected


def test_jsonl_batch_rejects_unsorted_capsules():
    first=_capsule("example:a")
    second=_capsule("example:b")
    capsules=sorted(
        [first,second],
        key=lambda item:item["capsule_id"],
        reverse=True,
    )
    lines=[rfc8785.dumps(item)+b"\n" for item in capsules]

    with pytest.raises(MeasurementCapsuleError,match="strictly sorted"):
        verify_jsonl_batch(lines)
