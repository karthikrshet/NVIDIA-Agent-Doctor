"""Tests for evidence-based CUDA driver compatibility checks."""

from __future__ import annotations

from unittest.mock import patch

from nvidia_agent_doctor.collectors.cuda import _check_compatibility, collect_cuda_info


def test_cuda_12_requires_documented_minimum_driver() -> None:
    compatible, notes = _check_compatibility("12.4", "12.4", "520.10")

    assert compatible is False
    assert "minimum 525" in notes[0]
    assert "docs.nvidia.com" in notes[0]


def test_cuda_12_with_supported_driver_is_not_flagged() -> None:
    compatible, notes = _check_compatibility("12.4", "12.4", "550.54")

    assert compatible is True
    assert notes == []


def test_cuda_11_with_supported_driver_is_not_flagged() -> None:
    compatible, notes = _check_compatibility("11.8", "11.8", "510.47")

    assert compatible is True
    assert notes == []


def test_cuda_collector_does_not_launch_nvidia_smi_when_preflight_failed() -> None:
    with patch("nvidia_agent_doctor.collectors.cuda.shutil.which", return_value=None):
        with patch("nvidia_agent_doctor.collectors.cuda.subprocess.run") as run:
            collect_cuda_info(nvidia_smi_available=False)

    run.assert_not_called()
