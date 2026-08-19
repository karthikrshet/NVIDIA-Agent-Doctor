"""Safe, machine-readable comparisons of NAD JSON reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MAX_REPORT_BYTES = 10 * 1024 * 1024


class ReportComparisonError(ValueError):
    """Raised when a supplied report is not a supported NAD JSON report."""


def compare_report_files(baseline_path: Path, current_path: Path) -> dict[str, Any]:
    """Compare two existing JSON reports without reproducing report contents."""
    baseline = _report_summary(_load_report(baseline_path), baseline_path)
    current = _report_summary(_load_report(current_path), current_path)

    regressions: list[str] = []
    improvements: list[str] = []
    score_delta = current["overall_score"] - baseline["overall_score"]
    if score_delta < 0:
        regressions.append(f"Health score decreased by {abs(score_delta)} point(s).")
    elif score_delta > 0:
        improvements.append(f"Health score increased by {score_delta} point(s).")
    _compare_count("diagnostic error", baseline, current, regressions, improvements)
    _compare_count("high security finding", baseline, current, regressions, improvements)

    return {
        "status": "regressed" if regressions else "improved" if improvements else "unchanged",
        "baseline": baseline,
        "current": current,
        "score_delta": score_delta,
        "regressions": regressions,
        "improvements": improvements,
    }


def _load_report(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise ReportComparisonError(f"Report file does not exist: {path}")
        if path.stat().st_size > MAX_REPORT_BYTES:
            raise ReportComparisonError(
                f"Report file exceeds {MAX_REPORT_BYTES // (1024 * 1024)} MiB."
            )
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportComparisonError(f"Could not read JSON report: {path}") from exc
    if not isinstance(data, dict):
        raise ReportComparisonError(f"Report must be a JSON object: {path}")
    return data


def _report_summary(report: dict[str, Any], path: Path) -> dict[str, int]:
    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise ReportComparisonError(f"Report has no supported summary: {path}")
    values: dict[str, int] = {}
    for key, lower, upper in (
        ("overall_score", 0, 100),
        ("total_errors", 0, 1_000_000),
        ("total_security_findings", 0, 1_000_000),
        ("exit_code", 0, 4),
    ):
        value = summary.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= upper:
            raise ReportComparisonError(f"Report summary field {key!r} is invalid: {path}")
        values[key] = value
    return values


def _compare_count(
    label: str,
    baseline: dict[str, int],
    current: dict[str, int],
    regressions: list[str],
    improvements: list[str],
) -> None:
    key = "total_errors" if label == "diagnostic error" else "total_security_findings"
    difference = current[key] - baseline[key]
    if difference > 0:
        regressions.append(f"{difference} new {label}(s).")
    elif difference < 0:
        improvements.append(f"{abs(difference)} fewer {label}(s).")
