"""Tests for explicit local-model explanation boundaries."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from nvidia_agent_doctor.core.result import CheckResult, DiagnosticReport, SectionResult
from nvidia_agent_doctor.core.severity import Severity
from nvidia_agent_doctor.integrations.local_model import explain_with_ollama


def test_local_model_request_requires_explicit_permission() -> None:
    with patch("nvidia_agent_doctor.integrations.local_model.urlopen") as request:
        result = explain_with_ollama(
            DiagnosticReport(),
            model="llama3.2",
            endpoint="http://127.0.0.1:11434/api/generate",
            allow_request=False,
        )

    request.assert_not_called()
    assert result["status"] == "request_not_allowed"


def test_local_model_rejects_remote_endpoint_without_request() -> None:
    result = explain_with_ollama(
        DiagnosticReport(),
        model="llama3.2",
        endpoint="https://example.test/api/generate",
        allow_request=True,
    )

    assert result["status"] == "invalid_endpoint"


def test_local_model_rejects_endpoint_credentials_and_query() -> None:
    report = DiagnosticReport()
    for endpoint in (
        "http://token@127.0.0.1:11434/api/generate",
        "http://127.0.0.1:11434/api/generate?api_key=secret",
    ):
        with patch("nvidia_agent_doctor.integrations.local_model.urlopen") as request:
            result = explain_with_ollama(
                report,
                model="llama3.2",
                endpoint=endpoint,
                allow_request=True,
            )

        request.assert_not_called()
        assert result["status"] == "invalid_endpoint"


def test_local_model_uses_valid_loopback_response() -> None:
    response = MagicMock()
    response.read.return_value = b'{"response": "Review CUDA_HOME before changing it."}'
    context = MagicMock()
    context.__enter__.return_value = response
    with patch(
        "nvidia_agent_doctor.integrations.local_model.urlopen", return_value=context
    ) as request:
        result = explain_with_ollama(
            DiagnosticReport(),
            model="llama3.2",
            endpoint="http://127.0.0.1:11434/api/generate",
            allow_request=True,
        )

    request.assert_called_once()
    assert result == {"status": "ok", "explanation": "Review CUDA_HOME before changing it."}


def test_local_model_sends_redacted_bounded_evidence() -> None:
    report = DiagnosticReport(
        sections={
            "security": SectionResult(
                name="security",
                display_name="Security",
                checks=[
                    CheckResult(
                        name="secret",
                        severity=Severity.WARNING,
                        message="API_KEY=sk-abcdefghijklmnopqrstuvwxyz",
                    )
                ],
            )
        }
    )
    response = MagicMock()
    response.read.return_value = b'{"response": "Review the finding."}'
    context = MagicMock()
    context.__enter__.return_value = response
    with patch(
        "nvidia_agent_doctor.integrations.local_model.urlopen", return_value=context
    ) as request:
        result = explain_with_ollama(
            report,
            model="llama3.2",
            endpoint="http://127.0.0.1:11434/api/generate",
            allow_request=True,
        )

    payload = request.call_args.args[0].data
    assert payload is not None
    assert b"sk-abcdefghijklmnopqrstuvwxyz" not in payload
    assert b"********" in payload
    assert result["status"] == "ok"


def test_local_model_rejects_oversized_response() -> None:
    response = MagicMock()
    response.read.return_value = b"x" * 1_000_001
    context = MagicMock()
    context.__enter__.return_value = response
    with patch("nvidia_agent_doctor.integrations.local_model.urlopen", return_value=context):
        result = explain_with_ollama(
            DiagnosticReport(),
            model="llama3.2",
            endpoint="http://127.0.0.1:11434/api/generate",
            allow_request=True,
        )

    assert result["status"] == "response_too_large"
