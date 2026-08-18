"""Tests for the explicit, loopback-only Triton readiness probe."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from nvidia_agent_doctor.integrations.triton import check_local_triton_readiness


def test_triton_readiness_never_requests_without_explicit_consent() -> None:
    with patch("nvidia_agent_doctor.integrations.triton.urlopen") as request:
        result = check_local_triton_readiness("http://127.0.0.1:8000")

    assert result["status"] == "request_not_allowed"
    request.assert_not_called()


def test_triton_readiness_rejects_remote_and_credential_bearing_urls() -> None:
    assert (
        check_local_triton_readiness("https://triton.example.test", allow_request=True)["status"]
        == "invalid_endpoint"
    )
    assert (
        check_local_triton_readiness("http://[::1", allow_request=True)["status"]
        == "invalid_endpoint"
    )
    assert (
        check_local_triton_readiness("http://user:pass@127.0.0.1:8000", allow_request=True)[
            "status"
        ]
        == "invalid_endpoint"
    )


def test_triton_readiness_uses_documented_ready_endpoint() -> None:
    response = MagicMock(status=200)
    context = MagicMock()
    context.__enter__.return_value = response
    context.__exit__.return_value = False
    with patch("nvidia_agent_doctor.integrations.triton.urlopen", return_value=context) as request:
        result = check_local_triton_readiness("http://127.0.0.1:8000", allow_request=True)

    assert result == {
        "status": "ready",
        "ready": True,
        "endpoint": "http://127.0.0.1:8000/v2/health/ready",
        "http_status": 200,
    }
    assert request.call_args.args[0].full_url == "http://127.0.0.1:8000/v2/health/ready"
    assert request.call_args.args[0].method == "GET"


def test_triton_readiness_redacts_loopback_connection_errors() -> None:
    with patch(
        "nvidia_agent_doctor.integrations.triton.urlopen",
        side_effect=URLError("API_KEY=super-secret"),
    ):
        result = check_local_triton_readiness("http://127.0.0.1:8000", allow_request=True)

    assert result["status"] == "unavailable"
    assert "super-secret" not in result["error"]
    assert "********" in result["error"]


def test_triton_readiness_reports_non_ready_http_status_without_a_traceback() -> None:
    error = HTTPError("http://127.0.0.1:8000/v2/health/ready", 503, "unavailable", {}, None)
    with patch("nvidia_agent_doctor.integrations.triton.urlopen", side_effect=error):
        result = check_local_triton_readiness("http://127.0.0.1:8000", allow_request=True)

    assert result["status"] == "not_ready"
    assert result["ready"] is False
    assert result["http_status"] == 503
