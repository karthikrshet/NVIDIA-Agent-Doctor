"""Tests for bounded Docker GPU validation."""

from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import patch

from nvidia_agent_doctor.integrations.docker_gpu import check_docker_gpu


def test_docker_gpu_probe_requires_explicit_container_permission() -> None:
    with patch("nvidia_agent_doctor.integrations.docker_gpu.shutil.which", return_value="docker"):
        with patch(
            "nvidia_agent_doctor.integrations.docker_gpu._docker_daemon_available",
            return_value=True,
        ):
            with patch(
                "nvidia_agent_doctor.integrations.docker_gpu._image_available", return_value=True
            ):
                with patch("nvidia_agent_doctor.integrations.docker_gpu.subprocess.run") as run:
                    result = check_docker_gpu("nvidia/cuda:11.6.2-base-ubuntu20.04")

    assert result["status"] == "container_run_not_allowed"
    assert result["gpu_visible"] is None
    run.assert_not_called()


def test_docker_gpu_probe_is_bounded_and_parses_real_command_shape() -> None:
    completed = CompletedProcess(
        args=[],
        returncode=0,
        stdout="NVIDIA GeForce RTX 3050 Laptop GPU, 511.65, 4096\n",
        stderr="",
    )
    with patch("nvidia_agent_doctor.integrations.docker_gpu.shutil.which", return_value="docker"):
        with patch(
            "nvidia_agent_doctor.integrations.docker_gpu._docker_daemon_available",
            return_value=True,
        ):
            with patch(
                "nvidia_agent_doctor.integrations.docker_gpu._image_available", return_value=True
            ):
                with patch(
                    "nvidia_agent_doctor.integrations.docker_gpu.subprocess.run",
                    return_value=completed,
                ) as run:
                    result = check_docker_gpu(
                        "nvidia/cuda:11.6.2-base-ubuntu20.04",
                        allow_container_run=True,
                    )

    command = run.call_args.args[0]
    assert result["status"] == "available"
    assert result["gpus"] == [
        {
            "name": "NVIDIA GeForce RTX 3050 Laptop GPU",
            "driver_version": "511.65",
            "memory_mb": "4096",
        }
    ]
    assert "--rm" in command
    assert "--network" in command and "none" in command
    assert "--read-only" in command
    assert "--cap-drop" in command and "ALL" in command
    assert "--pids-limit" in command and "64" in command
    assert "--memory" in command and "256m" in command
    assert "--gpus" in command and "all" in command


def test_docker_gpu_probe_rejects_invalid_image_references() -> None:
    result = check_docker_gpu("image;rm -rf /")

    assert result["status"] == "invalid_image"


def test_docker_gpu_probe_ignores_malformed_inventory_lines() -> None:
    completed = CompletedProcess(args=[], returncode=0, stdout="not,csv\n", stderr="")
    with patch("nvidia_agent_doctor.integrations.docker_gpu.shutil.which", return_value="docker"):
        with patch(
            "nvidia_agent_doctor.integrations.docker_gpu._docker_daemon_available",
            return_value=True,
        ):
            with patch(
                "nvidia_agent_doctor.integrations.docker_gpu._image_available", return_value=True
            ):
                with patch(
                    "nvidia_agent_doctor.integrations.docker_gpu.subprocess.run",
                    return_value=completed,
                ):
                    result = check_docker_gpu(
                        "nvidia/cuda:11.6.2-base-ubuntu20.04",
                        allow_container_run=True,
                    )

    assert result["status"] == "no_gpu_detected"
