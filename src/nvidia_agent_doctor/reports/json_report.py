"""NVIDIA Agent Doctor — JSON report generator."""

from __future__ import annotations

import json

from nvidia_agent_doctor.core.result import DiagnosticReport


def render_json(report: DiagnosticReport, indent: int = 2) -> str:
    """Serialize the diagnostic report to JSON.

    Secrets are never included — the data models ensure all sensitive values
    are redacted before reaching this layer.
    """
    data = report.to_json_dict()
    # Convert datetime to ISO format string (Pydantic does this in mode='json')
    return json.dumps(data, indent=indent, default=str)


def write_json_report(report: DiagnosticReport, output_path: str) -> None:
    """Write JSON report to a file."""
    from pathlib import Path

    path = Path(output_path)
    path.write_text(render_json(report), encoding="utf-8")
