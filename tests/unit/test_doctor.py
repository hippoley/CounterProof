from __future__ import annotations

import json

from click.testing import CliRunner

from skill_factory.evolution.cli import cli
from skill_factory.evolution.doctor import run_doctor


def test_counterproof_doctor_passes_real_git_selftest():
    report = run_doctor()

    assert report.ok is True
    by_name = {item.name: item for item in report.checks}
    assert by_name["git"].status == "pass"
    assert by_name["structured-result"].status == "pass"
    assert by_name["regression-witness"].status == "pass"
    assert by_name["proof-integrity"].status == "pass"


def test_counterproof_doctor_cli_json_output_is_machine_readable():
    result = CliRunner().invoke(cli, ["doctor", "--json-output"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    statuses = {item["name"]: item["status"] for item in payload["checks"]}
    assert statuses["regression-witness"] == "pass"
    assert statuses["proof-integrity"] == "pass"
