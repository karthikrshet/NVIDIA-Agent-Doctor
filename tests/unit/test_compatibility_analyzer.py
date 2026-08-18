"""Tests for evidence-based cross-component compatibility findings."""

from __future__ import annotations

from nvidia_agent_doctor.analyzers.compatibility import analyze_compatibility
from nvidia_agent_doctor.core.models import CUDAInfo, GPUInfo
from nvidia_agent_doctor.core.result import CheckResult
from nvidia_agent_doctor.core.severity import Severity


def _checks_by_name() -> dict[str, CheckResult]:
    section = analyze_compatibility(
        gpu_info=[GPUInfo(index=0, name="RTX test", driver_version="511.65")],
        cuda_info=CUDAInfo(
            runtime_version="11.8",
            driver_version="511.65",
            compatible=True,
        ),
        pytorch_info={
            "installed": True,
            "cuda_version": "11.8",
            "basic_compute_pass": True,
        },
        tensorrt_info={"installed": False},
    )
    return {check.name: check for check in section.checks}


def test_prebuilt_pytorch_runtime_does_not_require_a_local_cuda_toolkit() -> None:
    checks = _checks_by_name()

    toolkit_runtime = checks["cuda_toolkit_runtime"]
    pytorch = checks["cuda_pytorch"]

    assert toolkit_runtime.severity is Severity.NOT_APPLICABLE
    assert pytorch.severity is Severity.PASS
    assert "basic GPU computation" in pytorch.message


def test_tensorrt_import_does_not_claim_cuda_support_matrix_compatibility() -> None:
    section = analyze_compatibility(
        gpu_info=[GPUInfo(index=0, name="RTX test", driver_version="511.65")],
        cuda_info=CUDAInfo(runtime_version="11.8", driver_version="511.65", compatible=True),
        pytorch_info={
            "installed": True,
            "cuda_version": "11.8",
            "basic_compute_pass": True,
        },
        tensorrt_info={"installed": True, "cuda_compatible": None},
    )

    tensorrt = next(check for check in section.checks if check.name == "cuda_tensorrt")

    assert tensorrt.severity is Severity.UNKNOWN
    assert "has not been verified" in tensorrt.message
