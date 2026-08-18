"""NVIDIA Agent Doctor — Compatibility engine."""

from __future__ import annotations

from typing import Any

from nvidia_agent_doctor.collectors.cuda import collect_cuda_info
from nvidia_agent_doctor.collectors.gpu import collect_gpu_info
from nvidia_agent_doctor.core.models import CUDAInfo, GPUInfo
from nvidia_agent_doctor.core.result import CheckResult, SectionResult
from nvidia_agent_doctor.core.severity import Severity
from nvidia_agent_doctor.integrations.pytorch import check_pytorch
from nvidia_agent_doctor.integrations.tensorrt import check_tensorrt


def analyze_compatibility(
    gpu_info: list[GPUInfo] | None = None,
    cuda_info: CUDAInfo | None = None,
    pytorch_info: dict[str, Any] | None = None,
    tensorrt_info: dict[str, Any] | None = None,
) -> SectionResult:
    """
    Perform cross-component compatibility checks.

    We ONLY flag compatibility issues that are directly detectable from
    installed tool output. We do NOT invent or hardcode speculative
    compatibility matrices.
    """
    section = SectionResult(name="compatibility", display_name="Compatibility")

    pytorch_info = check_pytorch() if pytorch_info is None else pytorch_info
    gpu_info = collect_gpu_info() if gpu_info is None else gpu_info
    cuda_info = (
        collect_cuda_info(pytorch_cuda_version=pytorch_info.get("cuda_version"))
        if cuda_info is None
        else cuda_info
    )
    trt_info = check_tensorrt() if tensorrt_info is None else tensorrt_info

    # GPU ↔ Driver: already checked in GPU analyzer
    section.checks.append(
        CheckResult(
            name="driver_detected",
            severity=_presence_severity(gpu_info is not None and len(gpu_info) > 0),
            message="GPU driver"
            + (f" {gpu_info[0].driver_version}" if gpu_info else " not detected"),
        )
    )

    # CUDA toolkit vs runtime
    if cuda_info.toolkit_version and cuda_info.runtime_version:
        if cuda_info.compatible is False:
            section.checks.append(
                CheckResult(
                    name="cuda_toolkit_runtime",
                    severity=Severity.WARNING,
                    message=(
                        f"CUDA toolkit ({cuda_info.toolkit_version}) ↔ "
                        f"runtime ({cuda_info.runtime_version}): MISMATCH"
                    ),
                    detail="\n".join(cuda_info.compatibility_notes),
                    recommendation=(
                        "Align CUDA toolkit and runtime versions. "
                        "See NVIDIA CUDA release notes for your hardware."
                    ),
                )
            )
        else:
            section.checks.append(
                CheckResult(
                    name="cuda_toolkit_runtime",
                    severity=Severity.PASS,
                    message=(
                        f"CUDA toolkit ({cuda_info.toolkit_version}) ↔ "
                        f"runtime ({cuda_info.runtime_version}): PASS"
                    ),
                )
            )
    elif cuda_info.runtime_version:
        section.checks.append(
            CheckResult(
                name="cuda_toolkit_runtime",
                severity=Severity.NOT_APPLICABLE,
                message="CUDA runtime detected; local CUDA toolkit is not installed",
                detail=(
                    "A local toolkit is optional for prebuilt CUDA-enabled Python packages. "
                    "Install it only when compiling CUDA code locally."
                ),
            )
        )

    # CUDA ↔ PyTorch
    if pytorch_info["installed"] and pytorch_info.get("cuda_version"):
        pt_cuda = pytorch_info["cuda_version"]
        toolkit = cuda_info.toolkit_version

        if pytorch_info.get("basic_compute_pass") is True:
            section.checks.append(
                CheckResult(
                    name="cuda_pytorch",
                    severity=Severity.PASS,
                    message=(
                        f"PyTorch CUDA build ({pt_cuda}) completed a basic GPU computation: PASS"
                    ),
                    detail=(
                        "This verifies the installed PyTorch build can initialize and execute "
                        "on the detected NVIDIA GPU."
                    ),
                )
            )
        elif toolkit and pt_cuda:
            tk_major = toolkit.split(".")[0]
            pt_major = str(pt_cuda).split(".")[0]
            if tk_major != pt_major:
                section.checks.append(
                    CheckResult(
                        name="cuda_pytorch",
                        severity=Severity.WARNING,
                        message=(
                            f"CUDA toolkit ({toolkit}) ↔ PyTorch CUDA build ({pt_cuda}): "
                            "major version mismatch"
                        ),
                        recommendation=(
                            "Use a PyTorch build compiled for your installed CUDA version. "
                            "See https://pytorch.org/get-started/locally/"
                        ),
                    )
                )
            else:
                section.checks.append(
                    CheckResult(
                        name="cuda_pytorch",
                        severity=Severity.PASS,
                        message=(
                            f"CUDA toolkit ({toolkit}) ↔ PyTorch CUDA build ({pt_cuda}): PASS"
                        ),
                    )
                )
        else:
            section.checks.append(
                CheckResult(
                    name="cuda_pytorch",
                    severity=Severity.UNKNOWN,
                    message="Cannot compare CUDA and PyTorch versions (insufficient data)",
                )
            )

    elif pytorch_info["installed"] and not pytorch_info.get("cuda_version"):
        section.checks.append(
            CheckResult(
                name="cuda_pytorch",
                severity=Severity.WARNING,
                message="PyTorch installed without CUDA support",
                detail="This is a CPU-only PyTorch build.",
                recommendation=("For GPU workloads, install a CUDA-enabled PyTorch build."),
            )
        )

    # TensorRT ↔ CUDA
    if trt_info["installed"]:
        if trt_info.get("cuda_compatible") is True:
            section.checks.append(
                CheckResult(
                    name="cuda_tensorrt",
                    severity=Severity.PASS,
                    message=f"TensorRT ({trt_info.get('version', 'detected')}) ↔ CUDA: PASS",
                )
            )
        elif trt_info.get("cuda_compatible") is False:
            section.checks.append(
                CheckResult(
                    name="cuda_tensorrt",
                    severity=Severity.WARNING,
                    message="TensorRT ↔ CUDA: incompatibility detected",
                    recommendation="Verify TensorRT and CUDA version compatibility.",
                )
            )
        else:
            section.checks.append(
                CheckResult(
                    name="cuda_tensorrt",
                    severity=Severity.UNKNOWN,
                    message="TensorRT detected; CUDA compatibility has not been verified",
                    detail=(
                        "TensorRT import and local runtime probes do not establish a supported "
                        "TensorRT/CUDA/driver combination."
                    ),
                    recommendation=(
                        "Verify this combination against the NVIDIA TensorRT Support Matrix."
                    ),
                )
            )
    else:
        section.checks.append(
            CheckResult(
                name="cuda_tensorrt",
                severity=Severity.NOT_INSTALLED,
                message="TensorRT not installed (optional)",
            )
        )

    return section


def _presence_severity(present: bool) -> Severity:
    return Severity.PASS if present else Severity.NOT_INSTALLED
