"""NVIDIA Triton Inference Server diagnostic CLI commands."""

from __future__ import annotations

import json

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from nvidia_agent_doctor.security.credentials import redact_data

app = typer.Typer(help="Triton Inference Server diagnostics.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def triton_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        check()


@app.command("check")
def check(
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Inspect local Triton server, client, process, and container indicators."""
    from nvidia_agent_doctor.integrations.triton import check_triton

    result = redact_data(check_triton())
    if json_output:
        typer.echo(json.dumps(result, indent=2, default=str))
        return

    console = Console()
    console.print("[bold]Triton Inference Server Diagnostics[/bold]\n")
    table = Table(box=box.ROUNDED, border_style="bright_blue", show_header=False)
    table.add_column("Check", style="dim", min_width=24)
    table.add_column("Result")
    table.add_row("Server detected", _status(bool(result.get("installed"))))
    table.add_row("Source", str(result.get("source") or "none"))
    table.add_row("Version", str(result.get("version") or "unknown"))
    table.add_row("Python client", _status(bool(result.get("client_available"))))
    table.add_row("Server process", _status(bool(result.get("server_process_detected"))))
    console.print(table)
    console.print(
        "\n[dim]Detection does not contact a Triton endpoint, load a model, or run inference.[/dim]"
    )


def _status(value: bool) -> str:
    return "[green]OK[/green]" if value else "[dim]not detected[/dim]"
