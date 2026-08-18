"""CLI for explicit, read-only Kubernetes cluster scans."""

from __future__ import annotations

import json

import typer
from rich.console import Console

from nvidia_agent_doctor.cluster import scan_cluster

app = typer.Typer(help="Kubernetes cluster diagnostics.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def cluster_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        scan()


@app.command("scan")
def scan(
    allow_cluster_access: bool = typer.Option(
        False,
        "--allow-cluster-access",
        help="Allow read-only kubectl queries against the current configured context.",
    ),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Inspect node GPU capacity and GPU Operator pods using fixed kubectl queries."""
    result = scan_cluster(allow_cluster_access=allow_cluster_access)
    if json_output:
        typer.echo(json.dumps(result, indent=2))
        return
    console = Console()
    console.print(f"Cluster status: {result['status']}")
    for node in result["nodes"]:
        console.print(
            f"  {node['name']}: {'Ready' if node['ready'] else 'NotReady'}, GPU capacity={node['gpu_capacity']}"
        )
    if result.get("recommendation"):
        console.print(f"[yellow]{result['recommendation']}[/yellow]")
