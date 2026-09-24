from pathlib import Path

PUBLIC_SURFACES = (
    Path("README.md"),
    Path("docs/COUNTERPROOF.md"),
    Path("site/index.html"),
    Path("site/standalone.html"),
)


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
