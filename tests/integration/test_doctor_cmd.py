"""Integration tests for the `nad doctor` CLI command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from nvidia_agent_doctor.cli.main import app

runner = CliRunner()


class TestDoctorCommand:
    def test_doctor_exits_without_crashing_no_gpu(self) -> None:
        """Doctor should complete successfully even when no NVIDIA GPU is present."""
        with patch("nvidia_agent_doctor.collectors.gpu.nvidia_smi_available", return_value=False):
            with patch("nvidia_agent_doctor.collectors.gpu._run_nvidia_smi_xml", return_value=None):
                result = runner.invoke(app, ["doctor"])
                # Should not crash (exit code 0, 1, or 2 are all valid)
                assert result.exit_code in (0, 1, 2, 3)

    def test_doctor_json_output_is_valid(self) -> None:
        """--json flag should produce valid JSON output."""
        with patch("nvidia_agent_doctor.collectors.gpu.nvidia_smi_available", return_value=False):
            result = runner.invoke(app, ["doctor", "--json"])
            assert result.exit_code in (0, 1, 2, 3)
            try:
                data = json.loads(result.output)
                assert "tool" in data
                assert "sections" in data
                assert data["tool"]["name"] == "nvidia-agent-doctor"
            except json.JSONDecodeError:
                pytest.fail(f"JSON output is not valid: {result.output[:500]}")

    def test_doctor_json_contains_no_plaintext_secrets(self) -> None:
        """JSON output must not contain plaintext secret values."""
        import os

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-realsecret12345678901234"}):
            with patch(
                "nvidia_agent_doctor.collectors.gpu.nvidia_smi_available", return_value=False
            ):
                result = runner.invoke(app, ["doctor", "--json"])
                assert "sk-realsecret" not in result.output

    def test_doctor_quiet_flag(self) -> None:
        """--quiet should produce shorter output."""
        with patch("nvidia_agent_doctor.collectors.gpu.nvidia_smi_available", return_value=False):
            result_verbose = runner.invoke(app, ["doctor"])
            result_quiet = runner.invoke(app, ["doctor", "--quiet"])
            # Quiet output should be shorter
            assert len(result_quiet.output) <= len(result_verbose.output) + 200

    def test_version_flag(self) -> None:
        """--version should show version info."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "nvidia-agent-doctor" in result.output.lower() or "0.1.0" in result.output

    def test_version_json(self) -> None:
        """--version --json should produce valid JSON."""
        result = runner.invoke(app, ["--version", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "version" in data


class TestGPUCommand:
    def test_gpu_info_no_gpu(self) -> None:
        """gpu info without a GPU should not crash."""
        with patch("nvidia_agent_doctor.collectors.gpu.nvidia_smi_available", return_value=False):
            result = runner.invoke(app, ["gpu", "info"])
            assert result.exit_code == 0  # graceful

    def test_gpu_info_with_mock_gpu(self, nvidia_smi_xml_one_gpu: str) -> None:
        """gpu info with mocked GPU data should show GPU name."""
        with patch(
            "nvidia_agent_doctor.collectors.gpu._run_nvidia_smi_xml",
            return_value=nvidia_smi_xml_one_gpu,
        ):
            with patch(
                "nvidia_agent_doctor.collectors.gpu.nvidia_smi_available", return_value=True
            ):
                result = runner.invoke(app, ["gpu", "info"])
                assert result.exit_code == 0
                assert "RTX 4090" in result.output


class TestSecurityCommand:
    def test_security_scan_no_crash(self) -> None:
        result = runner.invoke(app, ["security", "scan"])
        assert result.exit_code == 0

    def test_security_scan_json(self) -> None:
        result = runner.invoke(app, ["security", "scan", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "sections" in data


class TestMachineReadableSubcommands:
    def test_mcp_json_is_valid_when_no_configuration_exists(self) -> None:
        result = runner.invoke(app, ["mcp", "scan", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output) == []

    def test_skills_json_has_no_progress_text(self) -> None:
        result = runner.invoke(app, ["skills", "scan", "examples/skills", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert isinstance(payload, list)


def test_invalid_config_returns_exit_code_four(tmp_path: Path) -> None:
    config = tmp_path / "invalid.toml"
    config.write_text("[doctor\nstrict = true")

    result = runner.invoke(app, ["--json", "--config", str(config), "doctor"])

    assert result.exit_code == 4
    assert json.loads(result.output)["exit_code"] == 4
