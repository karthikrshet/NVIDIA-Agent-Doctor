"""Tests for secret redaction."""

from __future__ import annotations

import pytest

from nvidia_agent_doctor.security.credentials import (
    REDACTED,
    redact_data,
    redact_env_dict,
    redact_secrets,
    scan_environment_for_exposed_secrets,
)


class TestRedactSecrets:
    def test_api_key_redacted_by_key_name(self) -> None:
        assert redact_secrets("API_KEY", "my-real-secret") == REDACTED

    def test_token_redacted_by_key_name(self) -> None:
        assert redact_secrets("TOKEN", "abc123") == REDACTED

    def test_password_redacted(self) -> None:
        assert redact_secrets("PASSWORD", "hunter2") == REDACTED

    def test_openai_key_value_redacted(self) -> None:
        assert redact_secrets("KEY", "sk-" + "x" * 30) == REDACTED

    def test_nvidia_api_key_value_redacted(self) -> None:
        assert redact_secrets("KEY", "nvapi-" + "x" * 30) == REDACTED

    def test_hf_token_redacted(self) -> None:
        assert redact_secrets("TOKEN_VALUE", "hf_" + "x" * 30) == REDACTED

    def test_safe_value_not_redacted(self) -> None:
        assert redact_secrets("MODEL_NAME", "llama-3.1") == "llama-3.1"

    def test_empty_value_not_redacted(self) -> None:
        assert redact_secrets("API_KEY", "") == ""

    def test_ngc_api_key_redacted(self) -> None:
        assert redact_secrets("NGC_API_KEY", "anything") == REDACTED

    def test_debug_flag_not_redacted(self) -> None:
        assert redact_secrets("DEBUG", "true") == "true"


class TestRedactEnvDict:
    def test_dict_with_secrets(self) -> None:
        env = {"API_KEY": "secret123", "DEBUG": "true", "MODEL": "llama"}
        redacted = redact_env_dict(env)
        assert redacted["API_KEY"] == REDACTED
        assert redacted["DEBUG"] == "true"
        assert redacted["MODEL"] == "llama"

    def test_empty_dict(self) -> None:
        assert redact_env_dict({}) == {}


class TestRecursiveRedaction:
    def test_redacts_metadata_arguments_urls_and_exception_text(self) -> None:
        secret = "sk-realsecret12345678901234567890"
        data = {
            "metadata": {"api_key": secret},
            "args": [f"--token={secret}"],
            "url": f"https://user:{secret}@example.test/api?access_token={secret}",
            "error": f"request failed: OPENAI_API_KEY={secret}",
        }

        result = redact_data(data)

        assert secret not in str(result)
        assert result["metadata"]["api_key"] == REDACTED
        assert result["args"][0] == "--token=********"
        assert result["url"] == "https://********@example.test/api?access_token=********"
        assert result["error"] == "request failed: OPENAI_API_KEY=********"


class TestScanEnvironmentForSecrets:
    def test_detects_exposed_env_secrets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234567890abcdef")
        findings = scan_environment_for_exposed_secrets()
        keys = [f["variable"] for f in findings]
        assert "OPENAI_API_KEY" in keys

    def test_values_always_redacted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_SECRET_TOKEN", "super-secret-value")
        findings = scan_environment_for_exposed_secrets()
        for finding in findings:
            assert finding["value"] == REDACTED
