"""NVIDIA Agent Doctor — OpenShell integration (heuristic detection)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any


def detect_openshell() -> dict[str, Any]:
    """
    Detect OpenShell installation and runtime state.

    Detection is heuristic: we look for known CLI binaries, environment
    variables, and config files. We do not depend on undocumented internals.

    Returns a dict describing what was found.
    Never raises.
    """
    result: dict[str, Any] = {
        "installed": False,
        "cli_available": False,
        "version": None,
        "runtime_running": None,
        "sandbox_active": None,
        "policy_configured": None,
        "network_configured": None,
        "credentials_configured": None,
        "observability_configured": None,
        "config_path": None,
        "detection_method": "heuristic",
        "note": (
            "OpenShell detection uses heuristics based on known CLI tools "
            "and config file locations. Results may vary with different installations."
        ),
    }

    # Check for CLI binaries
    cli_names = ["openshell", "osh", "openshell-agent"]
    for cli in cli_names:
        path = shutil.which(cli)
        if path:
            result["cli_available"] = True
            result["installed"] = True
            result["cli_path"] = path
            result["version"] = _get_cli_version(path)
            break

    # Check environment variables
    env_indicators = [
        "OPENSHELL_HOME",
        "OPENSHELL_CONFIG",
        "OSH_HOME",
        "OPENSHELL_API_KEY",
        "OSH_API_KEY",
    ]
    env_found = {k: os.environ.get(k) is not None for k in env_indicators}
    if any(env_found.values()):
        result["installed"] = True

    # Check config paths
    config_locations = [
        Path.home() / ".openshell" / "config.toml",
        Path.home() / ".openshell" / "config.yaml",
        Path.home() / ".osh" / "config.toml",
        Path("/etc/openshell/config.toml"),
        Path(os.environ.get("OPENSHELL_CONFIG", "__nonexistent__")),
    ]
    for cfg in config_locations:
        try:
            if cfg.exists():
                result["installed"] = True
                result["config_path"] = str(cfg)
                _parse_openshell_config(cfg, result)
                break
        except Exception:
            pass

    # Try runtime detection via process list
    result["runtime_running"] = _detect_runtime_process()

    return result


def _get_cli_version(cli_path: str) -> str | None:
    for flag in ["--version", "version", "-v"]:
        try:
            proc = subprocess.run([cli_path, flag], capture_output=True, text=True, timeout=5)
            if proc.returncode == 0 and proc.stdout.strip():
                import re

                match = re.search(r"(\d+\.\d+(?:\.\d+)?)", proc.stdout)
                if match:
                    return match.group(1)
        except Exception:
            pass
    return None


def _parse_openshell_config(config_path: Path, result: dict[str, Any]) -> None:
    """Read an OpenShell config file and populate presence flags."""
    try:
        with config_path.open("rb") as f:
            data = tomllib.load(f)

        result["policy_configured"] = "policy" in data or "policies" in data
        result["network_configured"] = "network" in data
        result["credentials_configured"] = "credentials" in data or "auth" in data
        result["observability_configured"] = (
            "observability" in data or "telemetry" in data or "tracing" in data
        )
        result["sandbox_active"] = data.get("sandbox", {}).get("enabled", None)

    except Exception:
        # Not a TOML file — try YAML
        try:
            import yaml

            with config_path.open() as f:
                data = yaml.safe_load(f) or {}

            result["policy_configured"] = "policy" in data or "policies" in data
            result["network_configured"] = "network" in data
            result["credentials_configured"] = "credentials" in data or "auth" in data
            result["observability_configured"] = "observability" in data or "telemetry" in data
        except Exception:
            pass


def _detect_runtime_process() -> bool | None:
    """Check if an OpenShell runtime/gateway process is running."""
    try:
        import psutil

        runtime_names = ["openshell", "osh-runtime", "osh-gateway", "openshell-agent"]
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if any(rt in name for rt in runtime_names):
                    return True
                cmdline = proc.info.get("cmdline") or []
                if any(any(rt in arg for rt in runtime_names) for arg in cmdline):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False
    except Exception:
        return None
