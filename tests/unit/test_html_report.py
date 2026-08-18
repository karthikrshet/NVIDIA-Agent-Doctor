"""Security tests for the self-contained HTML report."""

from __future__ import annotations

from nvidia_agent_doctor.core.result import CheckResult, DiagnosticReport, SectionResult
from nvidia_agent_doctor.core.severity import Severity
from nvidia_agent_doctor.reports.html import render_html


def test_report_escapes_untrusted_diagnostic_values() -> None:
    """Report fields must remain text, not executable HTML."""
    payload = '<img src=x onerror=alert("xss")>'
    report = DiagnosticReport()
    report.add_section(
        SectionResult(
            name="untrusted",
            display_name=payload,
            checks=[
                CheckResult(
                    name=payload,
                    severity=Severity.WARNING,
                    message=payload,
                    detail=payload,
                    recommendation=payload,
                )
            ],
        )
    )

    output = render_html(report)

    assert payload not in output
    assert "&lt;img src=x onerror=alert(&quot;xss&quot;)&gt;" in output
