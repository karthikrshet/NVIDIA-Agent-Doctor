"""NVIDIA Agent Doctor — `nad mcp` subcommands."""

from __future__ import annotations

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from nvidia_agent_doctor.core.severity import SecuritySeverity

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
    from nvidia_agent_doctor.cli.main import get_config
    from nvidia_agent_doctor.integrations.mcp import discover_mcp_servers
    from nvidia_agent_doctor.security.credentials import redact_data
    from nvidia_agent_doctor.security.mcp import analyze_mcp_server

    console = Console()
    configured_paths = get_config().mcp.config_paths
    servers = discover_mcp_servers(extra_paths=[*configured_paths, *config_path])
    server_findings = [(server, analyze_mcp_server(server)) for server in servers]

    if json_output:
        import json

        result = []
        for server, findings in server_findings:
            result.append(
                {
                    "server": redact_data(server.model_dump()),
                    "findings": [
                        redact_data({**f, "severity": f["severity"].value}) for f in findings
                    ],
                }
            )
        typer.echo(json.dumps(result, indent=2))
    else:
        if not servers:
            console.print("[dim]No MCP server configurations found.[/dim]")
            console.print("[dim]Searched: ~/.mcp/config.json, ~/.mcp.json, ./.mcp.json[/dim]")
        else:
            console.print(f"\n[bold]Found {len(servers)} MCP server(s)[/bold]\n")

            table = Table(box=box.ROUNDED, border_style="bright_blue", expand=True)
            table.add_column("Server", style="bold white")
            table.add_column("Transport", style="dim")
            table.add_column("Command", style="dim")
            table.add_column("Risk Level", justify="center")

            for server, findings in server_findings:
                max_severity = max(findings, key=lambda f: f["severity"].score)["severity"]

                table.add_row(
                    redact_data(server.name),
                    redact_data(server.transport or "stdio"),
                    redact_data(server.command or "N/A"),
                    f"[{max_severity.color}]{max_severity.value}[/{max_severity.color}]",
                )

            console.print(table)

            if verbose:
                console.print()
                for server, findings in server_findings:
                    console.print(f"\n[bold]{redact_data(server.name)}[/bold]")
                    console.print(f"  Config: {redact_data(str(server.config_path))}")
                    for finding in findings:
                        safe_finding = redact_data(
                            {key: value for key, value in finding.items() if key != "severity"}
                        )
                        sev = finding["severity"]
                        console.print(
                            f"  [{sev.color}]{sev.value}[/{sev.color}] {safe_finding['title']}"
                        )
                        console.print(f"    {safe_finding['description']}")
                        console.print(f"    [yellow]-> {safe_finding['recommendation']}[/yellow]")

            console.print(
                "\n[dim]Note: MCP security analysis is heuristic. Verify all findings manually.[/dim]"
                "\n[dim]Secret values are redacted and never displayed.[/dim]"
            )

    _exit_for_findings([finding for _, findings in server_findings for finding in findings])


def _exit_for_findings(findings: list[dict[str, object]]) -> None:
    """Map heuristic MCP severities to the documented diagnostic exit codes."""
    severities = {finding["severity"] for finding in findings}
    if SecuritySeverity.HIGH in severities or SecuritySeverity.CRITICAL in severities:
        raise typer.Exit(code=3)
    if SecuritySeverity.MEDIUM in severities or SecuritySeverity.LOW in severities:
        raise typer.Exit(code=1)
