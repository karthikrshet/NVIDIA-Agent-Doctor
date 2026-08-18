"""NVIDIA Agent Doctor — CLI entry point."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from nvidia_agent_doctor import __version__
from nvidia_agent_doctor.core.config import ConfigError, NADConfig, load_config

app = typer.Typer(
    name="nad",
    help=(
        "NVIDIA Agent Doctor — Diagnose, secure, validate and benchmark "
        "NVIDIA AI-agent environments.\n\n"
        "GPU • CUDA • OpenShell • NemoClaw • Nemotron • MCP • Agent Skills\n\n"
        "[dim]An independent open-source project. Not an official NVIDIA product.[/dim]"
    ),
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Global state accessible to subcommands
_console = Console()
_json_mode = False
_verbose = False
_quiet = False
_config = NADConfig()


def get_console() -> Console:
    return _console


def is_json_mode() -> bool:
    return _json_mode


def is_verbose() -> bool:
    return _verbose


def is_quiet() -> bool:
    return _quiet


def get_config() -> NADConfig:
    """Return the validated configuration for the current CLI invocation."""
    return _config


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output."),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress all non-essential output."),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output."),
    config: Path | None = typer.Option(None, "--config", help="Path to config file."),
) -> None:
    """NVIDIA Agent Doctor CLI."""
    global _json_mode, _verbose, _quiet, _console, _config

    if no_color:
        import os

        os.environ["NO_COLOR"] = "1"
        _console = Console(no_color=True)

    _json_mode = json_output
    _verbose = verbose
    _quiet = quiet
    try:
        _config = load_config(config)
    except ConfigError as exc:
        if json_output:
            import json

            typer.echo(json.dumps({"error": str(exc), "exit_code": 4}))
        else:
            typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=4) from exc

    if version:
        if json_output:
            import json

            typer.echo(json.dumps({"version": __version__, "tool": "nvidia-agent-doctor"}))
        else:
            _console.print(f"[bold]nvidia-agent-doctor[/bold] v{__version__}")
        raise typer.Exit()


# ── Subcommand imports ─────────────────────────────────────────────────────────
# (imported after app is defined to avoid circular imports)

from nvidia_agent_doctor.cli import benchmark as _bench_mod  # noqa: E402
from nvidia_agent_doctor.cli import compatibility as _compat_mod  # noqa: E402
from nvidia_agent_doctor.cli import cuda as _cuda_mod  # noqa: E402
from nvidia_agent_doctor.cli import doctor as _doctor_mod  # noqa: E402
from nvidia_agent_doctor.cli import gpu as _gpu_mod  # noqa: E402
from nvidia_agent_doctor.cli import mcp as _mcp_mod  # noqa: E402
from nvidia_agent_doctor.cli import nemoclaw as _claw_mod  # noqa: E402
from nvidia_agent_doctor.cli import nemotron as _nem_mod  # noqa: E402
from nvidia_agent_doctor.cli import openshell as _osh_mod  # noqa: E402
from nvidia_agent_doctor.cli import report as _report_mod  # noqa: E402
from nvidia_agent_doctor.cli import security as _sec_mod  # noqa: E402
from nvidia_agent_doctor.cli import skills as _skills_mod  # noqa: E402

app.add_typer(_doctor_mod.app, name="doctor")
app.add_typer(_gpu_mod.app, name="gpu")
app.add_typer(_cuda_mod.app, name="cuda")
app.add_typer(_sec_mod.app, name="security")
app.add_typer(_mcp_mod.app, name="mcp")
app.add_typer(_skills_mod.app, name="skills")
app.add_typer(_compat_mod.app, name="compatibility")
app.add_typer(_bench_mod.app, name="benchmark")
app.add_typer(_report_mod.app, name="report")
app.add_typer(_osh_mod.app, name="openshell")
app.add_typer(_nem_mod.app, name="nemotron")
app.add_typer(_claw_mod.app, name="nemoclaw")
