import json
from pathlib import Path

import yaml

from skill_factory.evolution.capabilities import capability_report

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

    assert public_claims["schema_version"] == 1
    assert public_claims["claims"], "at least one public claim must be bound"

    for claim in public_claims["claims"]:
        surface = Path(claim["surface"]).read_text(encoding="utf-8")
        assert claim["contains"] in surface, (
            f'{claim["id"]} is declared but its public statement is missing'
        )

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
