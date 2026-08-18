"""Explicit local NVIDIA NIM readiness integration."""

from __future__ import annotations

import json
import time
from typing import Any, cast
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from nvidia_agent_doctor.security.credentials import redact_data, redact_text

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
_MAX_RESPONSE_BYTES = 1_048_576


def check_local_nim(
    endpoint: str,
    allow_request: bool = False,
    timeout_seconds: int = 10,
    include_models: bool = False,
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
    data, latency_ms, error = _get_json(ready_endpoint, timeout_seconds)
    if error:
        return {"status": "unavailable", "ready": False, "error": error}

    status = data.get("status") if isinstance(data, dict) else None
    result: dict[str, Any] = {
        "status": "ready" if status == "ready" else "not_ready",
        "ready": status == "ready",
        "endpoint": ready_endpoint,
        "latency_ms": latency_ms,
    }
    if include_models and status == "ready":
        models_endpoint = ready_endpoint.removesuffix("/health/ready") + "/models"
        models, _, models_error = _get_json(models_endpoint, timeout_seconds)
        if models_error:
            result["models_status"] = "unavailable"
        else:
            result["models"] = _model_ids(models)
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


def _get_json(
    endpoint: str, timeout_seconds: int
) -> tuple[dict[str, Any] | None, float | None, str | None]:
    """Fetch a loopback JSON endpoint with a strict response-size bound."""
    request = Request(endpoint, method="GET")  # noqa: S310 - caller supplies validated loopback URL
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - loopback URL validated by caller
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
        if len(raw) > _MAX_RESPONSE_BYTES:
            return None, None, "Response exceeded the 1 MiB safety limit."
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        return (
            payload if isinstance(payload, dict) else None,
            round((time.perf_counter() - started) * 1000, 2),
            None,
        )
    except (OSError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, None, redact_text(str(exc))


def _model_ids(payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(payload, dict):
        return []
    models = payload.get("data", [])
    if not isinstance(models, list):
        return []
    return [
        str(model["id"])
        for model in models
        if isinstance(model, dict) and isinstance(model.get("id"), str)
    ][:50]
