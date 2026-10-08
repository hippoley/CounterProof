import json

from click.testing import CliRunner

from skill_factory.evolution.cli import cli
from skill_factory.evolution.runtime_closure import evaluate_runtime_closure


def test_closed_requires_all_declared_sinks():
    result = evaluate_runtime_closure(
        {
            "sinks": ["worker", "resource-server"],
            "events": [
                {"seq": 1, "type": "authority_change_recorded"},
                {"seq": 2, "type": "authority_change_effective", "sink": "worker"},
                {"seq": 3, "type": "sink_closed", "sink": "worker"},
                {"seq": 4, "type": "authority_change_effective", "sink": "resource-server"},
                {"seq": 5, "type": "sink_closed", "sink": "resource-server"},
            ],
        }
    )

    assert result["verdict"] == "CLOSED"
    assert result["facts"]["closed_sinks"] == ["resource-server", "worker"]


def test_partial_preserves_open_path():
    result = evaluate_runtime_closure(
        {
            "sinks": ["worker", "resource-server"],
            "events": [
                {"seq": 1, "type": "authority_change_recorded"},
                {"seq": 2, "type": "authority_change_effective", "sink": "worker"},
                {"seq": 3, "type": "sink_closed", "sink": "worker"},
                {"seq": 4, "type": "evidence_unavailable", "sink": "resource-server"},
            ],
        }
    )

    assert result["verdict"] == "PARTIAL"


def test_missing_sink_enforcement_stays_unknown():
    result = evaluate_runtime_closure(
        {
            "sinks": ["resource-server"],
            "events": [
                {"seq": 1, "type": "authority_change_recorded"},
                {"seq": 2, "type": "evidence_unavailable", "sink": "resource-server"},
            ],
        }
    )

    assert result["verdict"] == "UNKNOWN"
    assert result["facts"]["evidence_unavailable_sinks"] == ["resource-server"]


def test_effect_after_sink_effective_is_violation():
    result = evaluate_runtime_closure(
        {
            "sinks": ["payment"],
            "events": [
                {"seq": 1, "type": "authority_change_recorded"},
                {"seq": 2, "type": "authority_change_effective", "sink": "payment"},
                {"seq": 3, "type": "effect_committed", "sink": "payment"},
            ],
        }
    )

    assert result["verdict"] == "VIOLATION"
    assert result["facts"]["violating_sinks"] == ["payment"]


def test_effect_before_sink_effective_is_not_auto_violation():
    result = evaluate_runtime_closure(
        {
            "sinks": ["payment"],
            "events": [
                {"seq": 1, "type": "authority_change_recorded"},
                {"seq": 2, "type": "effect_committed", "sink": "payment"},
                {"seq": 3, "type": "authority_change_effective", "sink": "payment"},
                {"seq": 4, "type": "sink_closed", "sink": "payment"},
            ],
        }
    )

    assert result["verdict"] == "CLOSED"



def test_openclaw_merged_regression_maps_to_closed():
    result = evaluate_runtime_closure(
        {
            "sinks": ["native-pty-construction"],
            "events": [
                {"seq": 1, "type": "authority_change_recorded"},
                {
                    "seq": 2,
                    "type": "authority_change_effective",
                    "sink": "native-pty-construction",
                },
                {"seq": 3, "type": "sink_closed", "sink": "native-pty-construction"},
            ],
        }
    )

    assert result["verdict"] == "CLOSED"


def test_open_agent_auth_authority_side_only_stays_unknown():
    result = evaluate_runtime_closure(
        {
            "sinks": ["resource-server"],
            "events": [
                {"seq": 1, "type": "authority_change_recorded"},
                {"seq": 2, "type": "evidence_unavailable", "sink": "resource-server"},
            ],
        }
    )

    assert result["verdict"] == "UNKNOWN"



def test_runtime_closure_cli_emits_machine_json_and_output_file(tmp_path):
    trace = tmp_path / "trace.json"
    output = tmp_path / "closure.json"
    trace.write_text(
        json.dumps(
            {
                "sinks": ["resource-server"],
                "events": [
                    {"seq": 1, "type": "authority_change_recorded"},
                    {
                        "seq": 2,
                        "type": "evidence_unavailable",
                        "sink": "resource-server",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        ["runtime-closure", str(trace), "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "counterproof.runtime-closure/v0.1"
    assert payload["verdict"] == "UNKNOWN"
    assert json.loads(output.read_text(encoding="utf-8")) == payload


def test_runtime_closure_cli_rejects_undeclared_sink(tmp_path):
    trace = tmp_path / "invalid.json"
    trace.write_text(
        json.dumps(
            {
                "sinks": ["worker"],
                "events": [
                    {
                        "seq": 1,
                        "type": "sink_closed",
                        "sink": "other",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["runtime-closure", str(trace)])

    assert result.exit_code != 0
    assert "undeclared sink" in result.output



def test_runtime_closure_cli_require_closed_blocks_unknown(tmp_path):
    trace = tmp_path / "trace.json"
    trace.write_text(
        json.dumps(
            {
                "sinks": ["resource-server"],
                "events": [
                    {"seq": 1, "type": "authority_change_recorded"},
                    {
                        "seq": 2,
                        "type": "evidence_unavailable",
                        "sink": "resource-server",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        ["runtime-closure", str(trace), "--require-closed"],
    )

    assert result.exit_code != 0
    assert '"verdict": "UNKNOWN"' in result.output
    assert "runtime closure required, got UNKNOWN" in result.output


def test_runtime_closure_cli_require_closed_accepts_closed_and_binds_trace(tmp_path):
    trace = tmp_path / "trace.json"
    trace.write_text(
        json.dumps(
            {
                "sinks": ["worker"],
                "events": [
                    {"seq": 1, "type": "authority_change_recorded"},
                    {
                        "seq": 2,
                        "type": "authority_change_effective",
                        "sink": "worker",
                    },
                    {"seq": 3, "type": "sink_closed", "sink": "worker"},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        ["runtime-closure", str(trace), "--require-closed"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "CLOSED"
    assert len(payload["trace_sha256"]) == 64
