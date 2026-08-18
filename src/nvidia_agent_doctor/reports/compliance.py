"""Evidence-oriented security readiness report, not a compliance certification."""

from __future__ import annotations

from nvidia_agent_doctor.core.result import DiagnosticReport


def render_compliance_audit(report: DiagnosticReport) -> str:
    """Render local security findings as a concise remediation-oriented audit."""
    report = report.redacted_copy()
    findings = list(report.security_findings)
    for section in report.sections.values():
        findings.extend(section.security_findings)

    lines = [
        "# NVIDIA Agent Doctor — Security Readiness Audit",
        "",
        "> This report maps local diagnostic evidence to generic control areas. It is not a",
        "> certification, legal opinion, or an assessment against any named compliance framework.",
        "",
        f"**Security findings:** {len(findings)}",
        "",
        "## Evidence and remediation",
        "",
    ]
    if not findings:
        lines.append("No security findings were produced by the enabled local checks.")
        lines.append("This does not establish that the environment is secure or compliant.")
    for finding in findings:
        lines.extend(
            [
                f"### [{finding.severity.value}] {finding.title}",
                f"- **Control area:** {finding.component}",
                f"- **Evidence:** {finding.description}",
                f"- **Remediation:** {finding.recommendation}",
                "",
            ]
        )
    return "\n".join(lines)
