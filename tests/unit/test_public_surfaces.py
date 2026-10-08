import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import yaml

from skill_factory.evolution.capabilities import capability_report
from skill_factory.evolution.claimproof_basis_handoff import (
    load_claimproof_basis_handoff,
)
from skill_factory.evolution.external_execution_receipt import (
    admit_external_execution_receipt,
)

PUBLIC_SURFACES = (
    Path("README.md"),
    Path("docs/COUNTERPROOF.md"),
    Path("site/index.html"),
    Path("site/standalone.html"),
)




def _standalone_json(name: str, *, next_name: str | None) -> object:
    text = Path("site/standalone.html").read_text(encoding="utf-8")
    start_marker = f"const {name}="
    start = text.index(start_marker) + len(start_marker)
    if next_name is None:
        end = text.index(";\nconst __nativeFetch", start)
    else:
        end = text.index(f";\nconst {next_name}=", start)
    return json.loads(text[start:end])


def test_public_surfaces_use_canonical_counterproof_repository():
    stale_repo = "github.com/hippoley/SkillFactory"

    for path in PUBLIC_SURFACES:
        text = path.read_text(encoding="utf-8")
        assert stale_repo not in text, f"{path} still points at the renamed repository"


def test_proof_lab_public_surface_is_explicitly_fixture_backed():
    for path in (Path("site/index.html"), Path("site/standalone.html")):
        text = path.read_text(encoding="utf-8")
        assert "interactive fixture" in text
        assert "PROOF LAB / 001" in text


def test_readme_install_cta_targets_current_onboarding_section():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "(#30-second-onboarding)" in text
    assert "(#drop-it-into-a-pr)" not in text


def test_readme_hero_reflects_current_candidate_and_oracle_model():
    text = Path("README.md").read_text(encoding="utf-8")
    hero = text.split("</div>", 1)[0]
    assert "Replay the evidence. Test the oracle." in hero
    assert "exact candidates" in hero
    assert "explicit oracle" in hero
    assert "two commits" not in hero


def test_proof_lab_reality_data_surfaces_current_machine_backed_artifacts():
    reality = Path("site/data/reality_cases.json").read_text(encoding="utf-8")
    standalone = Path("site/standalone.html").read_text(encoding="utf-8")

    for case_id in ("bluefin-4539", "claude-code-89404", "gramps-2484"):
        assert f'"id": "{case_id}"' in reality
        assert f'"id": "{case_id}"' in standalone

    assert '"result": "OPEN PROBE"' not in reality
    assert '"result": "OPEN PROBE"' not in standalone
    assert "FLAGSHIP PROOF" in reality
    assert "ORACLE ARTIFACT" in reality
    assert "TRIAD PROOF" in reality


def test_proof_lab_public_copy_reflects_candidate_and_oracle_model():
    for path in (Path("site/index.html"), Path("site/standalone.html")):
        text = path.read_text(encoding="utf-8")
        assert "candidate-bound evidence" in text
        assert "declared oracle" in text


def test_reality_lab_does_not_present_stale_clash_evidence_as_current():
    text = Path("docs/REALITY_LAB.md").read_text(encoding="utf-8")
    assert "WITNESSED_BEHAVIOR on frozen candidates · lifecycle STALE" in text
    assert "historical behavior witness complete; lifecycle STALE" in text
    assert "must not be presented as current evidence for the changed candidate" in text


def test_reality_lab_tracks_avera_release_provenance_correction():
    text = Path("docs/REALITY_LAB.md").read_text(encoding="utf-8")
    assert "tool.version: 0.1.1" in text
    assert "not reproducible from an installable release" in text
    assert "v0.2.0" in text
    assert "pull/140" in text


def test_proof_lab_lifecycle_matches_canonical_reality_contracts():
    published = json.loads(
        Path("site/data/reality_cases.json").read_text(encoding="utf-8")
    )
    suite = yaml.safe_load(
        Path("examples/claim_matrix/reality-contracts.yml").read_text(encoding="utf-8")
    )
    contracts = {item["id"]: item for item in suite["contracts"]}
    bound_cases = [item for item in published["cases"] if item.get("reality_contract_id")]
    assert bound_cases, "Proof Lab must publish at least one Reality Contract-bound case"

    for item in bound_cases:
        contract = contracts[item["reality_contract_id"]]
        assert item["lifecycle"] == contract["lifecycle"]
        if item["lifecycle"] != "CURRENT":
            assert item.get("lifecycle_note"), (
                f'{item["id"]} publishes non-current evidence without a public reason'
            )

    clash = next(item for item in bound_cases if item["id"] == "clash-8017")
    assert clash["lifecycle"] == "STALE"
    assert "Historical proof remains valid only for the pinned candidates" in clash["lifecycle_note"]


