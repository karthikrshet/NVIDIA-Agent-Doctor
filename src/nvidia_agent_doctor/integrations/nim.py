"""Explicit local NVIDIA NIM readiness integration."""

from __future__ import annotations

import json
from typing import Any, cast
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from nvidia_agent_doctor.security.credentials import redact_data, redact_text

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def check_local_nim(
    endpoint: str,
    allow_request: bool = False,
    timeout_seconds: int = 10,
) -> dict[str, Any]:
    """Check a local NIM readiness endpoint without making inference calls."""
    ready_endpoint = _readiness_url(endpoint)
    if ready_endpoint is None:
        return {
            "status": "invalid_endpoint",
            "ready": False,
            "recommendation": "Use an http(s) loopback NIM base endpoint, such as http://127.0.0.1:8000.",
        }
    if not allow_request:
        return {
            "status": "request_not_allowed",
            "ready": False,
            "recommendation": "Re-run with --allow-local-request to query the local NIM readiness endpoint.",
        }
    request = Request(ready_endpoint, method="GET")  # noqa: S310 - loopback URL validated above
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - loopback URL validated above
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
    except (OSError, TimeoutError, json.JSONDecodeError) as exc:
        return {"status": "unavailable", "ready": False, "error": redact_text(str(exc))}

    status = data.get("status") if isinstance(data, dict) else None
    result: dict[str, Any] = {
        "status": "ready" if status == "ready" else "not_ready",
        "ready": status == "ready",
        "endpoint": ready_endpoint,
    }
    return cast(dict[str, Any], redact_data(result))


def _readiness_url(endpoint: str) -> str | None:
    parsed = urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in _LOOPBACK_HOSTS:
        return None
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return None
    base_path = parsed.path.rstrip("/")
    path = f"{base_path}/v1/health/ready" if base_path else "/v1/health/ready"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
