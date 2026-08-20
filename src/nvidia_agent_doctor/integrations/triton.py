"""NVIDIA Agent Doctor — Triton Inference Server integration."""

from __future__ import annotations

import shutil
import subprocess
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version
from typing import Any, cast
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from nvidia_agent_doctor.security.credentials import redact_data, redact_text

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
_MAX_READINESS_TIMEOUT_SECONDS = 30


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
        import tritonclient

        result["client_available"] = True
        result["client_version"] = getattr(tritonclient, "__version__", None)
        if result["client_version"] is None:
            try:
                result["client_version"] = distribution_version("tritonclient")
            except PackageNotFoundError:
                # A namespace/module can exist without installed distribution
                # metadata. It is still a detected client, just unversioned.
                pass
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


def check_local_triton_readiness(
    endpoint: str,
    allow_request: bool = False,
    timeout_seconds: int = 5,
) -> dict[str, Any]:
    """Query Triton's loopback ready endpoint only after explicit consent.

    The endpoint is based on NVIDIA Triton's documented ``/v2/health/ready``
    route. This makes no inference, metadata, model, or statistics request.
    """
    ready_endpoint = _readiness_url(endpoint)
    if ready_endpoint is None:
        return {
            "status": "invalid_endpoint",
            "ready": False,
            "recommendation": "Use an http(s) loopback base endpoint, such as http://127.0.0.1:8000.",
        }
    if not 1 <= timeout_seconds <= _MAX_READINESS_TIMEOUT_SECONDS:
        return {
            "status": "invalid_timeout",
            "ready": False,
            "recommendation": f"Use a timeout between 1 and {_MAX_READINESS_TIMEOUT_SECONDS} seconds.",
        }
    if not allow_request:
        return {
            "status": "request_not_allowed",
            "ready": False,
            "recommendation": "Re-run with --allow-local-request to query the local Triton readiness endpoint.",
        }

    request = Request(ready_endpoint, method="GET")  # noqa: S310 - validated loopback URL
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - validated loopback URL
            status_code = getattr(response, "status", 200)
        result = {
            "status": "ready" if status_code == 200 else "not_ready",
            "ready": status_code == 200,
            "endpoint": ready_endpoint,
            "http_status": status_code,
        }
    except HTTPError as exc:
        try:
            exc.close()
        except OSError:
            pass
        result = {
            "status": "not_ready",
            "ready": False,
            "endpoint": ready_endpoint,
            "http_status": exc.code,
        }
    except (OSError, TimeoutError) as exc:
        result = {
            "status": "unavailable",
            "ready": False,
            "endpoint": ready_endpoint,
            "error": redact_text(str(exc)),
        }
    return cast(dict[str, Any], redact_data(result))


def _readiness_url(endpoint: str) -> str | None:
    """Validate a base endpoint and append Triton's ready path if needed."""
    try:
        parsed = urlsplit(endpoint)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in _LOOPBACK_HOSTS:
        return None
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return None
    base_path = parsed.path.rstrip("/")
    path = (
        base_path
        if base_path.endswith("/v2/health/ready")
        else f"{base_path}/v2/health/ready"
        if base_path
        else "/v2/health/ready"
    )
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _get_tritonserver_version(binary: str) -> str | None:
    try:
        proc = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            import re

            match = re.search(r"(\d+\.\d+\.\d+)", proc.stdout)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None


def _detect_tritonserver_process() -> bool:
    """Check whether the actual Triton executable is running.

    Do not search arbitrary command-line arguments: a command such as
    ``docker pull nvcr.io/nvidia/tritonserver:tag`` names Triton but is not a
    running server. Container readiness is established by the explicit
    loopback probe instead.
    """
    try:
        import psutil

        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info.get("name", "") or ""
                executable_name = name.lower().removesuffix(".exe")
                if executable_name == "tritonserver":
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
