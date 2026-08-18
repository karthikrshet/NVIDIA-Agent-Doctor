"""NVIDIA Agent Doctor — `nad nemoclaw` subcommands (alias for nemotron module)."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(help="NemoClaw diagnostics.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def claw_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        check()


@app.command("check")
def check(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Check NemoClaw installation."""
    from rich import box
    from rich.table import Table

    from nvidia_agent_doctor.integrations.nemotron import detect_nemoclaw

    console = Console()
    claw = detect_nemoclaw()

    if json_output:
        import json

        typer.echo(json.dumps(claw, indent=2, default=str))
        return

    console.print("[bold]NemoClaw Diagnostics[/bold]\n")
    console.print(f"[dim]{claw.get('note', '')}[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="bright_blue", show_header=False)
    table.add_column("Component", style="dim", min_width=22)
    table.add_column("Status")

    table.add_row(
        "NemoClaw Installed", "[green]✓[/green]" if claw.get("installed") else "[dim]–[/dim]"
    )
    table.add_row(
        "CLI Available", "[green]✓[/green]" if claw.get("cli_available") else "[dim]–[/dim]"
    )
    if claw.get("version"):
        table.add_row("Version", claw["version"])

    console.print(table)

    if not claw.get("installed"):
        console.print("\n[dim]NemoClaw not detected. This is optional.[/dim]")
