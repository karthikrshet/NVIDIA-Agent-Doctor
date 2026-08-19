"""CLI behavior for report summary comparisons."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from nvidia_agent_doctor.cli.main import app

runner = CliRunner()


def test_report_compare_json_returns_warning_for_regression(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(
        json.dumps(
            {
                "summary": {
                    "overall_score": 90,
                    "total_errors": 0,
                    "total_security_findings": 0,
                    "exit_code": 0,
                }
            }
        ),
        encoding="utf-8",
    )
    current.write_text(
        json.dumps(
            {
                "summary": {
                    "overall_score": 80,
                    "total_errors": 0,
                    "total_security_findings": 0,
                    "exit_code": 1,
                }
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["report", "compare", str(baseline), str(current), "--json"])

    assert result.exit_code == 1
    assert json.loads(result.output)["status"] == "regressed"