def test_readme_public_case_count_matches_reality_lab_table():
    readme = Path("README.md").read_text(encoding="utf-8")
    reality_lab = Path("docs/REALITY_LAB.md").read_text(encoding="utf-8")
    field_rows = [
        line
        for line in reality_lab.splitlines()
        if line.startswith("| [") and "](https://github.com/" in line
    ]
    assert field_rows, "Reality Lab must publish at least one field case"
    assert f"| **{len(field_rows)} public PR cases** |" in readme


def test_high_signal_public_claims_match_canonical_reality_contracts():
    public_claims = yaml.safe_load(
        Path("examples/claim_matrix/public-claims.yml").read_text(encoding="utf-8")
    )
    suite = yaml.safe_load(
        Path("examples/claim_matrix/reality-contracts.yml").read_text(encoding="utf-8")
    )
    contracts = {item["id"]: item for item in suite["contracts"]}
    external_state = yaml.safe_load(
        Path("examples/claim_matrix/external-state.yml").read_text(encoding="utf-8")
    )
    observations = {item["id"]: item for item in external_state["observations"]}

    assert public_claims["schema_version"] == 1
    assert public_claims["claims"], "at least one public claim must be bound"

    for claim in public_claims["claims"]:
        surface = Path(claim["surface"]).read_text(encoding="utf-8")
        assert claim["contains"] in surface, (
            f'{claim["id"]} is declared but its public statement is missing'
        )

        if claim.get("must_also_contain"):
            assert claim["must_also_contain"] in surface, (
                f'{claim["id"]} is missing its public boundary statement'
            )

        if claim.get("reality_contract_id"):
            contract = contracts[claim["reality_contract_id"]]
            assert contract["lifecycle"] in claim["allowed_lifecycles"], (
                f'{claim["id"]} publishes lifecycle {contract["lifecycle"]}, '
                f'allowed={claim["allowed_lifecycles"]}'
            )

            expected = claim.get("expectation")
            if expected:
                observed = next(
                    item
                    for item in contract["expectations"]
                    if item["claim_id"] == expected["claim_id"]
                )
                for field in ("overall_claim", "receipt_verdict"):
                    assert observed.get(field) == expected[field], (
                        f'{claim["id"]} expected {field}={expected[field]!r}, '
                        f'observed={observed.get(field)!r}'
                    )

        provenance = claim.get("provenance")
        if provenance:
            handoff = Path(provenance["handoff_file"]).read_text(encoding="utf-8")
            for fragment in provenance["handoff_contains"]:
                assert fragment in handoff, (
                    f'{claim["id"]} handoff provenance lost {fragment!r}'
                )

            envelope_path = Path(provenance["envelope_file"])
            envelope_bytes = envelope_path.read_bytes()
            git_blob = hashlib.sha1(
                f"blob {len(envelope_bytes)}\0".encode() + envelope_bytes
            ).hexdigest()
            assert git_blob == provenance["envelope_git_blob_sha"]

            envelope = json.loads(envelope_bytes)
            for dotted, expected_value in provenance["json_expectations"].items():
                observed_value = envelope
                for key in dotted.split("."):
                    observed_value = observed_value[key]
                assert observed_value == expected_value, (
                    f'{claim["id"]} expected {dotted}={expected_value!r}, '
                    f'observed={observed_value!r}'
                )

        state_ref = claim.get("external_state_ref")
        if state_ref:
            observation = observations[state_ref]
            observed_at = date.fromisoformat(observation["observed_at"])
            today_utc = datetime.now(timezone.utc).date()
            age_days = (today_utc - observed_at).days
            assert age_days <= observation["refresh_after_days"], (
                f'{claim["id"]} external state snapshot is {age_days} days old; '
                f'refresh after {observation["refresh_after_days"]}'
            )

        assert bool(claim.get("reality_contract_id")) ^ bool(provenance), (
            f'{claim["id"]} must bind exactly one canonical evidence source'
        )


