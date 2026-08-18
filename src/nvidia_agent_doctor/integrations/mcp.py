"""NVIDIA Agent Doctor — MCP configuration discovery."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from nvidia_agent_doctor.core.models import MCPServerInfo
from nvidia_agent_doctor.security.credentials import REDACTED, redact_data, redact_secrets

_DEFAULT_MCP_PATHS = [
    Path.home() / ".mcp" / "config.json",
    Path.home() / ".mcp.json",
    Path(".mcp.json"),
    Path("mcp.json"),
    Path(".mcp") / "config.json",
    Path(os.environ.get("MCP_CONFIG_PATH", "__nonexistent__")),
]
_MAX_MCP_CONFIG_BYTES = 1_048_576
_SENSITIVE_ARGUMENTS = {"--api-key", "--password", "--secret", "--token", "-t"}


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
            # Configuration is untrusted input.  A scanner should not follow
            # a symlink supplied through a config path or read arbitrarily
            # large files during a normal diagnostic invocation.
            if (
                path.is_symlink()
                or not path.is_file()
                or path.stat().st_size > _MAX_MCP_CONFIG_BYTES
            ):
                continue
            resolved = path.resolve(strict=True)
            if resolved in seen:
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
    mcp_servers = data.get("mcpServers", {}) if isinstance(data, dict) else data
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

    raw_args = cfg.get("args", [])
    args = raw_args if isinstance(raw_args, list) else []
    url = cfg.get("url")
    return MCPServerInfo(
        name=name,
        transport=cfg.get("transport"),
        command=cfg.get("command"),
        args=_redact_args(args),
        env_vars=redacted_env,
        url=str(redact_data(url, key="url")) if url is not None else None,
        config_path=config_path,
    )


def _redact_args(args: list[Any]) -> list[str]:
    """Redact both ``--token=value`` and ``--token value`` forms."""
    redacted: list[str] = []
    redact_next = False
    for argument in args:
        text = str(argument)
        if redact_next:
            redacted.append(REDACTED)
            redact_next = False
            continue
        if text.lower() in _SENSITIVE_ARGUMENTS:
            redacted.append(text)
            redact_next = True
            continue
        redacted.append(str(redact_data(text, key="args")))
    return redacted
