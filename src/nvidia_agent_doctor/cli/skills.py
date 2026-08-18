"""NVIDIA Agent Doctor — `nad skills` subcommands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Agent skills scanning.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def skills_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command("scan")
def scan(
    directory: Path = typer.Argument(
        Path("."),
        help="Directory to scan for SKILL.md files.",
        exists=False,
    ),
    json_output: bool = typer.Option(False, "--json"),
    verbose: bool = typer.Option(False, "--verbose"),
    depth: int | None = typer.Option(None, "--depth", help="Maximum scan depth."),
    risk_graph: bool = typer.Option(False, "--risk-graph", help="Show cross-skill risk graph."),
) -> None:
    """
    Scan a directory for agent SKILL.md files and perform heuristic security analysis.

    This is HEURISTIC STATIC ANALYSIS only. Results require human review.
    False positives and false negatives are possible.
    """
    from nvidia_agent_doctor.cli.main import get_config
    from nvidia_agent_doctor.security.credentials import redact_data
    from nvidia_agent_doctor.skills.registry import SkillRiskGraph
    from nvidia_agent_doctor.skills.scanner import scan_skills_directory

    console = Console()
    depth = depth if depth is not None else get_config().skills.scan_depth

    if not directory.exists():
        console.print(f"[red]Directory not found: {directory}[/red]")
        raise typer.Exit(code=1)

    if not json_output:
        console.print(f"[dim]Scanning {directory.resolve()} (depth={depth})...[/dim]\n")
    results = scan_skills_directory(directory, max_depth=depth)

    if json_output:
        import json

        output = []
        for r in results:
            output.append(
                {
                    "skill": redact_data(r.skill.model_dump()),
                    "risk_level": r.risk_level.value,
                    "findings": [{**f, "severity": f["severity"].value} for f in r.findings],
                }
            )
        if risk_graph:
            graph = SkillRiskGraph(results)
            typer.echo(json.dumps({"skills": output, "risk_graph": graph.to_dict()}, indent=2))
        else:
            typer.echo(json.dumps(output, indent=2))
        return

    if not results:
        console.print("[dim]No SKILL.md files found.[/dim]")
        return

    # Summary table
    table = Table(
        title=f"Skills Scan — {len(results)} skill(s) found",
        box=box.ROUNDED,
        border_style="bright_blue",
    )
    table.add_column("Skill", style="bold white")
    table.add_column("Path", style="dim")
    table.add_column("Risk Level", justify="center")
    table.add_column("Findings")

    for result in results:
        sev = result.risk_level
        table.add_row(
            result.skill.name,
            result.skill.path,
            f"[{sev.color}]{sev.value}[/{sev.color}]",
            str(len(result.findings)),
        )

    console.print(table)

    if verbose:
        for result in results:
            console.print(f"\n[bold]{result.skill.name}[/bold] ({result.skill.path})")
            for finding in result.findings:
                sev = finding["severity"]
                console.print(f"  [{sev.color}]{sev.value}[/{sev.color}] {finding['title']}")
                console.print(f"    {finding['description']}")
                console.print(f"    [yellow]-> {finding['recommendation']}[/yellow]")

    if risk_graph:
        graph = SkillRiskGraph(results)
        console.print("\n[bold]Cross-Skill Risk Graph[/bold]")
        console.print(graph.render_ascii())

    console.print(
        "\n[dim]DISCLAIMER: This is heuristic/static analysis. "
        "A finding does not confirm malicious behavior. "
        "All results require human review.[/dim]"
    )


@app.command("verify")
def verify(
    skill: Path = typer.Argument(..., help="Path to the SKILL.md file."),
    signature: Path | None = typer.Option(
        None, "--signature", help="Detached SHA-256 digest file."
    ),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Verify a local detached digest and validate a SKILLCARD.yaml manifest."""
    import json

    from nvidia_agent_doctor.skills.verifier import verify_skill

    result = verify_skill(skill, signature)
    if json_output:
        typer.echo(json.dumps(result, indent=2))
    else:
        console = Console()
        console.print(f"Integrity: {result['integrity']['status']}")
        console.print(f"Skill card: {result['skillcard']['status']}")
        console.print("Verified" if result["verified"] else "Not verified")
    if not result["verified"]:
        raise typer.Exit(code=3)
