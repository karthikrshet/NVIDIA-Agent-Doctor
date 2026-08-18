"""NVIDIA Agent Doctor — `nad compatibility` subcommands."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(help="Compatibility checks.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def compat_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        check()


@app.command("check")
def check(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Check cross-component compatibility (GPU, Driver, CUDA, PyTorch, TensorRT)."""
    from nvidia_agent_doctor.analyzers.compatibility import analyze_compatibility
    from nvidia_agent_doctor.core.result import DiagnosticReport
    from nvidia_agent_doctor.reports.json_report import render_json
    from nvidia_agent_doctor.reports.terminal import _render_section

    console = Console()
    section = analyze_compatibility()

    if json_output:
        report = DiagnosticReport()
        report.add_section(section)
        typer.echo(render_json(report))
    else:
        _render_section(section, console)
