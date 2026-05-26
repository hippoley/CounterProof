"""Skill Factory Web UI — FastAPI backend."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from skill_factory.loader import load_skill, load_skill_index
from skill_factory.registry.registry import SkillRegistry
from skill_factory.verifier.static_check import verify_skill

# ── app setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Skill Factory Review UI",
    description="Review, validate, approve, and manage Agent Skills",
    version="0.1.0",
)

_HERE = Path(__file__).parent
_STATIC = _HERE / "static"
_TEMPLATES = _HERE / "templates"

if _STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_skills_dir() -> Path:
    """Resolve the skills directory relative to the project root."""
    # Walk up from this file to find the project root (contains pyproject.toml)
    p = Path(__file__).resolve()
    for _ in range(6):
        p = p.parent
        if (p / "pyproject.toml").exists():
            return p / "skills"
    return Path("skills")


def _get_registry() -> SkillRegistry:
    skills_dir = _get_skills_dir()
    registry_dir = skills_dir.parent / "registry_data"
    return SkillRegistry(registry_dir)


def _skill_to_dict(skill_dir: Path) -> dict[str, Any]:
    """Load a skill directory into a JSON-serializable dict."""
    try:
        skill = load_skill(skill_dir)
        result = verify_skill(skill_dir)
        return {
            "name": skill.name,
            "description": skill.description,
            "version": skill.meta.version,
            "domain": skill.meta.domain,
            "tags": skill.meta.tags,
            "path": str(skill_dir),
            "validation": {
                "passed": result.passed,
                "errors": result.errors,
                "warnings": result.warnings,
            },
            "has_evals": (skill_dir / "evals" / "evals.json").exists(),
            "has_scripts": any((skill_dir / "scripts").glob("*.py")) if (skill_dir / "scripts").exists() else False,
            "has_references": (skill_dir / "references").exists(),
        }
    except Exception as e:
        return {"name": skill_dir.name, "error": str(e), "path": str(skill_dir)}


# ── routes: UI ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Serve the main review UI."""
    html_file = _TEMPLATES / "index.html"
    if html_file.exists():
        return HTMLResponse(html_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Skill Factory UI</h1><p>Template not found.</p>", status_code=500)


# ── routes: API ───────────────────────────────────────────────────────────────

@app.get("/api/skills")
async def list_skills(
    domain: str = Query("", description="Filter by domain"),
    tag: str = Query("", description="Filter by tag"),
    search: str = Query("", description="Search by name or description"),
) -> JSONResponse:
    """List all skills in the skills/ directory with validation status."""
    skills_dir = _get_skills_dir()
    if not skills_dir.exists():
        return JSONResponse({"skills": [], "total": 0})

    skills = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").exists():
            continue
        info = _skill_to_dict(skill_dir)
        # Apply filters
        if domain and info.get("domain", "") != domain:
            continue
        if tag and tag not in info.get("tags", []):
            continue
        if search:
            q = search.lower()
            if q not in info.get("name", "").lower() and q not in info.get("description", "").lower():
                continue
        skills.append(info)

    return JSONResponse({"skills": skills, "total": len(skills)})


@app.get("/api/skills/{skill_name}")
async def get_skill(skill_name: str) -> JSONResponse:
    """Get full details for a single skill including SKILL.md content."""
    skills_dir = _get_skills_dir()
    skill_dir = skills_dir / skill_name
    if not skill_dir.exists():
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    info = _skill_to_dict(skill_dir)
    # Add full SKILL.md content
    skill_md = skill_dir / "SKILL.md"
    info["skill_md"] = skill_md.read_text(encoding="utf-8") if skill_md.exists() else ""

    # Add evals if present
    evals_file = skill_dir / "evals" / "evals.json"
    if evals_file.exists():
        info["evals"] = json.loads(evals_file.read_text())

    # Add trigger queries if present
    trigger_file = skill_dir / "evals" / "trigger_queries.json"
    if trigger_file.exists():
        info["trigger_queries"] = json.loads(trigger_file.read_text())

    return JSONResponse(info)


@app.get("/api/skills/{skill_name}/validate")
async def validate_skill(skill_name: str) -> JSONResponse:
    """Run static validation on a skill and return the result."""
    skills_dir = _get_skills_dir()
    skill_dir = skills_dir / skill_name
    if not skill_dir.exists():
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    result = verify_skill(skill_dir)
    return JSONResponse({
        "skill": skill_name,
        "passed": result.passed,
        "errors": result.errors,
        "warnings": result.warnings,
    })



class RegistryAction(BaseModel):
    skill_name: str
    overwrite: bool = False


@app.post("/api/registry/approve")
async def approve_skill(action: RegistryAction) -> JSONResponse:
    """Approve a skill: validate then add to registry."""
    skills_dir = _get_skills_dir()
    skill_dir = skills_dir / action.skill_name
    if not skill_dir.exists():
        raise HTTPException(status_code=404, detail=f"Skill '{action.skill_name}' not found")

    # Must pass validation before approval
    result = verify_skill(skill_dir)
    if not result.passed:
        return JSONResponse({
            "approved": False,
            "reason": "Validation failed",
            "errors": result.errors,
            "warnings": result.warnings,
        }, status_code=422)

    try:
        reg = _get_registry()
        skill = reg.add(skill_dir, overwrite=action.overwrite)
        return JSONResponse({
            "approved": True,
            "skill": skill.name,
            "version": skill.meta.version,
            "warnings": result.warnings,
        })
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/registry/reject")
async def reject_skill(action: RegistryAction) -> JSONResponse:
    """Reject a skill: record rejection reason (does not delete the skill directory)."""
    skills_dir = _get_skills_dir()
    skill_dir = skills_dir / action.skill_name
    if not skill_dir.exists():
        raise HTTPException(status_code=404, detail=f"Skill '{action.skill_name}' not found")

    # Write a rejection marker file
    rejection = {"skill": action.skill_name, "status": "rejected"}
    (skill_dir / ".rejected").write_text(json.dumps(rejection, indent=2))
    return JSONResponse({"rejected": True, "skill": action.skill_name})


@app.get("/api/registry")
async def list_registry() -> JSONResponse:
    """List all skills currently in the registry."""
    reg = _get_registry()
    skills = reg.list()
    return JSONResponse({
        "skills": [
            {
                "name": s.name,
                "version": s.version,
                "domain": s.domain,
                "tags": s.tags,
                "description": s.description,
            }
            for s in skills
        ],
        "total": len(skills),
    })


@app.delete("/api/registry/{skill_name}")
async def remove_from_registry(skill_name: str) -> JSONResponse:
    """Remove a skill from the registry."""
    try:
        reg = _get_registry()
        reg.remove(skill_name)
        return JSONResponse({"removed": True, "skill": skill_name})
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not in registry")


# ── CLI entrypoint ────────────────────────────────────────────────────────────

def serve(host: str = "0.0.0.0", port: int = 7860, reload: bool = False) -> None:
    """Start the Skill Factory web server."""
    try:
        import uvicorn  # type: ignore
    except ImportError as e:
        raise ImportError(
            "uvicorn not installed. Run: pip install skill-factory[web]"
        ) from e
    uvicorn.run("skill_factory.web.app:app", host=host, port=port, reload=reload)
