"""Deterministic redaction regression probes for local report boundaries."""

from __future__ import annotations

from io import StringIO
from typing import Any

from rich.console import Console

from nvidia_agent_doctor.core.result import CheckResult, DiagnosticReport, SectionResult
from nvidia_agent_doctor.core.severity import Severity
from nvidia_agent_doctor.reports.html import render_html
from nvidia_agent_doctor.reports.json_report import render_json
from nvidia_agent_doctor.reports.markdown import render_markdown
from nvidia_agent_doctor.reports.terminal import render_report
from nvidia_agent_doctor.security.credentials import REDACTED, redact_text

_SENTINEL = "sk-leakcheck0123456789abcdefghijklmnop"


def run_leak_check() -> dict[str, Any]:
    """Verify that canonical report and exception boundaries redact a sentinel.

    This is a local regression test, not a claim to find every possible secret
    format or a replacement for a secrets-management system.
    """
    report = DiagnosticReport()
    section = SectionResult(name="leak-check", display_name="Leak Check")
    section.checks.append(
        CheckResult(
            name="sentinel",
            severity=Severity.WARNING,
            message=f"API_KEY={_SENTINEL}",
            detail=f"https://user:{_SENTINEL}@example.test/?token={_SENTINEL}",
            metadata={"authorization": f"Bearer {_SENTINEL}", "args": ["--token", _SENTINEL]},
        )
    )
    report.add_section(section)

    terminal = StringIO()
    render_report(report, Console(file=terminal, force_terminal=False, color_system=None))
    outputs = {
        "json": render_json(report),
        "markdown": render_markdown(report),
        "html": render_html(report),
        "terminal": terminal.getvalue(),
        "exception": redact_text(f"request failed: API_KEY={_SENTINEL}"),
    }
    checks = [
        {"boundary": name, "passed": _SENTINEL not in value and REDACTED in value}
        for name, value in outputs.items()
    ]
    return {"passed": all(check["passed"] for check in checks), "checks": checks}
