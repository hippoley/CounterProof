"""Build the static CounterProof Proof Lab for GitHub Pages."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "site", DIST)

    data = DIST / "data"
    data.mkdir(exist_ok=True)

    build = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit": subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
    }
    (data / "build.json").write_text(
        json.dumps(build, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (DIST / ".nojekyll").touch()


if __name__ == "__main__":
    main()
