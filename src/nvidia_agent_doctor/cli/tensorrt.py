"""NVIDIA TensorRT diagnostic CLI commands."""

from __future__ import annotations

import json
from typing import Any

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from nvidia_agent_doctor.security.credentials import redact_data

app = typer.Typer(help="TensorRT diagnostics.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def tensorrt_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        check()


@app.command("check")
def check(
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Inspect the local TensorRT Python binding without building an engine."""
    from nvidia_agent_doctor.integrations.tensorrt import check_tensorrt

    result = redact_data(check_tensorrt())
    if json_output:
        typer.echo(json.dumps(result, indent=2, default=str))
        _exit_for_result(result)
        return

    console = Console()
    console.print("[bold]TensorRT Diagnostics[/bold]\n")
    table = Table(box=box.ROUNDED, border_style="bright_blue", show_header=False)
    table.add_column("Check", style="dim", min_width=24)
    table.add_column("Result")
    table.add_row("Installed", _status(bool(result.get("installed"))))
    if result.get("installed"):
        table.add_row("Version", str(result.get("version") or "unknown"))
        table.add_row("Python bindings", _status(bool(result.get("python_bindings"))))
        table.add_row("Runtime object", _status(result.get("runtime_available") is True))
        table.add_row("Builder object", _status(result.get("builder_available") is True))
        table.add_row(
            "PyTorch CUDA context",
            _status(result.get("pytorch_cuda_available") is True),
        )
    console.print(table)
    if result.get("error"):
        console.print(f"\n[red]TensorRT error:[/red] {result['error']}")
    console.print(
        "\n[dim]This command does not build an engine or establish TensorRT/CUDA "
        "support-matrix compatibility. Consult NVIDIA's TensorRT Support Matrix.[/dim]"
    )
    _exit_for_result(result)


def _status(value: bool) -> str:
    return "[green]OK[/green]" if value else "[dim]not available[/dim]"


def _exit_for_result(result: dict[str, Any]) -> None:
    """Return errors only for an installed runtime that cannot be probed."""
    if result.get("error"):
        raise typer.Exit(code=2)
    if result.get("installed") and result.get("runtime_available") is False:
        raise typer.Exit(code=1)
