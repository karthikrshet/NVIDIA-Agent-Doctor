"""Tests for evidence-based CUDA driver compatibility checks."""

from __future__ import annotations

from unittest.mock import patch

from nvidia_agent_doctor.analyzers.environment import analyze_cuda
from nvidia_agent_doctor.collectors.cuda import _check_compatibility, collect_cuda_info
from nvidia_agent_doctor.core.models import CUDAInfo
from nvidia_agent_doctor.core.severity import Severity


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


def test_cuda_collector_reuses_the_already_detected_pytorch_cuda_build() -> None:
    with patch("nvidia_agent_doctor.collectors.cuda._detect_toolkit_version", return_value=None):
        with patch(
            "nvidia_agent_doctor.collectors.cuda._detect_driver_cuda_version", return_value="511.65"
        ):
            with patch("nvidia_agent_doctor.collectors.cuda._find_cuda_libraries", return_value=[]):
                with patch(
                    "nvidia_agent_doctor.collectors.cuda._detect_runtime_version",
                    return_value="11.8",
                ) as runtime:
                    info = collect_cuda_info(nvidia_smi_available=True, pytorch_cuda_version="11.8")

    runtime.assert_called_once_with(True, "11.8")
    assert info.runtime_version == "11.8"


def test_driver_only_cuda_runtime_does_not_require_toolkit_environment_variables() -> None:
    section = analyze_cuda(CUDAInfo(runtime_version="11.6", driver_version="511.65"))
    env_check = next(check for check in section.checks if check.name == "cuda_env_vars")

    assert env_check.severity is Severity.NOT_APPLICABLE
    assert env_check.fix_command is None


def test_installed_toolkit_without_environment_variables_never_suggests_a_guessed_command() -> None:
    section = analyze_cuda(CUDAInfo(toolkit_version="12.4", nvcc_available=True))
    env_check = next(check for check in section.checks if check.name == "cuda_env_vars")

    assert env_check.severity is Severity.WARNING
    assert env_check.fix_command is None
    assert "/usr/local/cuda" not in (env_check.recommendation or "")
