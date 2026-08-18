"""NVIDIA Agent Doctor — `nad benchmark` subcommands."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(help="Optional performance benchmarks (opt-in).", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def bench_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command("run")
def run(
    json_output: bool = typer.Option(False, "--json"),
    gpu_only: bool = typer.Option(False, "--gpu-only", help="Only run GPU benchmark."),
    confirm: bool = typer.Option(
        False, "--yes", "-y",
        help="Skip confirmation prompt."
    ),
) -> None:
    """
    Run performance benchmarks.

    WARNING: This will use GPU compute resources. It is NEVER run automatically
    during `nad doctor`. Benchmarks must be explicitly requested.
    """
    console = Console()

    if not confirm:
        console.print("[yellow]Benchmark will use GPU resources.[/yellow]")
        confirmed = typer.confirm("Proceed with benchmark?", default=False)
        if not confirmed:
            console.print("[dim]Benchmark cancelled.[/dim]")
            return

    from nvidia_agent_doctor.benchmark.runner import run_benchmarks
    results = run_benchmarks(gpu_only=gpu_only)

    if json_output:
        import json
        typer.echo(json.dumps(results, indent=2, default=str))
        return

    console.print("\n[bold]Benchmark Results[/bold]")
    console.print()
    for name, result in results.items():
        if result.get("error"):
            console.print(f"  [red]{name}[/red]: ERROR — {result['error']}")
        elif result.get("skipped"):
            console.print(f"  [dim]{name}[/dim]: skipped — {result.get('reason', '')}")
        else:
            console.print(f"  [green]{name}[/green]:")
            for k, v in result.items():
                if k not in ("error", "skipped", "reason"):
                    console.print(f"    {k}: {v}")

    console.print(
        "\n[dim]Benchmark results reflect this specific hardware configuration "
        "and workload at the time of measurement.[/dim]"
    )
