"""NVIDIA Agent Doctor — `nad cuda` subcommands."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(help="CUDA diagnostics.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def cuda_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        check()


@app.command("check")
def check(
    json_output: bool = typer.Option(False, "--json"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Check CUDA installation and configuration."""
    from nvidia_agent_doctor.analyzers.environment import analyze_cuda
    from nvidia_agent_doctor.reports.terminal import _render_section
    from nvidia_agent_doctor.reports.json_report import render_json
    from nvidia_agent_doctor.core.result import DiagnosticReport

    console = Console()
    section = analyze_cuda()

    if json_output:
        report = DiagnosticReport()
        report.add_section(section)
        typer.echo(render_json(report))
    else:
        _render_section(section, console)
        if verbose and section.metadata.get("cuda_info"):
            import json
            console.print("\n[dim]Full CUDA info:[/dim]")
            console.print(json.dumps(section.metadata["cuda_info"], indent=2, default=str))
