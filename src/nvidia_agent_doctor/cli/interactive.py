"""Guided local interactive console for NVIDIA Agent Doctor."""

from __future__ import annotations

import sys

import typer
from rich.console import Console


def interactive() -> None:
    """Open a guided local console backed by the real diagnostic collectors."""
    if not sys.stdin.isatty():
        typer.echo("Interactive mode requires an attached terminal.", err=True)
        raise typer.Exit(code=4)

    from nvidia_agent_doctor.analyzers.environment import analyze_cuda, analyze_gpu
    from nvidia_agent_doctor.analyzers.security import analyze_security
    from nvidia_agent_doctor.cli.doctor import _run_doctor
    from nvidia_agent_doctor.reports.terminal import _render_section, render_doctor_summary

    console = Console()
    actions = {
        "1": "Run full doctor",
        "2": "Inspect NVIDIA GPU",
        "3": "Inspect CUDA",
        "4": "Run security baseline",
        "0": "Exit",
    }
    while True:
        console.print("\n[bold]NVIDIA Agent Doctor — Interactive Console[/bold]")
        console.print(
            "[dim]All checks are local and read-only. No telemetry or benchmarks are run.[/dim]"
        )
        for key, label in actions.items():
            console.print(f"  {key}. {label}")
        choice = typer.prompt("Select", default="0").strip()
        if choice == "0":
            console.print("Goodbye.")
            return
        if choice == "1":
            render_doctor_summary(_run_doctor(console, quiet=True), console)
        elif choice == "2":
            _render_section(analyze_gpu(), console)
        elif choice == "3":
            _render_section(analyze_cuda(), console)
        elif choice == "4":
            _render_section(analyze_security(), console)
        else:
            console.print("[yellow]Unknown selection. Choose one of the listed numbers.[/yellow]")
