"""Conservative interoperability envelope for evidence-source relationships.

The purpose of this module is not to decide that two sources are "independent".
It normalizes relationship facts already established by upstream verifiers while
preserving provenance and assurance ceilings.

No adapter is allowed to upgrade a weaker upstream statement into a stronger
cross-system claim.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


_SCHEMA="counterproof.evidence-relationship/v0.1"
_TRI={"TRUE","FALSE","UNKNOWN"}


def _fact(value: str, *, source: str, basis: str) -> dict[str, str]:
    if value not in _TRI:
        raise ValueError(f"unsupported relationship fact state: {value}")
    return {"state":value,"source":source,"basis":basis}


def _base(*, upstream: str, artifact_type: str) -> dict[str, Any]:
    return {
        "schema_version":_SCHEMA,
        "upstream":{
            "system":upstream,
            "artifact_type":artifact_type,
        },
        "facts":{
            "same_credential":_fact("UNKNOWN",source=upstream,basis="not-evaluated"),
            "same_administrative_party":_fact("UNKNOWN",source=upstream,basis="not-evaluated"),
            "distinct_declared_control_domain":_fact("UNKNOWN",source=upstream,basis="not-evaluated"),
            "separate_binary":_fact("UNKNOWN",source=upstream,basis="not-evaluated"),
            "separate_codegen":_fact("UNKNOWN",source=upstream,basis="not-evaluated"),
            "separate_transport":_fact("UNKNOWN",source=upstream,basis="not-evaluated"),
            "separate_authoring_party":_fact("UNKNOWN",source=upstream,basis="not-evaluated"),
            "distinct_independence_group":_fact("UNKNOWN",source=upstream,basis="not-evaluated"),
        },
        "relationship_class":"UNKNOWN",
        "trust_context":{},
        "non_claims":[
            "This envelope does not establish organizational independence.",
            "Different keys, binaries, transports, or labels do not by themselves establish independent failure domains.",
            "Unknown facts remain unknown and must not be upgraded by consumers.",
        ],
    }


def from_noa_settlement_result(result: dict[str, Any]) -> dict[str, Any]:
    """Normalize NOA's verifier-derived settlement observer relationship.

    Supported upstream values are intentionally closed to the public NOA
    settlement-evidence contract:
    SAME_SIGNING_KEY, SAME_ADMINISTRATIVE_PARTY, UNKNOWN.
    """
    if not isinstance(result,dict):
        raise ValueError("NOA settlement result must be an object")

    relationship=result.get("observerRelationship")
    source=result.get("observerRelationshipSource")
    if source!="VERIFIER_DERIVED":
        raise ValueError(
            "NOA observerRelationship must be VERIFIER_DERIVED before normalization"
        )
    if relationship not in {
        "SAME_SIGNING_KEY",
        "SAME_ADMINISTRATIVE_PARTY",
        "UNKNOWN",
    }:
        raise ValueError(f"unsupported NOA observerRelationship: {relationship}")

    envelope=_base(
        upstream="noa-mandate-core",
        artifact_type="settlement-evidence-result",
    )
    envelope["upstream"]["verdict"]=relationship
    envelope["upstream"]["relationship_source"]=source

    policy_hash=result.get("trustPolicyHash")
    registry_hash=result.get("registrySnapshotHash")
    if not isinstance(policy_hash,str) or not policy_hash.startswith("sha256:"):
        raise ValueError("NOA trustPolicyHash is required")
    if not isinstance(registry_hash,str) or not registry_hash.startswith("sha256:"):
        raise ValueError("NOA registrySnapshotHash is required")
    envelope["trust_context"]={
        "trust_policy_hash":policy_hash,
        "registry_snapshot_hash":registry_hash,
    }

    if relationship=="SAME_SIGNING_KEY":
        envelope["facts"]["same_credential"]=_fact(
            "TRUE",
            source="noa-mandate-core",
            basis="verifier-derived-public-key-material comparison",
        )
        envelope["relationship_class"]="KNOWN_OVERLAP"
    elif relationship=="SAME_ADMINISTRATIVE_PARTY":
        envelope["facts"]["same_credential"]=_fact(
            "FALSE",
            source="noa-mandate-core",
            basis="distinct keys under one tenant manifest",
        )
        envelope["facts"]["same_administrative_party"]=_fact(
            "TRUE",
            source="noa-mandate-core",
            basis="verifier-derived shared tenant manifest",
        )
        envelope["relationship_class"]="KNOWN_OVERLAP"
    else:
        envelope["relationship_class"]="UNKNOWN"

    envelope["non_claims"].append(
        "NOA deliberately does not expose INDEPENDENT_ORGANIZATION in this relationship surface."
    )
    return envelope


def from_windowpilot_object_observation(artifact: dict[str, Any]) -> dict[str, Any]:
    """Normalize WindowPilot's object-observation separation declaration.

    WindowPilot records distinct declared control domains while explicitly
    keeping independence_proven=false. This adapter preserves that ceiling.
    """
    if not isinstance(artifact,dict):
        raise ValueError("WindowPilot observation must be an object")
    if artifact.get("schema_version")!="windowpilot-object-observation/v0.1":
        raise ValueError("unsupported WindowPilot object observation schema")

    separation=artifact.get("separation")
    if not isinstance(separation,dict):
        raise ValueError("WindowPilot observation separation is required")
    if separation.get("independence_proven") is not False:
        raise ValueError(
            "WindowPilot v0.1 adapter refuses artifacts that claim proven independence"
        )
    if separation.get("declared_distinct_control_domains") is not True:
        raise ValueError(
            "WindowPilot observation must declare distinct control domains"
        )

    observer=artifact.get("observer") or {}
    observer_domain=str(observer.get("control_domain") or "").strip()
    effecting_domain=str(artifact.get("effecting_control_domain") or "").strip()
    if not observer_domain or not effecting_domain:
        raise ValueError("WindowPilot control domains are required")
    if observer_domain==effecting_domain:
        raise ValueError("WindowPilot control domains are not distinct")

    envelope=_base(
        upstream="windowpilot",
        artifact_type="windowpilot-object-observation/v0.1",
    )
    envelope["upstream"]["observation_id"]=artifact.get("observation_id")
    envelope["upstream"]["observation_sha256"]=artifact.get("observation_sha256")
    envelope["facts"]["distinct_declared_control_domain"]=_fact(
        "TRUE",
        source="windowpilot",
        basis="producer-declared distinct control-domain labels",
    )
    envelope["relationship_class"]="DECLARED_SEPARATION_ONLY"
    envelope["trust_context"]={
        "observer_control_domain":observer_domain,
        "effecting_control_domain":effecting_domain,
    }
    envelope["non_claims"].append(
        "WindowPilot control-domain labels are producer-supplied policy metadata, not verifier-derived proof of independence."
    )
    return envelope


def merge_relationship_envelopes(*envelopes: dict[str, Any]) -> dict[str, Any]:
    """Combine normalized facts without inventing consensus.

    Conflicting TRUE/FALSE facts become UNKNOWN with an explicit conflict
    record. UNKNOWN never overrides a known fact.
    """
    if not envelopes:
        raise ValueError("at least one relationship envelope is required")
    for item in envelopes:
        if item.get("schema_version")!=_SCHEMA:
            raise ValueError("unsupported relationship envelope schema")

    merged=_base(upstream="counterproof-merge",artifact_type="relationship-merge")
    merged["upstream"]["inputs"]=[
        deepcopy(item.get("upstream") or {}) for item in envelopes
    ]
    merged["trust_context"]={
        "inputs":[deepcopy(item.get("trust_context") or {}) for item in envelopes]
    }
    conflicts=[]

    for name in merged["facts"]:
        known=[]
        for item in envelopes:
            fact=(item.get("facts") or {}).get(name) or {}
            state=fact.get("state")
            if state in {"TRUE","FALSE"}:
                known.append((state,deepcopy(fact)))
        states={state for state,_ in known}
        if len(states)>1:
            merged["facts"][name]=_fact(
                "UNKNOWN",
                source="counterproof-merge",
                basis="conflicting-upstream-facts",
            )
            conflicts.append(name)
        elif len(states)==1:
            merged["facts"][name]=known[0][1]

    if conflicts:
        merged["relationship_class"]="CONFLICT"
    elif any(
        fact["state"]=="TRUE"
        for name,fact in merged["facts"].items()
        if name in {"same_credential","same_administrative_party"}
    ):
        merged["relationship_class"]="KNOWN_OVERLAP"
    elif merged["facts"]["distinct_declared_control_domain"]["state"]=="TRUE":
        merged["relationship_class"]="DECLARED_SEPARATION_ONLY"
    else:
        merged["relationship_class"]="UNKNOWN"

    merged["conflicts"]=conflicts
    return merged
