"""Safe, non-executing preflight checks for agent skill and MCP wiring."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from nvidia_agent_doctor.integrations.mcp import discover_mcp_servers
from nvidia_agent_doctor.security.credentials import redact_data
from nvidia_agent_doctor.security.mcp import analyze_mcp_server
from nvidia_agent_doctor.skills.scanner import scan_skills_directory


def run_agent_preflight(
    skills_directory: Path,
    mcp_config_paths: list[str],
    scan_depth: int,
) -> dict[str, Any]:
    """Validate local agent inputs without invoking tools, models, or servers.

    A real MCP session can execute arbitrary local commands or send data to a
    remote service. This preflight intentionally limits itself to discovery,
    parsing, command-path resolution, and static security findings.
    """
    checks: list[dict[str, Any]] = []
    has_high_risk_finding = False

    if not skills_directory.is_dir():
        checks.append(
            {
                "kind": "skills",
                "status": "ERROR",
                "evidence": "The supplied skills directory does not exist or is not a directory.",
            }
        )
    else:
        skills = scan_skills_directory(skills_directory, max_depth=scan_depth)
        checks.append(
            {
                "kind": "skills",
                "status": "PASS",
                "evidence": f"Parsed {len(skills)} SKILL.md file(s) without executing them.",
            }
        )
        for result in skills:
            if result.risk_level.value in {"HIGH", "CRITICAL"}:
                has_high_risk_finding = True
                checks.append(
                    {
                        "kind": "skill-security",
                        "status": "HIGH",
                        "name": result.skill.name,
                        "evidence": "Static analysis identified a potential security risk requiring review.",
                    }
                )

    servers = discover_mcp_servers(extra_paths=mcp_config_paths)
    if not servers:
        checks.append(
            {
                "kind": "mcp",
                "status": "SKIPPED",
                "evidence": "No MCP configuration was discovered; no MCP server was launched.",
            }
        )
    for server in servers:
        findings = analyze_mcp_server(server)
        if any(finding["severity"].value in {"HIGH", "CRITICAL"} for finding in findings):
            has_high_risk_finding = True

        if server.command:
            resolved = shutil.which(server.command)
            checks.append(
                {
                    "kind": "mcp-command",
                    "status": "PASS" if resolved else "WARNING",
                    "name": server.name,
                    "evidence": (
                        "Command resolves locally; it was not executed."
                        if resolved
                        else "Configured command does not resolve on PATH; it was not executed."
                    ),
                }
            )
        elif server.url:
            parsed = urlsplit(server.url)
            checks.append(
                {
                    "kind": "mcp-endpoint",
                    "status": "PASS" if parsed.scheme in {"http", "https"} and parsed.netloc else "WARNING",
                    "name": server.name,
                    "evidence": "Endpoint syntax checked locally; no network request was made.",
                }
            )
        else:
            checks.append(
                {
                    "kind": "mcp-configuration",
                    "status": "WARNING",
                    "name": server.name,
                    "evidence": "No command or endpoint was configured; it was not executed.",
                }
            )

    failures = any(check["status"] == "ERROR" for check in checks)
    warnings = any(check["status"] == "WARNING" for check in checks)
    response: dict[str, Any] = {
            "mode": "static-preflight",
            "executed": False,
            "checks": checks,
            "exit_code": 3 if has_high_risk_finding else 2 if failures else 1 if warnings else 0,
            "limitations": "This does not start an agent loop, invoke MCP servers, call a model, or prove runtime interoperability.",
    }
    return cast(dict[str, Any], redact_data(response))
