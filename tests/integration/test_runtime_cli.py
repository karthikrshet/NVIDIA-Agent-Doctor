"""CLI tests for bounded TensorRT and Triton local detection commands."""

from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from nvidia_agent_doctor.cli.main import app

runner = CliRunner()


def test_tensorrt_check_json_returns_available_local_runtime() -> None:
    probe = {
        "installed": True,
        "version": "10.0",
        "python_bindings": True,
        "runtime_available": True,
        "builder_available": False,
        "cuda_compatible": None,
        "pytorch_cuda_available": True,
        "error": None,
    }
    with patch("nvidia_agent_doctor.integrations.tensorrt.check_tensorrt", return_value=probe):
        result = runner.invoke(app, ["tensorrt", "check", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["runtime_available"] is True


def test_tensorrt_check_returns_warning_for_an_unusable_installed_runtime() -> None:
    with patch(
        "nvidia_agent_doctor.integrations.tensorrt.check_tensorrt",
        return_value={"installed": True, "runtime_available": False, "error": None},
    ):
        result = runner.invoke(app, ["tensorrt", "check", "--json"])

    assert result.exit_code == 1


def test_triton_check_json_reports_detection_without_contacting_a_server() -> None:
    probe = {
        "installed": False,
        "version": None,
        "client_available": True,
        "server_process_detected": False,
        "source": None,
        "error": None,
    }
    with patch("nvidia_agent_doctor.integrations.triton.check_triton", return_value=probe):
        with patch(
            "nvidia_agent_doctor.integrations.triton.check_local_triton_readiness",
            return_value={"status": "request_not_allowed", "ready": False},
        ):
            result = runner.invoke(app, ["triton", "check", "--json"])

    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["client_available"] is True
    assert output["readiness"]["status"] == "request_not_allowed"


def test_triton_check_returns_warning_for_an_explicit_unavailable_readiness_probe() -> None:
    with patch(
        "nvidia_agent_doctor.integrations.triton.check_triton",
        return_value={"installed": True, "client_available": False},
    ):
        with patch(
            "nvidia_agent_doctor.integrations.triton.check_local_triton_readiness",
            return_value={"status": "unavailable", "ready": False},
        ):
            result = runner.invoke(app, ["triton", "check", "--allow-local-request", "--json"])

    assert result.exit_code == 1
