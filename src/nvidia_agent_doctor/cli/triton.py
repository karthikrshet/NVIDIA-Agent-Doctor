"""NVIDIA Triton Inference Server diagnostic CLI commands."""

from __future__ import annotations

import json
from typing import Any

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
    endpoint: str = typer.Option(
        "http://127.0.0.1:8000",
        "--endpoint",
        help="Local Triton HTTP base endpoint.",
    ),
    allow_local_request: bool = typer.Option(
        False,
        "--allow-local-request",
        help="Allow one read-only request to Triton's validated loopback ready endpoint.",
    ),
    timeout_seconds: int = typer.Option(
        5,
        "--timeout-seconds",
        min=1,
        max=30,
        help="Readiness request timeout in seconds.",
    ),
) -> None:
    """Inspect local Triton indicators and optionally check loopback readiness."""
    from nvidia_agent_doctor.integrations.triton import (
        check_local_triton_readiness,
        check_triton,
    )

    result = redact_data(check_triton())
    readiness = check_local_triton_readiness(
        endpoint,
        allow_request=allow_local_request,
        timeout_seconds=timeout_seconds,
    )
    result["readiness"] = readiness
    if json_output:
        typer.echo(json.dumps(result, indent=2, default=str))
        _exit_for_result(readiness)
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
    table.add_row("Readiness API", str(readiness["status"]))
    console.print(table)
    console.print(
        "\n[dim]No Triton request is made without --allow-local-request. The readiness "
        "probe never loads a model or runs inference.[/dim]"
    )
    _exit_for_result(readiness)


def _status(value: bool) -> str:
    return "[green]OK[/green]" if value else "[dim]not detected[/dim]"


def _exit_for_result(readiness: dict[str, Any]) -> None:
    """An explicitly requested unavailable readiness probe is a warning."""
    if readiness.get("status") in {"not_ready", "unavailable"}:
        raise typer.Exit(code=1)
