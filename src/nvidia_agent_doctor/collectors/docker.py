"""NVIDIA Agent Doctor — Docker / container runtime collector."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from nvidia_agent_doctor.core.models import DockerInfo


def collect_docker_info() -> DockerInfo:
    """Collect Docker runtime information. Never raises."""
    docker_available, docker_version, docker_server = _check_docker_cli()
    nvidia_runtime = _check_nvidia_runtime()
    in_container, container_id = _detect_container()

    return DockerInfo(
        docker_available=docker_available,
        docker_version=docker_version,
        docker_server_version=docker_server,
        nvidia_runtime_available=nvidia_runtime,
        in_container=in_container,
        container_id=container_id,
    )


def _check_docker_cli() -> tuple[bool, str | None, str | None]:
    """Return (available, client_version, server_version)."""
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Client.Version}}|{{.Server.Version}}"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split("|")
            client = parts[0].strip() if parts else None
            server = parts[1].strip() if len(parts) > 1 else None
            return True, client, server
        # Docker may be installed but daemon not running
        result2 = subprocess.run(
            ["docker", "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result2.returncode == 0:
            return True, result2.stdout.strip(), None
        return False, None, None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False, None, None


def _check_nvidia_runtime() -> bool:
    """Check if nvidia container runtime is available."""
    # Check via docker info
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.Runtimes}}"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and "nvidia" in result.stdout.lower():
            return True
    except Exception:
        pass

    # Check for nvidia-container-toolkit / nvidia-container-runtime binaries
    try:
        result = subprocess.run(
            ["which", "nvidia-container-runtime"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass

    # Windows: check for path
    import shutil
    if shutil.which("nvidia-container-runtime"):
        return True

    return False


def _detect_container() -> tuple[bool, str | None]:
    """Detect if we're running inside a container."""
    # Check /.dockerenv
    if Path("/.dockerenv").exists():
        container_id = _read_container_id()
        return True, container_id

    # Check /proc/1/cgroup for docker/lxc
    cgroup_path = Path("/proc/1/cgroup")
    if cgroup_path.exists():
        try:
            content = cgroup_path.read_text()
            if "docker" in content or "lxc" in content or "kubepods" in content:
                container_id = _read_container_id()
                return True, container_id
        except OSError:
            pass

    # Check KUBERNETES_SERVICE_HOST
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        return True, None

    return False, None


def _read_container_id() -> str | None:
    """Try to extract container ID from /proc/1/cgroup."""
    try:
        with open("/proc/1/cgroup") as f:
            for line in f:
                parts = line.strip().split("/")
                for part in reversed(parts):
                    if len(part) == 64 and all(c in "0123456789abcdef" for c in part):
                        return part[:12]
    except OSError:
        pass
    return None
