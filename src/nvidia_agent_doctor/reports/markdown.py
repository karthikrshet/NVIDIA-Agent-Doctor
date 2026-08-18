"""NVIDIA Agent Doctor — Markdown report generator."""

from __future__ import annotations

from nvidia_agent_doctor.core.result import DiagnosticReport, SectionResult


def render_markdown(report: DiagnosticReport) -> str:
    """Generate a Markdown report from a DiagnosticReport."""
    report = report.redacted_copy()
    lines: list[str] = []

    lines.append("# NVIDIA Agent Doctor — Diagnostic Report")
    lines.append("")
    lines.append(f"**Generated:** {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Version:** {report.tool.version}")
    lines.append(f"**Overall Health:** {report.overall_score}/100")
    lines.append(f"**Warnings:** {report.total_warnings}")
    lines.append(f"**Errors:** {report.total_errors}")
    lines.append("")
    lines.append("> **Disclaimer:** " + report.tool.disclaimer)
    lines.append("> " + report.tool.privacy)
    lines.append("")
    lines.append("---")
    lines.append("")

    # Per-section results
    for section in report.sections.values():
        lines.extend(_render_section_md(section))

    # Security findings
    all_findings = list(report.security_findings)
    for section in report.sections.values():
        all_findings.extend(section.security_findings)

    if all_findings:
        lines.append("## Security Findings")
        lines.append("")
        for finding in all_findings:
            lines.append(f"### [{finding.severity.value}] {finding.title}")
            lines.append(f"**Component:** {finding.component}")
            lines.append(f"**Description:** {finding.description}")
            lines.append(f"**Recommendation:** {finding.recommendation}")
            lines.append("")

    # Recommendations
    recs = report.all_recommendations
    if recs:
        lines.append("## Recommendations")
        lines.append("")
        for i, rec in enumerate(recs, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    return "\n".join(lines)


def _render_section_md(section: SectionResult) -> list[str]:
    lines: list[str] = []
    sev = section.overall_severity
    icon = {
        "PASS": "✅",
        "WARNING": "WARNING",
        "ERROR": "❌",
        "NOT_INSTALLED": "➖",
        "NOT_APPLICABLE": "N/A",
        "UNKNOWN": "❓",
    }.get(sev.value, "")

    lines.append(f"## {icon} {section.display_name}")
    lines.append("")

    if not section.checks:
        lines.append("*No checks performed.*")
        lines.append("")
        return lines

    lines.append("| Check | Status | Details |")
    lines.append("|-------|--------|---------|")

    for check in section.checks:
        status = check.severity.value
        detail = (check.detail or "").replace("\n", " ")
        lines.append(f"| {check.name} | {status} | {check.message} {detail} |")

    lines.append("")

    # Recommendations
    recs = [c.recommendation for c in section.checks if c.recommendation]
    if recs:
        lines.append("**Recommendations:**")
        for rec in recs:
            lines.append(f"- {rec}")
        lines.append("")

    return lines


def write_markdown_report(report: DiagnosticReport, output_path: str) -> None:
    from pathlib import Path

    Path(output_path).write_text(render_markdown(report), encoding="utf-8")
