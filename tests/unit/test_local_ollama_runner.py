"""Offline runner protocol tests; no Ollama process or remote network is used."""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from urllib.error import URLError

import pytest


MODULE_PATH = Path("examples/skill_gate/local_ollama_runner.py")
SPEC = importlib.util.spec_from_file_location("counterproof_local_runner_test", MODULE_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def _prompt(arm, skill_path=None):
    return {
        "schema_version": "counterproof.skill-runner/v0.1",
        "case_id": "test-001",
        "prompt": "Respond with EXACT",
        "arm": arm,
        "skill_path": skill_path,
    }


def test_local_runner_baseline_has_no_skill(monkeypatch):
    requests = []

    def fake_open(request, timeout):
        assert timeout == 35
        requests.append(json.loads(request.data))
        return FakeResponse(
            b'{"choices":[{"message":{"content":"EXACT"}}]}'
        )

    monkeypatch.setattr(runner, "urlopen", fake_open)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_prompt("baseline"))))
    assert runner.run() == {"output": "EXACT"}
    assert len(requests) == 1
    assert requests[0]["model"] == "qwen2.5:3b"
    assert len(requests[0]["messages"]) == 2
    assert requests[0]["stream"] is False


def test_local_runner_skill_injects_same_installed_skill_content(monkeypatch, tmp_path):
    skill = tmp_path / "managed-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("STRICT SKILL CONTENT", encoding="utf-8")
    requests = []

    def fake_open(request, timeout):
        requests.append(json.loads(request.data))
        return FakeResponse(b'{"choices":[{"message":{"content":"EXACT"}}]}')

    monkeypatch.setattr(runner, "urlopen", fake_open)
    monkeypatch.setattr(
        sys, "stdin", io.StringIO(json.dumps(_prompt("skill", str(skill))))
    )
    assert runner.run()["output"] == "EXACT"
    assert requests[0]["messages"][1]["content"] == "STRICT SKILL CONTENT"


def test_local_runner_rejects_skill_in_baseline(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sys, "stdin", io.StringIO(json.dumps(_prompt("baseline", str(tmp_path))))
    )
    with pytest.raises(ValueError, match="baseline must not load"):
        runner.run()


def test_local_runner_does_not_turn_endpoint_failure_into_pass(monkeypatch):
    def fail(*_args, **_kwargs):
        raise URLError("model server down")

    monkeypatch.setattr(runner, "urlopen", fail)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_prompt("baseline"))))
    with pytest.raises(RuntimeError, match="local Ollama model call failed"):
        runner.run()
