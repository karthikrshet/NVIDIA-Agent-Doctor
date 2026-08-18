"""NVIDIA Agent Doctor — MCP security analysis."""

from __future__ import annotations

from typing import Any

from nvidia_agent_doctor.core.models import MCPServerInfo
from nvidia_agent_doctor.core.severity import SecuritySeverity

_HIGH_RISK_COMMANDS = [
    "bash",
    "sh",
    "zsh",
    "fish",
    "powershell",
    "cmd",
    "sudo",
    "su",
    "doas",
]

_RISKY_ARGS_PATTERNS = [
    "--privileged",
    "--allow-write",
    "--write",
    "--unrestricted",
    "--all-access",
]


def analyze_mcp_server(server: MCPServerInfo) -> list[dict[str, Any]]:
    """
    Analyze a single MCP server for security risks.
    Returns a list of security findings.
    """
    findings: list[dict[str, Any]] = []

    # Check for shell execution
    if server.command and any(
        server.command.lower().endswith(cmd) or server.command.lower() == cmd
        for cmd in _HIGH_RISK_COMMANDS
    ):
        findings.append(
            {
                "severity": SecuritySeverity.HIGH,
                "title": "MCP server executes shell directly",
                "description": (
                    f"Server '{server.name}' uses command '{server.command}', "
                    "which is a shell interpreter. Shell-based MCP servers can "
                    "execute arbitrary system commands."
                ),
                "recommendation": (
                    "Review the server arguments carefully. Consider using a "
                    "purpose-built MCP server instead of a bare shell."
                ),
            }
        )

    # Check for risky arguments
    risky_args = [
        arg
        for arg in server.args
        if any(pattern in arg.lower() for pattern in _RISKY_ARGS_PATTERNS)
    ]
    if risky_args:
        findings.append(
            {
                "severity": SecuritySeverity.MEDIUM,
                "title": "MCP server uses potentially dangerous arguments",
                "description": (
                    f"Server '{server.name}' uses arguments: {risky_args}. "
                    "These flags may grant elevated access."
                ),
                "recommendation": "Review and restrict argument flags to minimum required.",
            }
        )

    # Check for exposed secrets in environment
    exposed_secrets = [
        k
        for k, v in server.env_vars.items()
        if v == "********"  # was redacted — means a secret key was detected
    ]
    if exposed_secrets:
        findings.append(
            {
                "severity": SecuritySeverity.MEDIUM,
                "title": "MCP server has secrets in environment",
                "description": (
                    f"Server '{server.name}' has potentially sensitive environment "
                    f"variables: {exposed_secrets}. Values have been redacted."
                ),
                "recommendation": (
                    "Use a secrets manager rather than embedding credentials "
                    "directly in MCP config files."
                ),
            }
        )

    # Check for remote URLs
    if server.url and (server.url.startswith("http://") and not server.url.startswith("https://")):
        findings.append(
            {
                "severity": SecuritySeverity.MEDIUM,
                "title": "MCP server uses insecure HTTP",
                "description": (
                    f"Server '{server.name}' connects to '{server.url}' over HTTP. "
                    "Data transmitted may be intercepted."
                ),
                "recommendation": "Use HTTPS for all remote MCP server connections.",
            }
        )

    if not findings:
        findings.append(
            {
                "severity": SecuritySeverity.INFO,
                "title": "No obvious security issues detected",
                "description": (
                    f"Server '{server.name}' passed basic security checks. "
                    "This is a heuristic scan and does not guarantee security."
                ),
                "recommendation": "Review server capabilities and permissions periodically.",
            }
        )

    return findings


def score_mcp_server(server: MCPServerInfo) -> str:
    """Return a human-readable risk rating for an MCP server."""
    findings = analyze_mcp_server(server)
    max_severity = SecuritySeverity.INFO
    for finding in findings:
        sev = finding["severity"]
        if sev.score > max_severity.score:
            max_severity = sev
    return max_severity.value
