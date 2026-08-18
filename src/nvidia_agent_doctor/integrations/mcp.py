"""NVIDIA Agent Doctor — MCP configuration discovery."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from nvidia_agent_doctor.core.models import MCPServerInfo
from nvidia_agent_doctor.security.credentials import redact_secrets

_DEFAULT_MCP_PATHS = [
    Path.home() / ".mcp" / "config.json",
    Path.home() / ".mcp.json",
    Path(".mcp.json"),
    Path("mcp.json"),
    Path(".mcp") / "config.json",
    Path(os.environ.get("MCP_CONFIG_PATH", "__nonexistent__")),
]


def discover_mcp_servers(
    extra_paths: list[str] | None = None,
) -> list[MCPServerInfo]:
    """
    Discover MCP server configurations from well-known locations.
    Returns a list of MCPServerInfo objects with secrets redacted.
    Never raises.
    """
    search_paths = list(_DEFAULT_MCP_PATHS)
    if extra_paths:
        search_paths.extend(Path(p) for p in extra_paths)

    servers: list[MCPServerInfo] = []
    seen: set[Path] = set()

    for path in search_paths:
        try:
            resolved = path.resolve()
            if resolved in seen or not path.exists():
                continue
            seen.add(resolved)
            found = _parse_mcp_config(path)
            servers.extend(found)
        except Exception:
            continue

    return servers


def _parse_mcp_config(path: Path) -> list[MCPServerInfo]:
    """Parse a single MCP config file. Returns empty list on any error."""
    try:
        with path.open() as f:
            data = json.load(f)
    except Exception:
        return []

    servers: list[MCPServerInfo] = []

    # Standard MCP format: {"mcpServers": {"name": {...}}}
    mcp_servers = data.get("mcpServers", {})
    if isinstance(mcp_servers, dict):
        for name, cfg in mcp_servers.items():
            if not isinstance(cfg, dict):
                continue
            server = _parse_server_entry(name, cfg, str(path))
            servers.append(server)

    # Alternative flat format: [{"name": ..., "command": ...}]
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "name" in item:
                server = _parse_server_entry(item["name"], item, str(path))
                servers.append(server)

    return servers


def _parse_server_entry(name: str, cfg: dict[str, Any], config_path: str) -> MCPServerInfo:
    """Parse a single server entry, redacting secret env vars."""
    env_vars = cfg.get("env", {})
    if isinstance(env_vars, dict):
        redacted_env: dict[str, str] = {k: redact_secrets(k, str(v)) for k, v in env_vars.items()}
    else:
        redacted_env = {}

    return MCPServerInfo(
        name=name,
        transport=cfg.get("transport"),
        command=cfg.get("command"),
        args=cfg.get("args", []),
        env_vars=redacted_env,
        url=cfg.get("url"),
        config_path=config_path,
    )
