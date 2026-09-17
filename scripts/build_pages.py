"""Build a static review UI from the repository's real skills and validators."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from skill_factory.loader import load_skill
from skill_factory.verifier.static_check import verify_skill

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
DIST = ROOT / "dist"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def serialize_skill(skill_dir: Path) -> dict:
    skill = load_skill(skill_dir)
    result = verify_skill(skill_dir)
    return {
        "name": skill.name,
        "description": skill.description,
        "version": skill.meta.version,
        "domain": skill.meta.domain,
        "tags": skill.meta.tags,
        "content": skill.content,
        "validation": {
            "passed": result.passed,
            "errors": result.errors,
            "warnings": result.warnings,
        },
        "evals": read_json(skill_dir / "evals" / "evals.json"),
        "trigger_queries": read_json(skill_dir / "evals" / "trigger_queries.json"),
        "resources": {
            "scripts": len(list((skill_dir / "scripts").glob("*.py"))) if (skill_dir / "scripts").exists() else 0,
            "references": len(list((skill_dir / "references").glob("*"))) if (skill_dir / "references").exists() else 0,
            "assets": len(list((skill_dir / "assets").glob("*"))) if (skill_dir / "assets").exists() else 0,
        },
    }


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "site", DIST)
    skills = [
        serialize_skill(path)
        for path in sorted(SKILLS.iterdir())
        if path.is_dir() and (path / "SKILL.md").exists()
    ]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit": subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip(),
        "skills": skills,
        "summary": {
            "total": len(skills),
            "valid": sum(item["validation"]["passed"] for item in skills),
            "eval_cases": sum(len((item["evals"] or {}).get("cases", item["evals"] or [])) for item in skills),
        },
    }
    data = DIST / "data"
    data.mkdir(exist_ok=True)
    (data / "skills.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (DIST / ".nojekyll").touch()


if __name__ == "__main__":
    main()
