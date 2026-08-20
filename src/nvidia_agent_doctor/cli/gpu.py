"""NVIDIA Agent Doctor — `nad gpu` subcommands."""

from __future__ import annotations

import typer
from rich import box
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="NVIDIA GPU diagnostics.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def gpu_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command("info")
def gpu_info(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show detailed GPU information."""
    from nvidia_agent_doctor.collectors.gpu import collect_gpu_info, nvidia_smi_available

    console = Console()

    if not nvidia_smi_available():
        if json_output:
            import json

            typer.echo(
                json.dumps(
                    {
                        "available": False,
                        "gpus": [],
                        "reason": "nvidia-smi is unavailable",
                    }
                )
            )
            return
        console.print("[yellow]nvidia-smi not available.[/yellow]")
        console.print(
            "[dim]Possible reasons: no NVIDIA GPU, driver not installed, "
            "or running in unsupported environment.[/dim]"
        )
        return

    gpus = collect_gpu_info()
    if not gpus:
        if json_output:
            import json

            typer.echo(json.dumps({"available": True, "gpus": [], "reason": "no GPUs detected"}))
            return
        console.print("[yellow]No NVIDIA GPUs detected.[/yellow]")
        return

    if json_output:
        import json

        typer.echo(
            json.dumps(
                {"available": True, "gpus": [g.model_dump() for g in gpus]},
                indent=2,
                default=str,
            )
        )
        return

    for gpu in gpus:
        table = Table(
            title=f"GPU {gpu.index}: {gpu.name}",
            box=box.ROUNDED,
            border_style="bright_blue",
            show_header=False,
        )
        table.add_column("Property", style="dim", min_width=24)
        table.add_column("Value", style="bold white")

        table.add_row("Driver Version", gpu.driver_version or "N/A")
        table.add_row("CUDA Version (driver)", gpu.cuda_version or "N/A")
        table.add_row("Compute Capability", gpu.compute_capability or "N/A")
        if gpu.vram_total_gb is not None:
            vram_used = f"{gpu.vram_used_gb} GB used" if gpu.vram_used_gb is not None else ""
            table.add_row("VRAM", f"{gpu.vram_total_gb} GB  {vram_used}")
        if gpu.utilization_gpu_pct is not None:
            table.add_row("GPU Utilization", f"{gpu.utilization_gpu_pct}%")
        if gpu.temperature_c is not None:
            temp_style = (
                "red"
                if gpu.temperature_c >= 90
                else "yellow"
                if gpu.temperature_c >= 80
                else "green"
            )
            table.add_row("Temperature", f"[{temp_style}]{gpu.temperature_c}°C[/{temp_style}]")
        if gpu.power_draw_w is not None:
            table.add_row("Power Draw", f"{gpu.power_draw_w}W / {gpu.power_limit_w or '?'}W")
        if gpu.uuid:
            table.add_row("UUID", gpu.uuid[:20] + "…")

        console.print(table)
        console.print()


@app.command("health")
def gpu_health(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Perform GPU health checks."""
    from nvidia_agent_doctor.analyzers.environment import analyze_gpu
    from nvidia_agent_doctor.core.result import DiagnosticReport
    from nvidia_agent_doctor.reports.json_report import render_json
    from nvidia_agent_doctor.reports.terminal import _render_section

    console = Console()
    section = analyze_gpu()

    if json_output:
        report = DiagnosticReport()
        report.add_section(section)
        typer.echo(render_json(report))
    else:
        _render_section(section, console)

    if section.exit_code:
        raise typer.Exit(code=section.exit_code)


@app.command("topology")
def gpu_topology(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show supported GPU-to-GPU topology without exposing host affinity data."""
    import json

    from nvidia_agent_doctor.collectors.gpu import collect_gpu_topology

    result = collect_gpu_topology()
    if json_output:
        typer.echo(json.dumps(result, indent=2))
        return

    console = Console()
    if result["status"] != "available":
        console.print(f"[yellow]{result['reason']}[/yellow]")
        console.print(
            "[dim]Topology is optional and depends on the installed NVIDIA driver. "
            "No raw topology output, CPU affinity, or PCI identifiers are displayed.[/dim]"
        )
        return

    console.print(f"[bold]GPU topology:[/bold] {result['gpu_count']} GPU(s)")
    links = result["links"]
    if not links:
        console.print(
            "[dim]No GPU-to-GPU interconnects reported (single GPU or no matrix links).[/dim]"
        )
        return

    table = Table(box=box.ROUNDED, border_style="bright_blue")
    table.add_column("From", style="bold")
    table.add_column("To", style="bold")
    table.add_column("Link class")
    for link in links:
        table.add_row(link["from"], link["to"], link["link"])
    console.print(table)
    console.print(
        "[dim]Link classes come from nvidia-smi; this command does not infer PCIe or NVLink topology.[/dim]"
    )
