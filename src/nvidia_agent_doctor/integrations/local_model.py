"""Explicit, loopback-only Ollama explanation integration."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from nvidia_agent_doctor.core.result import DiagnosticReport
from nvidia_agent_doctor.security.credentials import redact_text

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
_MAX_CONTEXT_CHARS = 20_000


def explain_with_ollama(
    report: DiagnosticReport,
    model: str,
    endpoint: str,
    allow_request: bool,
    timeout_seconds: int = 20,
) -> dict[str, Any]:
    """Ask an explicitly permitted local Ollama model to explain a redacted report."""
    if not model.strip():
        return {"status": "model_required", "explanation": None}
    if not allow_request:
        return {
            "status": "request_not_allowed",
            "explanation": None,
            "recommendation": "Re-run with --allow-model-request to contact a local Ollama endpoint.",
        }
    if not _is_loopback_ollama_endpoint(endpoint):
        return {
            "status": "invalid_endpoint",
            "explanation": None,
            "recommendation": "Only http://localhost, 127.0.0.1, or ::1 Ollama endpoints are allowed.",
        }

    prompt = _build_prompt(report)
    request = Request(  # noqa: S310 - endpoint is validated as loopback HTTP above
        endpoint,
        data=json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - loopback validated above
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, json.JSONDecodeError) as exc:
        return {"status": "unavailable", "explanation": None, "error": redact_text(str(exc))}

    explanation = payload.get("response") if isinstance(payload, dict) else None
    if not isinstance(explanation, str) or not explanation.strip():
        return {"status": "invalid_response", "explanation": None}
    return {"status": "ok", "explanation": redact_text(explanation)}


def _is_loopback_ollama_endpoint(endpoint: str) -> bool:
    parsed = urlsplit(endpoint)
    return parsed.scheme == "http" and parsed.hostname in _LOOPBACK_HOSTS and parsed.path == "/api/generate"


def _build_prompt(report: DiagnosticReport) -> str:
    """Create a bounded, redacted prompt requesting explanation rather than action."""
    evidence = json.dumps(report.to_json_dict(), sort_keys=True)[:_MAX_CONTEXT_CHARS]
    return (
        "Explain these local NVIDIA AI environment diagnostic findings in plain language. "
        "Do not invent unavailable hardware, versions, commands, or compatibility claims. "
        "Prioritize evidence, uncertainty, and safe manual next steps.\n\n"
        f"Diagnostic evidence:\n{evidence}"
    )
