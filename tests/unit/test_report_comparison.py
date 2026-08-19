"""Tests for safe report regression comparison."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nvidia_agent_doctor.reports.comparison import ReportComparisonError, compare_report_files


def _write_report(path: Path, *, score: int, errors: int, security: int, exit_code: int) -> None:
    path.write_text(
        json.dumps(
            {
                "summary": {
                    "overall_score": score,
                    "total_errors": errors,
                    "total_security_findings": security,
                    "exit_code": exit_code,
                }
            }
        ),
        encoding="utf-8",
    )


def test_compare_reports_detects_health_and_security_regressions(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    _write_report(baseline, score=95, errors=0, security=0, exit_code=0)
    _write_report(current, score=80, errors=1, security=1, exit_code=3)

    result = compare_report_files(baseline, current)

    assert result["status"] == "regressed"
    assert result["score_delta"] == -15
    assert len(result["regressions"]) == 3


def test_compare_reports_rejects_malformed_or_incomplete_input(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text("[]", encoding="utf-8")
    _write_report(current, score=100, errors=0, security=0, exit_code=0)

    with pytest.raises(ReportComparisonError, match="JSON object"):
        compare_report_files(baseline, current)
