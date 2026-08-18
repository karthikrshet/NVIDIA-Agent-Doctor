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


def test_nim_readiness_parses_ready_response() -> None:
    response = MagicMock()
    response.read.return_value = b'{"status": "ready"}'
    context = MagicMock()
    context.__enter__.return_value = response
    with patch("nvidia_agent_doctor.integrations.nim.urlopen", return_value=context):
        result = check_local_nim("http://localhost:8000", allow_request=True)

    assert result == {
        "status": "ready",
        "ready": True,
        "endpoint": "http://localhost:8000/v1/health/ready",
    }
