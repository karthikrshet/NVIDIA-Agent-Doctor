"""NVIDIA Agent Doctor — `nad report` subcommands."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="Generate diagnostic reports.", invoke_without_command=True)
_SUPPORTED_FORMATS = {"terminal", "json", "markdown", "html", "compliance-audit"}


@app.callback(invoke_without_command=True)
def report_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        generate()


@app.command("generate")
def generate(
    format: str = typer.Option(
        "terminal",
        "--format",
        "-f",
        help="Output format: terminal, json, markdown, html, compliance-audit",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path (default: stdout for text formats)"
    ),
) -> None:
    """Generate a full diagnostic report in the specified format."""
    from nvidia_agent_doctor.cli.doctor import _run_doctor
    from nvidia_agent_doctor.reports import compliance, html, json_report, markdown, terminal

    if format not in _SUPPORTED_FORMATS:
        supported = ", ".join(sorted(_SUPPORTED_FORMATS))
        raise typer.BadParameter(
            f"unsupported report format {format!r}; choose one of: {supported}",
            param_hint="--format",
        )

    console = Console()
    report = _run_doctor(console, quiet=True)

    if format == "json":
        content = json_report.render_json(report)
        if output:
            _write_report(output, content, "JSON", console)
        else:
            typer.echo(content)

    elif format == "markdown":
        content = markdown.render_markdown(report)
        if output:
            _write_report(output, content, "Markdown", console)
        else:
            typer.echo(content)

    elif format == "html":
        content = html.render_html(report)
        if output:
            _write_report(output, content, "HTML", console)
        elif typer.get_terminal_size()[0] > 0:
            # Default HTML output path
            default_path = Path(f"nad-report-{report.timestamp.strftime('%Y%m%d-%H%M%S')}.html")
            _write_report(default_path, content, "HTML", console)

    elif format == "compliance-audit":
        content = compliance.render_compliance_audit(report)
        if output:
            _write_report(output, content, "Security readiness audit", console)
        else:
            typer.echo(content)

    else:
        terminal.render_report(report, console=console)

    if report.exit_code:
        raise typer.Exit(code=report.exit_code)


@app.command("compare")
def compare(
    baseline: Path = typer.Argument(..., help="Earlier NAD JSON report."),
    current: Path = typer.Argument(..., help="Newer NAD JSON report."),
    json_output: bool = typer.Option(False, "--json", help="Output comparison as JSON."),
) -> None:
    """Compare report summaries and return a warning on a regression."""
    from nvidia_agent_doctor.reports.comparison import ReportComparisonError, compare_report_files
    from nvidia_agent_doctor.security.credentials import redact_data

    try:
        result = redact_data(compare_report_files(baseline, current))
    except ReportComparisonError as exc:
        raise typer.BadParameter(str(exc), param_hint="REPORT") from exc

    if json_output:
        typer.echo(json.dumps(result, indent=2, sort_keys=True))
    else:
        typer.echo(f"Comparison status: {result['status']}")
        typer.echo(
            f"Health score: {result['baseline']['overall_score']} -> "
            f"{result['current']['overall_score']} ({result['score_delta']:+d})"
        )
        for message in result["regressions"] + result["improvements"]:
            typer.echo(f"- {message}")
    if result["status"] == "regressed":
        raise typer.Exit(code=1)


def _write_report(output: Path, content: str, label: str, console: Console) -> None:
    """Write a requested report path without exposing an unhandled traceback."""
    try:
        output.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise typer.BadParameter(
            f"could not write report to {output}: {exc}", param_hint="--output"
        ) from exc
    console.print(f"[green]{label} written to {output}[/green]")
