"""Tests for the evidence-oriented security readiness report."""

from __future__ import annotations

from nvidia_agent_doctor.core.result import DiagnosticReport, SecurityFinding
from nvidia_agent_doctor.core.severity import SecuritySeverity
from nvidia_agent_doctor.reports.compliance import render_compliance_audit


def test_compliance_audit_is_explicitly_not_a_certification_and_redacts() -> None:
    secret = "sk-readinessreport0123456789abcdefghijkl"
    report = DiagnosticReport(
        security_findings=[
            SecurityFinding(
                title="Credential exposure",
                severity=SecuritySeverity.HIGH,
                description=f"API_KEY={secret}",
                recommendation="Rotate the secret.",
                component="credentials",
            )
        ]
    )

    output = render_compliance_audit(report)

    assert "not a" in output.lower()
    assert secret not in output
    assert "API_KEY=********" in output
