"""NVIDIA Agent Doctor — Triton Inference Server integration."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any


def check_triton() -> dict[str, Any]:
    """
    Detect Triton Inference Server installation (local or container).
    Never raises.
    """
    result: dict[str, Any] = {
        "installed": False,
        "version": None,
        "client_available": False,
        "server_process_detected": False,
        "source": None,
        "error": None,
    }

    # Check for tritonserver binary
    tritonserver_path = shutil.which("tritonserver")
    if tritonserver_path:
        result["installed"] = True
        result["source"] = "binary"
        version = _get_tritonserver_version(tritonserver_path)
        result["version"] = version

    # Check Python client (tritonclient)
    try:
        import tritonclient  # type: ignore[import]
        result["client_available"] = True
        result["client_version"] = getattr(tritonclient, "__version__", None)
    except ImportError:
        pass

    # Check for running tritonserver process (safe read-only)
    result["server_process_detected"] = _detect_tritonserver_process()

    # If no local binary, check if we're in a Triton container
    if not result["installed"]:
        if _check_triton_container():
            result["installed"] = True
            result["source"] = "container"

    return result


def _get_tritonserver_version(binary: str) -> str | None:
    try:
        proc = subprocess.run(
            [binary, "--version"],
            capture_output=True, text=True, timeout=5
        )
        if proc.returncode == 0:
            import re
            match = re.search(r"(\d+\.\d+\.\d+)", proc.stdout)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None


def _detect_tritonserver_process() -> bool:
    """Check if tritonserver is running as a process."""
    try:
        import psutil
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                name = proc.info.get("name", "") or ""
                if "tritonserver" in name.lower():
                    return True
                cmdline = proc.info.get("cmdline") or []
                if any("tritonserver" in arg for arg in cmdline):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass
    return False


def _check_triton_container() -> bool:
    """Detect if we're inside an NVIDIA Triton container."""
    from pathlib import Path
    indicators = [
        "/opt/tritonserver",
        "/usr/local/lib/triton",
    ]
    return any(Path(p).exists() for p in indicators)
