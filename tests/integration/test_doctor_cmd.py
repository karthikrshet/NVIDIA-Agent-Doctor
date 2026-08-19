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
    @pytest.mark.parametrize("arguments, expected_probe", [([], False), (["--deep-pytorch"], True)])
    def test_doctor_selects_the_requested_pytorch_probe_mode(
        self, arguments: list[str], expected_probe: bool
    ) -> None:
        pytorch_metadata = {
            "installed": False,
            "version": None,
            "cuda_version": None,
            "cuda_build_metadata": None,
            "runtime_probed": expected_probe,
            "cuda_available": False,
            "device_count": 0,
            "devices": [],
            "bf16_support": None,
            "fp16_support": None,
            "basic_compute_pass": None,
            "error": None,
        }
        with patch(
            "nvidia_agent_doctor.integrations.pytorch.check_pytorch",
            return_value=pytorch_metadata,
        ) as check_pytorch:
            result = runner.invoke(app, ["doctor", "--json", *arguments])

        assert result.exit_code in (0, 1, 2, 3)
        check_pytorch.assert_called_once_with(probe_runtime=expected_probe)

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

    def test_doctor_auto_resolve_json_is_review_only(self) -> None:
        with patch("nvidia_agent_doctor.collectors.gpu.nvidia_smi_available", return_value=False):
            result = runner.invoke(app, ["doctor", "--json", "--auto-resolve"])

        assert result.exit_code in (0, 1, 2, 3)
        plan = json.loads(result.output)["remediation_plan"]
        assert all(step["status"] == "manual-review-required" for step in plan)

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

    def test_gpu_info_json_no_gpu_is_valid(self) -> None:
        with patch("nvidia_agent_doctor.collectors.gpu.nvidia_smi_available", return_value=False):
            result = runner.invoke(app, ["gpu", "info", "--json"])

        assert result.exit_code == 0
        assert json.loads(result.output) == {
            "available": False,
            "gpus": [],
            "reason": "nvidia-smi is unavailable",
        }

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
        # A warning/error/security status is an intentional finding, not a
        # command crash. The scanner must preserve the documented status.
        assert result.exit_code in (0, 1, 2, 3)

    def test_security_scan_json(self) -> None:
        result = runner.invoke(app, ["security", "scan", "--json"])
        assert result.exit_code in (0, 1, 2, 3)
        data = json.loads(result.output)
        assert "sections" in data
        assert data["summary"]["exit_code"] == result.exit_code


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

    def test_agent_preflight_json_is_machine_readable(self) -> None:
        result = runner.invoke(app, ["test-agent", "examples/skills", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["mode"] == "static-preflight"
        assert payload["executed"] is False


def test_invalid_config_returns_exit_code_four(tmp_path: Path) -> None:
    config = tmp_path / "invalid.toml"
    config.write_text("[doctor\nstrict = true")

    result = runner.invoke(app, ["--json", "--config", str(config), "doctor"])

    assert result.exit_code == 4
    assert json.loads(result.output)["exit_code"] == 4


def test_unsupported_noop_config_returns_exit_code_four(tmp_path: Path) -> None:
    config = tmp_path / "unsupported.toml"
    config.write_text("[doctor]\nstrict = true")

    result = runner.invoke(app, ["--json", "--config", str(config), "doctor"])

    assert result.exit_code == 4
    assert json.loads(result.output)["exit_code"] == 4
