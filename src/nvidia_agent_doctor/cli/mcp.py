"""NVIDIA Agent Doctor — `nad mcp` subcommands."""

from __future__ import annotations

import typer
from rich import box
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="MCP configuration analysis.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def mcp_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        scan()


@app.command("scan")
def scan(
    json_output: bool = typer.Option(False, "--json"),
    verbose: bool = typer.Option(False, "--verbose"),
    config_path: list[str] = typer.Option([], "--config", help="Additional MCP config paths."),
) -> None:
    """Discover and analyze MCP server configurations."""
    from nvidia_agent_doctor.integrations.mcp import discover_mcp_servers
    from nvidia_agent_doctor.security.credentials import redact_data
    from nvidia_agent_doctor.security.mcp import analyze_mcp_server

    console = Console()
    servers = discover_mcp_servers(extra_paths=config_path if config_path else None)

    if json_output:
        import json

        result = []
        for server in servers:
            findings = analyze_mcp_server(server)
            result.append(
                {
                    "server": redact_data(server.model_dump()),
                    "findings": [{**f, "severity": f["severity"].value} for f in findings],
                }
            )
        typer.echo(json.dumps(result, indent=2))
        return

    if not servers:
        console.print("[dim]No MCP server configurations found.[/dim]")
        console.print("[dim]Searched: ~/.mcp/config.json, ~/.mcp.json, ./.mcp.json[/dim]")
        return

    console.print(f"\n[bold]Found {len(servers)} MCP server(s)[/bold]\n")

    table = Table(box=box.ROUNDED, border_style="bright_blue", expand=True)
    table.add_column("Server", style="bold white")
    table.add_column("Transport", style="dim")
    table.add_column("Command", style="dim")
    table.add_column("Risk Level", justify="center")

    for server in servers:
        findings = analyze_mcp_server(server)
        max_severity = max(findings, key=lambda f: f["severity"].score)["severity"]

        table.add_row(
            server.name,
            server.transport or "stdio",
            server.command or "N/A",
            f"[{max_severity.color}]{max_severity.value}[/{max_severity.color}]",
        )

    console.print(table)

    if verbose:
        console.print()
        for server in servers:
            findings = analyze_mcp_server(server)
            console.print(f"\n[bold]{server.name}[/bold]")
            console.print(f"  Config: {server.config_path}")
            for finding in findings:
                sev = finding["severity"]
                console.print(f"  [{sev.color}]{sev.value}[/{sev.color}] {finding['title']}")
                console.print(f"    {finding['description']}")
                console.print(f"    [yellow]-> {finding['recommendation']}[/yellow]")

    console.print(
        "\n[dim]Note: MCP security analysis is heuristic. Verify all findings manually.[/dim]"
        "\n[dim]Secret values are redacted and never displayed.[/dim]"
    )
