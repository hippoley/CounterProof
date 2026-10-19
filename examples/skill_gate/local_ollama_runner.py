#!/usr/bin/env python3
"""Opt-in, local-only OpenAI-compatible model runner for Skill gate previews.

This is a TEXT-ONLY model probe. It does NOT invoke coding tools or prove
cross-agent behavioral improvement. Modify MODEL in this file and the gate
will bind its changed SHA-256 at evaluation time. Never sends traffic outside
127.0.0.1 and never reads credentials.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MODEL = "qwen2.5:3b"  # Must already be present in a local Ollama installation.
LOCAL_URL = "http://127.0.0.1:11434/v1/chat/completions"
TIMEOUT_SECONDS = 35
MAX_RESPONSE_BYTES = 1024 * 1024


def run() -> dict[str, str]:
    payload = json.load(sys.stdin)
    if payload.get("schema_version") != "counterproof.skill-runner/v0.1":
        raise ValueError("unsupported runner contract version")
    arm = payload.get("arm")
    if arm not in {"baseline", "skill"}:
        raise ValueError("arm must be baseline or skill")
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")
    path = payload.get("skill_path")
    if arm == "baseline" and path is not None:
        raise ValueError("baseline must not load a Skill")
    if arm == "skill" and not isinstance(path, str):
        raise ValueError("skill arm requires managed Skill path")
    skill_text = (
        (Path(path) / "SKILL.md").read_text(encoding="utf-8")
        if arm == "skill" else None
    )
    messages = [
        {"role": "system", "content":
            "Answer the task faithfully and concisely; follow exact output constraints."},
    ]
    if skill_text is not None:
        messages.append({"role": "system", "content": skill_text})
    messages.append({"role": "user", "content": prompt})
    body = json.dumps({
        "model": MODEL, "messages": messages,
        "stream": False, "temperature": 0, "max_tokens": 128,
    }).encode()
    request = Request(
        LOCAL_URL, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(
            "local Ollama model call failed; confirm Ollama is running, "
            "the configured model exists, and endpoint is loopback"
        ) from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("model response exceeds limit")
    response = json.loads(raw.decode("utf-8"))
    answer = response["choices"][0]["message"]["content"]
    if not isinstance(answer, str):
        raise ValueError("model response content must be text")
    return {"output": answer}


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=False))
    except (OSError, ValueError, KeyError, IndexError, TypeError, RuntimeError) as exc:
        print(f"LOCAL_MODEL_RUNNER_ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
