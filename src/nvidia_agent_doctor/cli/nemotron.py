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
    from nvidia_agent_doctor.integrations.nemotron import detect_nemotron, detect_nemoclaw
    from rich.table import Table
    from rich import box

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

    table.add_row("NeMo Installed",
                  "[green]✓[/green]" if nem.get("nemo_installed") else "[dim]–[/dim]")
    if nem.get("nemo_version"):
        table.add_row("NeMo Version", nem["nemo_version"])
    table.add_row("NIM Available",
                  "[green]✓[/green]" if nem.get("nim_available") else "[dim]–[/dim]")
    table.add_row("NGC CLI",
                  "[green]✓[/green]" if nem.get("ngc_cli") else "[dim]–[/dim]")
    table.add_row("NemoClaw Installed",
                  "[green]✓[/green]" if claw.get("installed") else "[dim]–[/dim]")
    if claw.get("version"):
        table.add_row("NemoClaw Version", claw["version"])

    console.print(table)


@app.command("benchmark")
def benchmark(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
) -> None:
    """
    Run a Nemotron inference benchmark (opt-in, requires NeMo installation).

    This command will allocate GPU memory and run inference. It is never run
    automatically during `nad doctor`.
    """
    console = Console()

    if not confirm:
        confirmed = typer.confirm(
            "Nemotron benchmark will use GPU memory and run inference. Proceed?",
            default=False,
        )
        if not confirmed:
            console.print("[dim]Benchmark cancelled.[/dim]")
            return

    console.print("[dim]Nemotron benchmark requires NeMo to be installed and a model configured.[/dim]")
    console.print("[dim]To run: configure a model path in .nvidia-agent-doctor.toml[/dim]")
    console.print("\n[yellow]Nemotron benchmark not yet available in this version.[/yellow]")
    console.print("[dim]See roadmap in README for v0.3 timeline.[/dim]")
