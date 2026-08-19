"""Docker GPU validation CLI commands."""

from __future__ import annotations

import json
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from nvidia_agent_doctor.integrations.docker_gpu import DEFAULT_CUDA_IMAGE, check_docker_gpu
from nvidia_agent_doctor.security.credentials import redact_data

app = typer.Typer(help="Docker GPU-container diagnostics.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def docker_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command("gpu-check")
def gpu_check(
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
    image: str = typer.Option(
        DEFAULT_CUDA_IMAGE,
        "--image",
        help="Already-local CUDA image used only for the bounded inventory probe.",
    ),
    allow_container_run: bool = typer.Option(
        False,
        "--allow-container-run",
        help="Allow one bounded, network-isolated, automatically removed container.",
    ),
    timeout_seconds: int = typer.Option(
        15,
        "--timeout-seconds",
        min=1,
        max=30,
        help="Container probe timeout in seconds.",
    ),
) -> None:
    """Verify that an already-local Docker image can see NVIDIA GPUs."""
    result = redact_data(
        check_docker_gpu(
            image,
            allow_container_run=allow_container_run,
            timeout_seconds=timeout_seconds,
        )
    )
    if json_output:
        typer.echo(json.dumps(result, indent=2, sort_keys=True))
    else:
        console = Console()
        table = Table(title="Docker GPU Container Validation", show_header=False)
        table.add_column("Check", style="dim")
        table.add_column("Result")
        table.add_row("Status", str(result["status"]))
        table.add_row("Image", str(result["image"]))
        table.add_row("Docker daemon", "available" if result["docker_available"] else "unavailable")
        table.add_row("Image available", _state(result["image_available"]))
        table.add_row("GPU visible", _state(result["gpu_visible"]))
        for index, gpu in enumerate(result["gpus"]):
            table.add_row(
                f"GPU {index}",
                f"{gpu['name']} | driver {gpu['driver_version']} | {gpu['memory_mb']} MiB",
            )
        console.print(table)
        if result["error"]:
            console.print(f"[yellow]{result['error']}[/yellow]")
        console.print(
            "[dim]No images are pulled. With --allow-container-run, the probe uses no network, "
            "a read-only filesystem, dropped capabilities, resource limits, and --rm.[/dim]"
        )
    _exit_for_result(result)


def _state(value: bool | None) -> str:
    if value is True:
        return "available"
    if value is False:
        return "unavailable"
    return "not checked"


def _exit_for_result(result: dict[str, Any]) -> None:
    if result["status"] in {"probe_failed", "timeout", "no_gpu_detected"}:
        raise typer.Exit(code=1)
    if result["status"] in {"invalid_image", "invalid_timeout", "docker_daemon_unavailable"}:
        raise typer.Exit(code=2)