def test_standalone_embedded_data_matches_site_json_sources():
    assert _standalone_json(
        "__COUNTERPROOF_CASES__",
        next_name="__COUNTERPROOF_CAPS__",
    ) == json.loads(Path("site/data/evolution_cases.json").read_text(encoding="utf-8"))
    assert _standalone_json(
        "__COUNTERPROOF_CAPS__",
        next_name="__COUNTERPROOF_REALITY__",
    ) == json.loads(Path("site/data/capabilities.json").read_text(encoding="utf-8"))
    assert _standalone_json(
        "__COUNTERPROOF_REALITY__",
        next_name=None,
    ) == json.loads(Path("site/data/reality_cases.json").read_text(encoding="utf-8"))


def test_public_capability_json_matches_runtime_truth_table():
    published = json.loads(
        Path("site/data/capabilities.json").read_text(encoding="utf-8")
    )
    assert published == capability_report()

def test_governance_dry_run_is_bound_to_fresh_external_snapshot():
    external_state = yaml.safe_load(
        Path("examples/claim_matrix/external-state.yml").read_text(encoding="utf-8")
    )
    observations = {item["id"]: item for item in external_state["observations"]}
    observation = observations["ite63-openfab-604-dry-run"]

    assert observation["refresh_after_days"] == 14
    assert observation["sources"], "governance dry-run must pin source observations"

    sources = {item["url"]: item for item in observation["sources"]}
    ite = sources["https://github.com/in-toto/ITE/pull/63"]
    assert ite["kind"] == "pull_request"
    assert ite["state"] == "open"
    assert ite["merged"] is False
    assert ite["head_sha"] == "ef11838ea97886f5e3702513983c4bf0af50d3b3"

    proposal = sources["https://github.com/in-toto/attestation/issues/604"]
    assert proposal["kind"] == "issue"
    assert proposal["state"] == "open"
    assert proposal["updated_at"] == "2026-10-02T17:46:36Z"
    assert proposal["comments"] == 6

    openfab = [
        item
        for item in observation["sources"]
        if item["url"] == "https://github.com/Open-fab-ai/openfab"
    ]
    assert openfab == [
        {
            "url": "https://github.com/Open-fab-ai/openfab",
            "kind": "repository_file",
            "path": "docs/generation-predicate-v0.1.md",
            "blob_sha": "77051b33a8ab5c9fdf95bab8c6b263a173810ad4",
        }
    ]

    vectors = [
        item
        for item in observation["sources"]
        if item["url"] == "https://github.com/probityai/agent-evidence-vectors"
    ]
    assert {item["path"]: item["blob_sha"] for item in vectors} == {
        "vectors-ai-generation/MANIFEST.json": (
            "89cbc4f7d8f0e268a2da35e2417eb2c5090629d5"
        ),
        "docs/proposals/ai-generation-v01-findings.md": (
            "0b764141c515f4b6c408b92a906147a7c35d2451"
        ),
    }

    dry_run = Path("docs/interop/ite63-openfab-604-dry-run.md").read_text(
        encoding="utf-8"
    )
    assert "ite63-openfab-604-dry-run" in dry_run

    expected_fragments = {
        "ef11838ea97886f5e3702513983c4bf0af50d3b3",
        "2026-10-02T17:46:36Z",
        "77051b33a8ab5c9fdf95bab8c6b263a173810ad4",
        "89cbc4f7d8f0e268a2da35e2417eb2c5090629d5",
        "0b764141c515f4b6c408b92a906147a7c35d2451",
    }
    for fragment in expected_fragments:
        assert fragment in dry_run

    observed_at = date.fromisoformat(observation["observed_at"])
    today_utc = datetime.now(timezone.utc).date()
    age_days = (today_utc - observed_at).days
    assert age_days <= observation["refresh_after_days"], (
        f"governance dry-run snapshot is {age_days} days old; "
        f"refresh after {observation['refresh_after_days']}"
    )

def test_external_evidence_ledger_preserves_recognition_boundaries():
    ledger = yaml.safe_load(
        Path("examples/claim_matrix/external-evidence-ledger.yml").read_text(
            encoding="utf-8"
        )
    )
    records = {item["id"]: item for item in ledger["records"]}

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

