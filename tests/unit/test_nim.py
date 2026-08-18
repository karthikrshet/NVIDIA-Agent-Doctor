"""Tests for explicit local NVIDIA NIM readiness checks."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from nvidia_agent_doctor.integrations.nim import check_local_nim


def test_nim_readiness_request_requires_explicit_permission() -> None:
    with patch("nvidia_agent_doctor.integrations.nim.urlopen") as request:
        result = check_local_nim("http://127.0.0.1:8000")

    request.assert_not_called()
    assert result["status"] == "request_not_allowed"


def test_nim_readiness_rejects_non_loopback_endpoint() -> None:
    result = check_local_nim("https://nim.example.test", allow_request=True)

    assert result["status"] == "invalid_endpoint"


def test_nim_readiness_rejects_malformed_url_without_raising() -> None:
    result = check_local_nim("http://[::1", allow_request=True)

    assert result["status"] == "invalid_endpoint"


def test_nim_readiness_parses_ready_response() -> None:
    response = MagicMock()
    response.read.return_value = b'{"status": "ready"}'
    context = MagicMock()
    context.__enter__.return_value = response
    with patch("nvidia_agent_doctor.integrations.nim.urlopen", return_value=context):
        result = check_local_nim("http://localhost:8000", allow_request=True)

    assert result["status"] == "ready"
    assert result["ready"] is True
    assert result["endpoint"] == "http://localhost:8000/v1/health/ready"
    assert isinstance(result["latency_ms"], float)


def test_nim_optional_model_discovery_is_read_only() -> None:
    ready_response = MagicMock()
    ready_response.read.return_value = b'{"status": "ready"}'
    models_response = MagicMock()
    models_response.read.return_value = b'{"data": [{"id": "nim-model"}]}'
    ready_context = MagicMock()
    ready_context.__enter__.return_value = ready_response
    models_context = MagicMock()
    models_context.__enter__.return_value = models_response
    with patch(
        "nvidia_agent_doctor.integrations.nim.urlopen",
        side_effect=[ready_context, models_context],
    ) as request:
        result = check_local_nim("http://127.0.0.1:8000", allow_request=True, include_models=True)

    assert request.call_count == 2
    assert result["models"] == ["nim-model"]
