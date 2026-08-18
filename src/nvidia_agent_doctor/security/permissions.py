"""NVIDIA Agent Doctor — Security permissions analysis."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast


def check_file_permissions(path: Path) -> dict[str, Any]:
    """Check if a file has overly permissive permissions."""
    result: dict[str, Any] = {
        "path": str(path),
        "exists": False,
        "world_readable": None,
        "world_writable": None,
        "mode": None,
        "findings": [],
    }
    try:
        st = path.stat()
        result["exists"] = True
        mode = st.st_mode
        result["mode"] = oct(mode)
        world_read = bool(mode & stat.S_IROTH)
        world_write = bool(mode & stat.S_IWOTH)
        result["world_readable"] = world_read
        result["world_writable"] = world_write

        if world_write:
            result["findings"].append(
                {
                    "severity": "HIGH",
                    "description": f"{path} is world-writable ({oct(mode)})",
                    "recommendation": f"Run: chmod o-w {path}",
                }
            )
        elif world_read:
            result["findings"].append(
                {
                    "severity": "MEDIUM",
                    "description": f"{path} is world-readable ({oct(mode)})",
                    "recommendation": f"Run: chmod o-r {path} if it contains sensitive data.",
                }
            )
    except (OSError, PermissionError):
        pass
    return result


def check_ssh_key_permissions() -> list[dict[str, Any]]:
    """Check SSH private key permissions."""
    findings: list[dict[str, Any]] = []
    ssh_dir = Path.home() / ".ssh"
    if not ssh_dir.exists():
        return findings

    private_key_patterns = ["id_rsa", "id_ed25519", "id_ecdsa", "id_dsa"]
    for key_name in private_key_patterns:
        key_path = ssh_dir / key_name
        if key_path.exists():
            result = check_file_permissions(key_path)
            findings.extend(result["findings"])

    return findings


def check_nvidia_config_permissions() -> list[dict[str, Any]]:
    """Check permissions on NVIDIA-related config files."""
    findings: list[dict[str, Any]] = []

    config_paths = [
        Path.home() / ".nvidia-agent-doctor.toml",
        Path.home() / ".openshell" / "config.toml",
        Path.home() / ".mcp.json",
        Path(".nvidia-agent-doctor.toml"),
        Path(".mcp.json"),
    ]

    for path in config_paths:
        if path.exists():
            result = check_file_permissions(path)
            findings.extend(result["findings"])

    return findings


def is_running_as_root() -> bool:
    """Check if the process is running as root."""
    if os.name != "nt":
        getuid = cast(Callable[[], int], getattr(os, "getuid"))  # noqa: B009
        return getuid() == 0

    import ctypes

    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False
