"""NVIDIA Agent Doctor — `nad security` subcommands."""

from __future__ import annotations

import typer
from rich import box
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Security analysis.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def security_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        scan()


@app.command("scan")
def scan(
    json_output: bool = typer.Option(False, "--json"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Perform a security analysis of the NVIDIA AI environment."""
    from nvidia_agent_doctor.analyzers.security import analyze_security
    from nvidia_agent_doctor.core.result import DiagnosticReport
    from nvidia_agent_doctor.reports.json_report import render_json
    from nvidia_agent_doctor.reports.terminal import _render_section

    console = Console()
    section = analyze_security()

    if json_output:
        report = DiagnosticReport()
        report.add_section(section)
        typer.echo(render_json(report))
        return

    _render_section(section, console)

    # Security findings table
    all_findings = section.security_findings
    if all_findings:
        console.print("\n[bold red]Security Findings[/bold red]")
        table = Table(box=box.SIMPLE_HEAVY, border_style="red", expand=True)
        table.add_column("Severity", style="bold", min_width=10)
        table.add_column("Title")
        table.add_column("Component", style="dim")

        for finding in all_findings:
            table.add_row(
                f"[{finding.severity.color}]{finding.severity.value}[/{finding.severity.color}]",
                finding.title,
                finding.component,
            )
            if verbose:
                table.add_row("", f"[dim]{finding.description}[/dim]", "")
                table.add_row("", f"[yellow]-> {finding.recommendation}[/yellow]", "")

        console.print(table)

    console.print("\n[dim]Note: Security scan is heuristic. Always verify findings manually.[/dim]")
