"""NVIDIA Agent Doctor — Beautiful terminal report renderer using Rich."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from nvidia_agent_doctor.core.result import CheckResult, DiagnosticReport, SectionResult


def render_report(report: DiagnosticReport, console: Console | None = None) -> None:
    """Render a full diagnostic report to the terminal."""
    if console is None:
        console = Console()

    _render_header(console)
    console.print()

    for section in report.sections.values():
        _render_section(section, console)

    _render_summary(report, console)
    _render_disclaimer(console)


def render_doctor_summary(report: DiagnosticReport, console: Console | None = None) -> None:
    """Render the compact doctor-style summary panel."""
    if console is None:
        console = Console()

    _render_header(console)
    console.print()

    # Build summary table
    table = Table(
        box=box.ROUNDED,
        show_header=False,
        expand=True,
        border_style="bright_black",
        padding=(0, 2),
    )
    table.add_column("Component", style="bold white", min_width=24)
    table.add_column("Status", justify="right", min_width=14)

    display_names = {
        "system": "System",
        "gpu": "NVIDIA GPU",
        "cuda": "CUDA",
        "pytorch": "PyTorch",
        "tensorrt": "TensorRT",
        "triton": "Triton",
        "docker": "Docker",
        "openshell": "OpenShell",
        "nemoclaw": "NemoClaw",
        "nemotron": "Nemotron",
        "mcp": "MCP",
        "skills": "Agent Skills",
        "security": "Security",
        "compatibility": "Compatibility",
    }

    for name, section in report.sections.items():
        display = display_names.get(name, section.display_name)
        sev = section.overall_severity
        icon = sev.icon
        color = sev.color
        status_text = Text(f"{icon}  {sev.value}", style=color)
        table.add_row(display, status_text)

    console.print(table)
    console.print()
    _render_summary(report, console)
    _render_disclaimer(console)


def _render_header(console: Console) -> None:
    """Render the NVIDIA Agent Doctor banner."""
    header_text = Text()
    header_text.append("  NVIDIA AGENT DOCTOR  ", style="bold white on dark_blue")
    header_text.append("\n")
    header_text.append("  Independent Open-Source Diagnostic Toolkit  ", style="dim white")

    console.print(
        Panel(
            header_text,
            border_style="bright_blue",
            expand=False,
            padding=(0, 4),
        )
    )


def _render_section(section: SectionResult, console: Console) -> None:
    """Render a single section with all its checks."""
    sev = section.overall_severity
    section_title = Text()
    section_title.append(f"{sev.icon} ", style=sev.color)
    section_title.append(section.display_name, style="bold")

    console.print(section_title)

    for check in section.checks:
        _render_check_line(check, console, indent="   ")

    if section.security_findings:
        console.print("   [dim]Security findings:[/dim]")
        for finding in section.security_findings:
            console.print(
                f"   [{finding.severity.color}]{finding.severity.value}[/] {finding.title}"
            )

    console.print()


def _render_check_line(check: CheckResult, console: Console, indent: str = "") -> None:
    """Render a single check result line."""
    icon = check.severity.icon
    color = check.severity.color

    line = Text()
    line.append(f"{indent}{icon} ", style=color)
    line.append(check.message)

    console.print(line)

    if check.detail:
        console.print(f"{indent}   [dim]{check.detail}[/dim]")

    if check.recommendation:
        console.print(f"{indent}   [yellow]-> {check.recommendation}[/yellow]")


def _render_summary(report: DiagnosticReport, console: Console) -> None:
    """Render the overall health score summary."""
    score = report.overall_score
    warnings = report.total_warnings
    errors = report.total_errors
    recs = len(report.all_recommendations)

    # Score bar
    if score >= 90:
        score_color = "bold green"
        bar_char = "#"
    elif score >= 70:
        score_color = "bold yellow"
        bar_char = "#"
    else:
        score_color = "bold red"
        bar_char = "#"

    bar_filled = round(score / 5)
    bar = bar_char * bar_filled + "." * (20 - bar_filled)

    summary = Table(box=None, show_header=False, padding=(0, 1))
    summary.add_column("", style="bold")
    summary.add_column("", style="")

    summary.add_row(
        "Overall Health:",
        Text(f"{score}/100  {bar}", style=score_color),
    )
    summary.add_row(
        "Warnings:",
        Text(str(warnings), style="yellow" if warnings else "green"),
    )
    summary.add_row(
        "Critical Issues:",
        Text(str(errors), style="red" if errors else "green"),
    )
    summary.add_row("Recommendations:", str(recs))

    console.print(
        Panel(
            summary,
            title="[bold]Diagnostic Summary[/bold]",
            border_style="bright_black",
            expand=False,
            padding=(0, 2),
        )
    )

    if report.all_recommendations:
        console.print("\n[bold]Recommendations:[/bold]")
        for i, rec in enumerate(report.all_recommendations[:10], 1):
            console.print(f"  {i}. {rec}")


def _render_disclaimer(console: Console) -> None:
    """Render the independence disclaimer."""
    console.print()
    console.print(
        "[dim]NVIDIA Agent Doctor is an independent open-source project "
        "and is not affiliated with or endorsed by NVIDIA Corporation. "
        "All diagnostics are local-only. No telemetry.[/dim]"
    )
