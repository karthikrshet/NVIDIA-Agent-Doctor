"""NVIDIA Agent Doctor — System information collector."""

from __future__ import annotations

import platform
import socket
import sys

import psutil

from nvidia_agent_doctor.core.models import SystemInfo


def collect_system_info() -> SystemInfo:
    """Collect general system information. Never raises."""
    try:
        ram = psutil.virtual_memory()
        ram_total_gb: float | None = round(ram.total / (1024**3), 1)
        ram_available_gb: float | None = round(ram.available / (1024**3), 1)
    except Exception:
        ram_total_gb = None
        ram_available_gb = None

    try:
        cpu_count: int | None = psutil.cpu_count(logical=True)
    except Exception:
        cpu_count = None

    try:
        cpu_model: str | None = _get_cpu_model()
    except Exception:
        cpu_model = None

    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "Unknown"

    return SystemInfo(
        os_name=platform.system() or "Unknown",
        os_version=platform.version() or "Unknown",
        os_release=platform.release() or "Unknown",
        architecture=platform.machine() or "Unknown",
        hostname=hostname,
        cpu_count=cpu_count,
        cpu_model=cpu_model,
        ram_total_gb=ram_total_gb,
        ram_available_gb=ram_available_gb,
        python_version=sys.version,
        python_executable=sys.executable,
    )


def _get_cpu_model() -> str | None:
    """Attempt to retrieve a human-friendly CPU model string."""
    system = platform.system()
    if system == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass
    elif system == "Darwin":
        try:
            import subprocess

            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
    elif system == "Windows":
        try:
            import subprocess

            result = subprocess.run(
                ["wmic", "cpu", "get", "name"], capture_output=True, text=True, timeout=5
            )
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if len(lines) >= 2:
                return lines[1]
        except Exception:
            pass
    return None
