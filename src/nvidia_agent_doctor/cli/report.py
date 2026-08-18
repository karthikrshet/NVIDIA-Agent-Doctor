"""NVIDIA Agent Doctor — `nad report` subcommands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="Generate diagnostic reports.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def report_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        generate()


@app.command("generate")
def generate(
    format: str = typer.Option(
        "terminal", "--format", "-f", help="Output format: terminal, json, markdown, html, compliance-audit"
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path (default: stdout for text formats)"
    ),
) -> None:
    """Generate a full diagnostic report in the specified format."""
    from nvidia_agent_doctor.cli.doctor import _run_doctor
    from nvidia_agent_doctor.reports import compliance, html, json_report, markdown, terminal

    console = Console()
    report = _run_doctor(console, quiet=True)

    if format == "json":
        content = json_report.render_json(report)
        if output:
            output.write_text(content, encoding="utf-8")
            console.print(f"[green]JSON report written to {output}[/green]")
        else:
            typer.echo(content)

    elif format == "markdown":
        content = markdown.render_markdown(report)
        if output:
            output.write_text(content, encoding="utf-8")
            console.print(f"[green]Markdown report written to {output}[/green]")
        else:
            typer.echo(content)

    elif format == "html":
        content = html.render_html(report)
        if output:
            output.write_text(content, encoding="utf-8")
            console.print(f"[green]HTML report written to {output}[/green]")
        elif typer.get_terminal_size()[0] > 0:
            # Default HTML output path
            default_path = Path(f"nad-report-{report.timestamp.strftime('%Y%m%d-%H%M%S')}.html")
            default_path.write_text(content, encoding="utf-8")
            console.print(f"[green]HTML report written to {default_path}[/green]")

    elif format == "compliance-audit":
        content = compliance.render_compliance_audit(report)
        if output:
            output.write_text(content, encoding="utf-8")
            console.print(f"[green]Security readiness audit written to {output}[/green]")
        else:
            typer.echo(content)

    else:
        terminal.render_report(report, console=console)
