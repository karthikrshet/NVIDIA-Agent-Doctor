"""Bounded, opt-in Docker GPU visibility validation."""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any

from nvidia_agent_doctor.security.credentials import redact_text

DEFAULT_CUDA_IMAGE = "nvidia/cuda:11.6.2-base-ubuntu20.04"
_IMAGE_REFERENCE = re.compile(
    r"^[a-z0-9][a-z0-9._/-]*(?::[A-Za-z0-9][A-Za-z0-9._-]*)?"
    r"(?:@sha256:[0-9a-f]{64})?$"
)


def check_docker_gpu(
    image: str = DEFAULT_CUDA_IMAGE,
    *,
    allow_container_run: bool = False,
    timeout_seconds: int = 15,
) -> dict[str, Any]:
    """Validate GPU visibility in an already-local Docker image.

    The check never pulls images. When explicitly allowed, it launches a
    transient, network-isolated and read-only container that executes one
    ``nvidia-smi`` inventory query. It never benchmarks or allocates GPU
    memory deliberately.
    """
    result: dict[str, Any] = {
        "status": "unknown",
        "image": image,
        "docker_available": False,
        "image_available": None,
        "gpu_visible": None,
        "gpus": [],
        "error": None,
    }
    if not 1 <= timeout_seconds <= 30:
        result.update(status="invalid_timeout", error="Timeout must be between 1 and 30 seconds.")
        return result
    if not _IMAGE_REFERENCE.fullmatch(image):
        result.update(status="invalid_image", error="Image reference is not valid.")
        return result
    if shutil.which("docker") is None:
        result["status"] = "docker_unavailable"
        return result
    if not _docker_daemon_available():
        result["status"] = "docker_daemon_unavailable"
        return result
    result["docker_available"] = True

    if not _image_available(image):
        result.update(status="image_unavailable", image_available=False)
        return result
    result["image_available"] = True
    if not allow_container_run:
        result["status"] = "container_run_not_allowed"
        return result

    try:
        probe = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--gpus",
                "all",
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "64",
                "--memory",
                "256m",
                "--memory-swap",
                "256m",
                "--cpus",
                "1",
                "--entrypoint",
                "nvidia-smi",
                image,
                "--query-gpu=name,driver_version,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        result.update(status="timeout", gpu_visible=False, error="Container probe timed out.")
        return result
    except (FileNotFoundError, OSError) as exc:
        result.update(status="probe_failed", gpu_visible=False, error=redact_text(str(exc)))
        return result

    if probe.returncode != 0:
        detail = probe.stderr.strip() or probe.stdout.strip() or "Docker GPU probe failed."
        result.update(status="probe_failed", gpu_visible=False, error=redact_text(detail))
        return result

    gpus = _parse_inventory(probe.stdout)
    if not gpus:
        result.update(status="no_gpu_detected", gpu_visible=False)
        return result
    result.update(status="available", gpu_visible=True, gpus=gpus)
    return result


def _docker_daemon_available() -> bool:
    try:
        probe = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    return probe.returncode == 0 and bool(probe.stdout.strip())


def _image_available(image: str) -> bool:
    try:
        probe = subprocess.run(
            ["docker", "image", "inspect", "--", image],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    return probe.returncode == 0


def _parse_inventory(output: str) -> list[dict[str, str]]:
    """Parse the fixed CSV output requested from ``nvidia-smi``."""
    inventory: list[dict[str, str]] = []
    for line in output.splitlines():
        values = [item.strip() for item in line.split(",", maxsplit=2)]
        if len(values) != 3:
            continue
        name, driver, memory = values
        if name and driver and memory:
            inventory.append({"name": name, "driver_version": driver, "memory_mb": memory})
    return inventory
