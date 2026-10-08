from __future__ import annotations

import copy
import json
from pathlib import Path

from skill_factory.evolution.avera_check_v0 import avera_check_v0_digest

fixture = json.loads(
    Path("examples/handoff/avera-check-v0/envelope.json").read_text(encoding="utf-8")
)

scores = [0.66, 1e-7, -0.0, 1.0]
vectors = []
for score in scores:
    env = copy.deepcopy(fixture)
    env["result"]["confidence_score"] = score
    env["digest"] = avera_check_v0_digest(env)
    vectors.append(
        {
            "confidence_score": score,
            "envelope": env,
            "python_digest": env["digest"],
        }
    )

Path("avera-v0-cross-language-vectors.json").write_text(
    json.dumps(vectors, ensure_ascii=False, separators=(",", ":")),
    encoding="utf-8",
)
print(json.dumps({"python_vectors":"READY","cases":len(vectors)}))
