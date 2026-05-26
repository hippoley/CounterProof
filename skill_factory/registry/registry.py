"""Skill Registry: versioned store for validated skills."""
from __future__ import annotations
import json
import shutil
from pathlib import Path

from skill_factory.loader import load_skill
from skill_factory.models import Skill, SkillMeta


class SkillRegistry:
    """
    Manages a local directory of validated skills.

    Layout::

        registry_data/
          index.json          # {name: {version, path, domain, tags, description}}
          skills/
            my-skill/         # copy of the skill directory
    """

    def __init__(self, registry_dir: Path | str = "registry_data"):
        self.registry_dir = Path(registry_dir)
        self.skills_dir = self.registry_dir / "skills"
        self.index_path = self.registry_dir / "index.json"
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, dict] = self._load_index()

    # ── index helpers ──────────────────────────────────────────────────────

    def _load_index(self) -> dict[str, dict]:
        if self.index_path.exists():
            return json.loads(self.index_path.read_text())
        return {}

    def _save_index(self) -> None:
        self.index_path.write_text(json.dumps(self._index, indent=2))

    # ── public API ─────────────────────────────────────────────────────────

    def add(self, skill_dir: Path | str, overwrite: bool = False) -> Skill:
        """Copy a skill into the registry and update the index."""
        skill = load_skill(Path(skill_dir))
        dest = self.skills_dir / skill.name
        if dest.exists():
            if not overwrite:
                raise FileExistsError(
                    f"Skill '{skill.name}' already in registry. Use overwrite=True."
                )
            shutil.rmtree(dest)
        shutil.copytree(skill.path, dest)
        self._index[skill.name] = {
            "version": skill.meta.version,
            "path": str(dest),
            "domain": skill.meta.domain,
            "tags": skill.meta.tags,
            "description": skill.description,
        }
        self._save_index()
        return skill

    def get(self, name: str) -> Skill:
        """Load a skill from the registry by name."""
        if name not in self._index:
            raise KeyError(f"Skill '{name}' not found in registry.")
        return load_skill(Path(self._index[name]["path"]))

    def remove(self, name: str) -> None:
        """Remove a skill from the registry."""
        if name not in self._index:
            raise KeyError(f"Skill '{name}' not found in registry.")
        dest = Path(self._index[name]["path"])
        if dest.exists():
            shutil.rmtree(dest)
        del self._index[name]
        self._save_index()

    def list(self) -> list[SkillMeta]:
        """Return lightweight metadata for all registered skills."""
        result = []
        for name, info in self._index.items():
            result.append(
                SkillMeta(
                    name=name,
                    description=info["description"],
                    version=info["version"],
                    metadata={"domain": info["domain"], "tags": info["tags"]},
                )
            )
        return result

    def search(self, query: str) -> list[SkillMeta]:
        """Simple keyword search over name, description, domain, and tags."""
        q = query.lower()
        return [
            m for m in self.list()
            if q in m.name.lower()
            or q in m.description.lower()
            or q in m.domain.lower()
            or any(q in t.lower() for t in m.tags)
        ]
