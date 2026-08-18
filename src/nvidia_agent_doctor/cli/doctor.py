"""NVIDIA Agent Doctor — `nad doctor` command."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from typing import Any

import typer
from rich.console import Console

from nvidia_agent_doctor.core.result import CheckResult, DiagnosticReport, SectionResult
from nvidia_agent_doctor.security.credentials import redact_text

app = typer.Typer(help="Run a full environment diagnostic.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def doctor(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output."),
    quiet: bool = typer.Option(False, "--quiet", help="Minimal output."),
    fix: bool = typer.Option(
        False, "--fix", help="Suggest safe remediation steps (requires confirmation)."
    ),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colors."),
    profile: bool = typer.Option(False, "--profile", help="Record local check durations."),
) -> None:
    """
    Run a complete, safe read-only environment diagnostic.

    Checks: System • GPU • CUDA • PyTorch • Docker • Security • Compatibility

    Use --json for machine-readable output.
    Use --fix to see remediation suggestions (never destructive without confirmation).
    """
    console = Console(no_color=no_color)
    # Suppress progress output when JSON mode is active to avoid mixing text with JSON
    _quiet = quiet or json_output
    report = _run_doctor(console, verbose=verbose, quiet=_quiet, profile=profile)

    if json_output:
        from nvidia_agent_doctor.reports.json_report import render_json

        typer.echo(render_json(report))
    else:
        from nvidia_agent_doctor.reports.terminal import render_doctor_summary

        render_doctor_summary(report, console=console)

    if fix:
        _show_fix_suggestions(report, console)

    sys.exit(report.exit_code)


def _run_doctor(
    console: Console,
    verbose: bool = False,
    quiet: bool = False,
    profile: bool = False,
) -> DiagnosticReport:
    """Run all diagnostic checks and return a report."""
    from nvidia_agent_doctor.analyzers.compatibility import analyze_compatibility
    from nvidia_agent_doctor.analyzers.environment import (
        analyze_cuda,
        analyze_docker,
        analyze_gpu,
        analyze_pytorch,
        analyze_system,
    )
    from nvidia_agent_doctor.analyzers.security import analyze_security
    from nvidia_agent_doctor.collectors.cuda import collect_cuda_info
    from nvidia_agent_doctor.collectors.gpu import collect_gpu_info, nvidia_smi_available
    from nvidia_agent_doctor.core.severity import Severity
    from nvidia_agent_doctor.integrations.nemotron import detect_nemotron
    from nvidia_agent_doctor.integrations.openshell import detect_openshell
    from nvidia_agent_doctor.integrations.pytorch import check_pytorch
    from nvidia_agent_doctor.integrations.tensorrt import check_tensorrt
    from nvidia_agent_doctor.integrations.triton import check_triton

    report = DiagnosticReport()

    # Share read-only hardware probes across sections. This keeps a default
    # doctor run from repeatedly launching nvidia-smi or importing optional
    # GPU runtimes solely for compatibility reporting.
    probe_durations: dict[str, float] = {}

    started = time.perf_counter()
    smi_available = nvidia_smi_available()
    probe_durations["nvidia-smi availability"] = round((time.perf_counter() - started) * 1000, 2)

    started = time.perf_counter()
    gpu_info = collect_gpu_info() if smi_available else []
    probe_durations["GPU inventory"] = round((time.perf_counter() - started) * 1000, 2)

    started = time.perf_counter()
    cuda_info = collect_cuda_info(nvidia_smi_available=smi_available)
    probe_durations["CUDA discovery"] = round((time.perf_counter() - started) * 1000, 2)

    started = time.perf_counter()
    pytorch_info = check_pytorch()
    probe_durations["PyTorch discovery"] = round((time.perf_counter() - started) * 1000, 2)

    started = time.perf_counter()
    tensorrt_info = check_tensorrt()
    probe_durations["TensorRT discovery"] = round((time.perf_counter() - started) * 1000, 2)

    _checkers = [
        ("system", analyze_system, "System"),
        ("gpu", lambda: analyze_gpu(gpu_info, smi_available), "GPU"),
        ("cuda", lambda: analyze_cuda(cuda_info), "CUDA"),
        ("pytorch", lambda: analyze_pytorch(pytorch_info), "PyTorch"),
        ("docker", analyze_docker, "Docker"),
        ("security", analyze_security, "Security"),
        (
            "compatibility",
            lambda: analyze_compatibility(gpu_info, cuda_info, pytorch_info, tensorrt_info),
            "Compatibility",
        ),
    ]

    durations: dict[str, float] = {}
    for name, fn, display in _checkers:
        if not quiet:
            console.print(f"  [dim]Checking {display}...[/dim]", end="\r")
        started = time.perf_counter()
        try:
            section = fn()
        except Exception as e:
            section = SectionResult(name=name, display_name=display)
            section.checks.append(
                CheckResult(
                    name="check_error",
                    severity=Severity.UNKNOWN,
                    message=f"{display} check encountered an unexpected error",
                    detail=redact_text(str(e)) if verbose else None,
                )
            )
        report.add_section(section)
        if profile:
            durations[name] = round((time.perf_counter() - started) * 1000, 2)

    # Optional component sections (NOT_INSTALLED is expected and fine)
    _add_optional_section(
        report, "tensorrt", "TensorRT", lambda: _tensorrt_section(tensorrt_info), quiet, console
    )
    _add_optional_section(
        report, "triton", "Triton", lambda: _triton_section(check_triton()), quiet, console
    )

    if profile:
        profile_entries = {**probe_durations, **durations}
        report.recommendations.append(
            "Profile (ms): "
            + ", ".join(
                f"{name}={duration}"
                for name, duration in sorted(profile_entries.items(), key=lambda item: item[1], reverse=True)
            )
        )
    _add_optional_section(
        report,
        "openshell",
        "OpenShell",
        lambda: _openshell_section(detect_openshell()),
        quiet,
        console,
    )
    _add_optional_section(
        report, "nemotron", "Nemotron", lambda: _nemotron_section(detect_nemotron()), quiet, console
    )

    if not quiet:
        console.print(" " * 40, end="\r")  # Clear spinner line

    return report


def _add_optional_section(
    report: DiagnosticReport,
    name: str,
    display: str,
    fn: Callable[[], SectionResult],
    quiet: bool,
    console: Console,
) -> None:
    from nvidia_agent_doctor.core.severity import Severity

    if not quiet:
        console.print(f"  [dim]Checking {display}...[/dim]", end="\r")
    try:
        section = fn()
    except Exception as e:
        section = SectionResult(name=name, display_name=display)
        section.checks.append(
            CheckResult(
                name="check_error",
                severity=Severity.UNKNOWN,
                message=f"{display} check failed",
                detail=redact_text(str(e)),
            )
        )
    report.add_section(section)


def _tensorrt_section(info: dict[str, Any]) -> SectionResult:
    from nvidia_agent_doctor.core.severity import Severity

    section = SectionResult(name="tensorrt", display_name="TensorRT")
    if not info["installed"]:
        section.checks.append(
            CheckResult(
                name="tensorrt",
                severity=Severity.NOT_INSTALLED,
                message="TensorRT not installed (optional)",
            )
        )
    else:
        sev = Severity.PASS if info.get("builder_available") else Severity.WARNING
        section.checks.append(
            CheckResult(
                name="tensorrt",
                severity=sev,
                message=f"TensorRT {info.get('version') or 'detected'}",
                detail=f"Builder: {info.get('builder_available')} | Runtime: {info.get('runtime_available')}",
            )
        )
    return section


def _triton_section(info: dict[str, Any]) -> SectionResult:
    from nvidia_agent_doctor.core.severity import Severity

    section = SectionResult(name="triton", display_name="Triton")
    if not info["installed"]:
        section.checks.append(
            CheckResult(
                name="triton",
                severity=Severity.NOT_INSTALLED,
                message="Triton Inference Server not detected (optional)",
            )
        )
    else:
        section.checks.append(
            CheckResult(
                name="triton",
                severity=Severity.PASS,
                message=f"Triton {info.get('version') or 'detected'} (source: {info.get('source', 'unknown')})",
            )
        )
        if info.get("server_process_detected"):
            section.checks.append(
                CheckResult(
                    name="triton_running",
                    severity=Severity.PASS,
                    message="Triton server process is running",
                )
            )
    return section


def _openshell_section(info: dict[str, Any]) -> SectionResult:
    from nvidia_agent_doctor.core.severity import Severity

    section = SectionResult(name="openshell", display_name="OpenShell")
    if not info["installed"]:
        section.checks.append(
            CheckResult(
                name="openshell",
                severity=Severity.NOT_INSTALLED,
                message="OpenShell not detected (optional)",
                detail=info.get("note"),
            )
        )
        return section

    section.checks.append(
        CheckResult(
            name="openshell_installed",
            severity=Severity.PASS,
            message=f"OpenShell detected (version: {info.get('version') or 'unknown'})",
            detail=info.get("note"),
        )
    )

    if info.get("runtime_running") is True:
        section.checks.append(
            CheckResult(
                name="openshell_runtime",
                severity=Severity.PASS,
                message="OpenShell runtime is running",
            )
        )
    elif info.get("runtime_running") is False:
        section.checks.append(
            CheckResult(
                name="openshell_runtime",
                severity=Severity.WARNING,
                message="OpenShell runtime not detected as running",
            )
        )

    for attr, label in [
        ("policy_configured", "Policy"),
        ("network_configured", "Network"),
        ("credentials_configured", "Credentials"),
        ("observability_configured", "Observability"),
    ]:
        val = info.get(attr)
        if val is True:
            section.checks.append(
                CheckResult(
                    name=f"openshell_{attr}",
                    severity=Severity.PASS,
                    message=f"OpenShell {label}: configured",
                )
            )
        elif val is False:
            section.checks.append(
                CheckResult(
                    name=f"openshell_{attr}",
                    severity=Severity.WARNING,
                    message=f"OpenShell {label}: not configured",
                    recommendation=f"Configure {label.lower()} in your OpenShell config.",
                )
            )

    return section


def _nemotron_section(info: dict[str, Any]) -> SectionResult:
    from nvidia_agent_doctor.core.severity import Severity

    section = SectionResult(name="nemotron", display_name="Nemotron / NeMo")
    if not info["installed"]:
        section.checks.append(
            CheckResult(
                name="nemotron",
                severity=Severity.NOT_INSTALLED,
                message="Nemotron / NeMo not detected (optional)",
                detail=info.get("note"),
            )
        )
    else:
        if info.get("nemo_installed"):
            section.checks.append(
                CheckResult(
                    name="nemo",
                    severity=Severity.PASS,
                    message=f"NeMo {info.get('nemo_version') or 'detected'}",
                )
            )
        if info.get("nim_available"):
            section.checks.append(
                CheckResult(
                    name="nim",
                    severity=Severity.PASS,
                    message="NIM (NVIDIA Inference Microservice) detected",
                )
            )

    return section


def _show_fix_suggestions(report: DiagnosticReport, console: Console) -> None:
    """Show actionable fix suggestions requiring user confirmation."""
    from nvidia_agent_doctor.core.severity import Severity

    fixable: list[CheckResult] = []
    for section in report.sections.values():
        for check in section.checks:
            if check.fix_command and check.severity in (Severity.WARNING, Severity.ERROR):
                fixable.append(check)

    if not fixable:
        console.print(
            "\n[green]No automatic fixes available. All issues require manual action.[/green]"
        )
        return

    console.print("\n[bold]Suggested Fixes:[/bold]")
    for check in fixable:
        console.print(f"\n  Issue: {check.message}")
        console.print(f"  Fix:   [cyan]{check.fix_command}[/cyan]")
        confirmed = typer.confirm("  Apply this fix?", default=False)
        if confirmed:
            console.print(
                "  [yellow]Manual application required — copy and run the command above.[/yellow]"
            )
