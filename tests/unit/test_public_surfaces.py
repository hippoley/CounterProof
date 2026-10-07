import json
from pathlib import Path

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
