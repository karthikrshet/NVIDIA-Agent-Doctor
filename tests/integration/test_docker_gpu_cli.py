"""Integration tests for the opt-in Docker GPU CLI command."""

from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from nvidia_agent_doctor.cli.main import app

runner = CliRunner()


def test_docker_gpu_check_passes_explicit_consent_and_emits_json() -> None:
    expected = {
        "status": "available",
        "image": "nvidia/cuda:11.6.2-base-ubuntu20.04",
        "docker_available": True,
        "image_available": True,
        "gpu_visible": True,
        "gpus": [{"name": "GPU", "driver_version": "511.65", "memory_mb": "4096"}],
        "error": None,
    }
    with patch("nvidia_agent_doctor.cli.docker.check_docker_gpu", return_value=expected) as check:
        result = runner.invoke(app, ["docker", "gpu-check", "--allow-container-run", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output)["gpu_visible"] is True
    check.assert_called_once_with(
        "nvidia/cuda:11.6.2-base-ubuntu20.04",
        allow_container_run=True,
        timeout_seconds=15,
    )
