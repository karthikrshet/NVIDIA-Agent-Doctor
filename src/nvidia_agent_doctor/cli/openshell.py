"""NVIDIA Agent Doctor — `nad openshell` subcommands."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(help="OpenShell diagnostics.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def osh_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        diagnose()


@app.command("diagnose")
def diagnose(
    json_output: bool = typer.Option(False, "--json"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Diagnose OpenShell installation and runtime state."""
    from rich import box
    from rich.table import Table

    from nvidia_agent_doctor.integrations.openshell import detect_openshell

    console = Console()
    info = detect_openshell()

    if json_output:
        import json

        typer.echo(json.dumps(info, indent=2, default=str))
        return

    if not info["installed"]:
        console.print("[dim]OpenShell not detected.[/dim]")
        console.print(f"[dim]{info.get('note', '')}[/dim]")
        return

    console.print("[bold]OpenShell Diagnostics[/bold]\n")

    table = Table(box=box.ROUNDED, border_style="bright_blue", show_header=False)
    table.add_column("Component", style="dim", min_width=22)
    table.add_column("Status")

    checks = [
        ("Installation", info.get("installed")),
        ("CLI Available", info.get("cli_available")),
        ("Runtime Running", info.get("runtime_running")),
        ("Sandbox Active", info.get("sandbox_active")),
        ("Policy Configured", info.get("policy_configured")),
        ("Network Configured", info.get("network_configured")),
        ("Credentials Configured", info.get("credentials_configured")),
        ("Observability Configured", info.get("observability_configured")),
    ]

    score = 0
    total = 0
    for label, value in checks:
        if value is True:
            status = "[green]✓[/green]"
            score += 1
        elif value is False:
            status = "[yellow]⚠[/yellow]"
        elif value is None:
            status = "[dim]–[/dim]"
        else:
            status = "[dim]?[/dim]"
        if value is not None:
            total += 1
        table.add_row(label, status)

    console.print(table)

    if total > 0:
        health = round((score / total) * 100)
        color = "green" if health >= 80 else "yellow" if health >= 60 else "red"
        console.print(f"\n[bold]Overall Health: [{color}]{health}/100[/{color}][/bold]")

    if verbose:
        console.print(f"\n[dim]Config: {info.get('config_path') or 'not found'}[/dim]")
        console.print(f"[dim]Version: {info.get('version') or 'unknown'}[/dim]")
        console.print(f"\n[dim]{info.get('note', '')}[/dim]")
