"""NVIDIA Agent Doctor — `nad nemotron` subcommands."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(help="Nemotron / NeMo diagnostics.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def nem_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        check()


@app.command("check")
def check(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Check Nemotron / NeMo installation."""
    from rich import box
    from rich.table import Table

    from nvidia_agent_doctor.integrations.nemotron import detect_nemoclaw, detect_nemotron

    console = Console()
    nem = detect_nemotron()
    claw = detect_nemoclaw()

    if json_output:
        import json

        typer.echo(json.dumps({"nemotron": nem, "nemoclaw": claw}, indent=2, default=str))
        return

    console.print("[bold]Nemotron / NeMo Diagnostics[/bold]\n")
    console.print(f"[dim]{nem.get('note', '')}[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="bright_blue", show_header=False)
    table.add_column("Component", style="dim", min_width=22)
    table.add_column("Status")

    table.add_row(
        "NeMo Installed", "[green]OK[/green]" if nem.get("nemo_installed") else "[dim]-[/dim]"
    )
    if nem.get("nemo_version"):
        table.add_row("NeMo Version", nem["nemo_version"])
    table.add_row(
        "NIM Available", "[green]OK[/green]" if nem.get("nim_available") else "[dim]-[/dim]"
    )
    table.add_row("NGC CLI", "[green]OK[/green]" if nem.get("ngc_cli") else "[dim]-[/dim]")
    table.add_row(
        "NemoClaw Installed", "[green]OK[/green]" if claw.get("installed") else "[dim]-[/dim]"
    )
    if claw.get("version"):
        table.add_row("NemoClaw Version", claw["version"])

    console.print(table)


@app.command("nim")
def nim(
    endpoint: str = typer.Option("http://127.0.0.1:8000", "--endpoint"),
    allow_local_request: bool = typer.Option(
        False,
        "--allow-local-request",
        help="Allow a read-only request to the validated local NIM readiness endpoint.",
    ),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Check a local NVIDIA NIM readiness endpoint without sending inference."""
    import json

    from nvidia_agent_doctor.integrations.nim import check_local_nim

    result = check_local_nim(endpoint, allow_request=allow_local_request)
    if json_output:
        typer.echo(json.dumps(result, indent=2))
    else:
        console = Console()
        console.print(f"Local NIM status: {result['status']}")
        if result.get("recommendation"):
            console.print(f"[yellow]{result['recommendation']}[/yellow]")
