"""NVIDIA Agent Doctor — Self-contained HTML report generator."""

from __future__ import annotations

from nvidia_agent_doctor.core.result import DiagnosticReport


_SEVERITY_COLORS = {
    "PASS": "#22c55e",
    "WARNING": "#f59e0b",
    "ERROR": "#ef4444",
    "NOT_INSTALLED": "#6b7280",
    "NOT_APPLICABLE": "#9ca3af",
    "UNKNOWN": "#3b82f6",
}

_SEVERITY_ICONS = {
    "PASS": "✓",
    "WARNING": "⚠",
    "ERROR": "✗",
    "NOT_INSTALLED": "–",
    "NOT_APPLICABLE": "·",
    "UNKNOWN": "?",
}

_SEC_COLORS = {
    "INFO": "#06b6d4",
    "LOW": "#3b82f6",
    "MEDIUM": "#f59e0b",
    "HIGH": "#ef4444",
    "CRITICAL": "#7c3aed",
}


def render_html(report: DiagnosticReport) -> str:
    """Generate a self-contained HTML report."""
    score = report.overall_score
    score_color = "#22c55e" if score >= 90 else "#f59e0b" if score >= 70 else "#ef4444"
    ts = report.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    sections_html = ""
    for section in report.sections.values():
        sev = section.overall_severity
        icon = _SEVERITY_ICONS.get(sev.value, "?")
        color = _SEVERITY_COLORS.get(sev.value, "#9ca3af")
        checks_rows = ""
        for check in section.checks:
            c_color = _SEVERITY_COLORS.get(check.severity.value, "#9ca3af")
            c_icon = _SEVERITY_ICONS.get(check.severity.value, "?")
            detail = check.detail or ""
            rec = f'<br><span class="rec">→ {check.recommendation}</span>' if check.recommendation else ""
            checks_rows += f"""
            <tr>
                <td>{check.name}</td>
                <td><span class="badge" style="background:{c_color}">{c_icon} {check.severity.value}</span></td>
                <td>{check.message}<br><small style="color:#9ca3af">{detail}</small>{rec}</td>
            </tr>"""

        sections_html += f"""
        <div class="section">
            <h2><span style="color:{color}">{icon}</span> {section.display_name}</h2>
            <table>
                <thead><tr><th>Check</th><th>Status</th><th>Details</th></tr></thead>
                <tbody>{checks_rows}</tbody>
            </table>
        </div>"""

    recs_html = ""
    for i, rec in enumerate(report.all_recommendations[:20], 1):
        recs_html += f"<li>{rec}</li>"

    findings_html = ""
    all_findings = list(report.security_findings)
    for section in report.sections.values():
        all_findings.extend(section.security_findings)
    for finding in all_findings:
        color = _SEC_COLORS.get(finding.severity.value, "#9ca3af")
        findings_html += f"""
        <div class="finding">
            <span class="badge" style="background:{color}">{finding.severity.value}</span>
            <strong>{finding.title}</strong>
            <p>{finding.description}</p>
            <p><em>Recommendation: {finding.recommendation}</em></p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NVIDIA Agent Doctor Report</title>
    <style>
        :root {{
            --bg: #0f172a; --surface: #1e293b; --border: #334155;
            --text: #f1f5f9; --dim: #94a3b8; --accent: #3b82f6;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background: var(--bg); color: var(--text); font-family: system-ui, sans-serif;
               line-height: 1.6; padding: 2rem; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        header {{ text-align: center; margin-bottom: 2rem; }}
        header h1 {{ font-size: 2rem; background: linear-gradient(135deg, #3b82f6, #8b5cf6);
                    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        header p {{ color: var(--dim); margin-top: 0.5rem; }}
        .score-card {{ background: var(--surface); border: 1px solid var(--border);
                      border-radius: 12px; padding: 1.5rem; margin: 1.5rem 0;
                      display: flex; align-items: center; gap: 2rem; }}
        .score-number {{ font-size: 3rem; font-weight: bold; color: {score_color}; }}
        .score-label {{ color: var(--dim); font-size: 0.875rem; }}
        .stats {{ display: flex; gap: 2rem; }}
        .stat {{ text-align: center; }}
        .stat-value {{ font-size: 1.5rem; font-weight: bold; }}
        .stat-label {{ color: var(--dim); font-size: 0.75rem; }}
        .section {{ background: var(--surface); border: 1px solid var(--border);
                   border-radius: 12px; padding: 1.5rem; margin: 1rem 0; }}
        .section h2 {{ margin-bottom: 1rem; font-size: 1.1rem; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ text-align: left; padding: 0.5rem; color: var(--dim); font-size: 0.75rem;
             border-bottom: 1px solid var(--border); text-transform: uppercase; letter-spacing: 0.05em; }}
        td {{ padding: 0.5rem; border-bottom: 1px solid #1e293b; font-size: 0.875rem; vertical-align: top; }}
        .badge {{ padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem;
                 color: white; font-weight: bold; display: inline-block; }}
        .rec {{ color: #f59e0b; font-size: 0.8rem; }}
        .finding {{ background: #0f172a; border-left: 3px solid var(--border);
                   padding: 1rem; margin: 0.5rem 0; border-radius: 0 8px 8px 0; }}
        .finding p {{ margin-top: 0.5rem; font-size: 0.875rem; color: var(--dim); }}
        ul, ol {{ padding-left: 1.5rem; color: var(--dim); font-size: 0.875rem; }}
        li {{ margin: 0.25rem 0; }}
        footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border);
                 color: var(--dim); font-size: 0.75rem; text-align: center; }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>🩺 NVIDIA Agent Doctor</h1>
        <p>Independent Open-Source Diagnostic Toolkit</p>
        <p style="margin-top:0.25rem">Generated: {ts} &nbsp;|&nbsp; Version: {report.tool.version}</p>
    </header>

    <div class="score-card">
        <div>
            <div class="score-number">{score}</div>
            <div class="score-label">Overall Health Score</div>
        </div>
        <div class="stats">
            <div class="stat">
                <div class="stat-value" style="color:#f59e0b">{report.total_warnings}</div>
                <div class="stat-label">Warnings</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color:#ef4444">{report.total_errors}</div>
                <div class="stat-label">Errors</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color:#3b82f6">{report.total_security_findings}</div>
                <div class="stat-label">Security Findings</div>
            </div>
        </div>
    </div>

    {sections_html}

    {"<div class='section'><h2>🔐 Security Findings</h2>" + findings_html + "</div>" if findings_html else ""}

    {"<div class='section'><h2>💡 Recommendations</h2><ol>" + recs_html + "</ol></div>" if recs_html else ""}

    <footer>
        <p>{report.tool.disclaimer}</p>
        <p>{report.tool.privacy}</p>
    </footer>
</div>
</body>
</html>"""


def write_html_report(report: DiagnosticReport, output_path: str) -> None:
    from pathlib import Path
    Path(output_path).write_text(render_html(report), encoding="utf-8")