def test_external_evidence_ledger_orders_recognition_without_claim_inflation():
    ledger = yaml.safe_load(
        Path("examples/claim_matrix/external-evidence-ledger.yml").read_text(
            encoding="utf-8"
        )
    )
    records = {item["id"]: item for item in ledger["records"]}

    reviewer = records["reviewer-claim-matrix-use-intent"]
    assert reviewer["status"] == "THIRD_PARTY_CONFIRMED_USE_INTENT"
    assert reviewer["durable_value"]["explicit_use_intent"] is True
    assert reviewer["durable_value"]["producer_owned_artifact"] is False

    prove = records["codex-prove-optional-handoff"]
    assert prove["status"] == "MAINTAINER_CONFIRMED_INTEROP_BOUNDARY"
    assert prove["durable_value"]["maintainer_boundary_confirmation"] is True
    assert prove["durable_value"]["upstream_adoption"] is False

    claimproof = records["claimproof-first-class-use-case-invitation"]
    assert (
        claimproof["status"]
        == "CONSUMER_ARTIFACT_IMPLEMENTED_MAINTAINER_CONFIRMATION_PENDING"
    )
    assert claimproof["durable_value"]["explicit_upstream_invitation"] is True
    assert claimproof["durable_value"]["consumer_artifact_landed"] is True
    assert claimproof["durable_value"]["maintainer_confirmation_pending"] is True
    assert claimproof["durable_value"]["upstream_artifact_landed"] is False

    agent_done = records["agent-done-or-not-receipt-input"]
    assert agent_done["status"] == "MAINTAINER_APPROVED_INPUT_BOUNDARY"
    assert agent_done["durable_value"]["explicit_reuse_permission"] is True
    assert agent_done["durable_value"]["frozen_payload_landed"] is False

def test_claimproof_basis_handoff_binds_native_store_to_candidate():
    fixture = Path("examples/interop/claimproof-basis-v0")
    receipt = load_claimproof_basis_handoff(fixture / "handoff.json")

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
    fixture = Path("examples/interop/claimproof-basis-v0")
    handoff = (fixture / "handoff.json").read_text(encoding="utf-8")
    basis = (fixture / "claim-basis.json").read_text(encoding="utf-8")

    (tmp_path / "handoff.json").write_text(handoff, encoding="utf-8")
    (tmp_path / "claim-basis.json").write_text(
        basis.replace("the targeted regression suite passes", "different claim"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="claim basis identity mismatch"):
        load_claimproof_basis_handoff(tmp_path / "handoff.json")


def test_claimproof_basis_handoff_requires_candidate_identity(tmp_path: Path):
    fixture = Path("examples/interop/claimproof-basis-v0")
    handoff = (fixture / "handoff.json").read_text(encoding="utf-8")
    handoff = handoff.replace(
        '"identity": "example-candidate-identity"',
        '"identity": ""',
    )
    (tmp_path / "handoff.json").write_text(handoff, encoding="utf-8")
    (tmp_path / "claim-basis.json").write_text(
        (fixture / "claim-basis.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="candidate.identity is required"):
        load_claimproof_basis_handoff(tmp_path / "handoff.json")

def test_real_agent_done_receipt_is_admitted_as_execution_input_only():
    fixture = Path("examples/interop/agent-done-v2-real")
    admitted = admit_external_execution_receipt(
        fixture / "receipt.json",
        fixture / "provenance.json",
    )

    assert admitted["receipt_type"] == "EXTERNAL_EXECUTION_EVIDENCE_INPUT"
    assert admitted["admission"] == "BOUND_EXECUTION_INPUT"
    assert admitted["producer"]["identity"] == "done-gate.sh@0.13.1"
    assert admitted["producer"]["resolved_commit"] == (
        "4a801bf056519af5a845e773260ef23796eea3ff"
    )
    assert admitted["candidate"]["commit"] == (
        "a3e1ed55ba84f2cde64c328d682fff54b2770017"
    )
    assert admitted["execution"]["exit_code"] == 0
    assert admitted["execution"]["output_sha256"] == (
        "f4a46ed95fa04eca41f7b2bd877f244e2ed1aa01e4528f1866895ed48c0ce9f9"
    )
    text = json.dumps(admitted).lower()
    assert "candidate is correct" in text
    assert "fixed" in text


def test_external_execution_receipt_rejects_non_reexecuted(tmp_path: Path):
    fixture = Path("examples/interop/agent-done-v2-real")
    receipt = json.loads((fixture / "receipt.json").read_text(encoding="utf-8"))
    receipt["disposition"] = "asserted"

    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(ValueError, match="disposition=reexecuted"):
        admit_external_execution_receipt(
            receipt_path,
            fixture / "provenance.json",
        )

