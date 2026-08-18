"""Tests for efficient Docker runtime collection."""

from __future__ import annotations

from unittest.mock import patch

from nvidia_agent_doctor.collectors.docker import collect_docker_info


def test_skips_runtime_probe_when_docker_daemon_is_unavailable() -> None:
    with patch(
        "nvidia_agent_doctor.collectors.docker._check_docker_cli",
        return_value=(True, "Docker client", None),
    ):
        with patch("nvidia_agent_doctor.collectors.docker._check_nvidia_runtime") as runtime:
            info = collect_docker_info()

    runtime.assert_not_called()
    assert info.nvidia_runtime_available is False
