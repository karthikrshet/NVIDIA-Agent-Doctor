"""CLI for safe agent workflow preflight checks."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from nvidia_agent_doctor.agent_test import run_agent_preflight


def test_agent(
    skills_directory: Path = typer.Argument(Path("."), help="Directory containing SKILL.md files."),
    mcp_config: list[str] = typer.Option([], "--mcp-config", help="Additional MCP configuration files."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Safely preflight agent inputs without executing tools or network calls."""
    from nvidia_agent_doctor.cli.main import get_config

    config = get_config()
    result = run_agent_preflight(
        skills_directory,
        [*config.mcp.config_paths, *mcp_config],
        config.skills.scan_depth,
    )
    if json_output:
        typer.echo(json.dumps(result, indent=2))
    else:
        console = Console()
        console.print("Agent workflow static preflight (no tools, servers, or models were executed).")
        for check in result["checks"]:
            console.print(f"{check['status']}: {check['kind']} — {check['evidence']}")
        console.print(f"Exit code: {result['exit_code']}")
    if result["exit_code"]:
        raise typer.Exit(code=int(result["exit_code"]))
