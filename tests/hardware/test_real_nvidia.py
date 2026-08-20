"""Real NVIDIA hardware validation tests.

These tests intentionally use the local system. They must only be run on a
machine whose GPU state is in scope, for example: ``pytest -m gpu -v``.
"""

from __future__ import annotations

import importlib.util
import os

import pytest

from nvidia_agent_doctor.collectors.cuda import collect_cuda_info
from nvidia_agent_doctor.collectors.gpu import (
    collect_gpu_info,
    collect_gpu_topology,
    nvidia_smi_available,
)
from nvidia_agent_doctor.integrations.nim import check_local_nim
from nvidia_agent_doctor.integrations.pytorch import check_pytorch
from nvidia_agent_doctor.integrations.tensorrt import check_tensorrt
from nvidia_agent_doctor.integrations.triton import check_local_triton_readiness, check_triton

pytestmark = pytest.mark.gpu


def _require_nvidia_smi() -> None:
    if not nvidia_smi_available():
        pytest.skip("GPU VALIDATION BLOCKED: nvidia-smi is unavailable on this machine.")


def test_real_nvidia_smi_inventory() -> None:
    _require_nvidia_smi()
    gpus = collect_gpu_info()

    assert gpus, "nvidia-smi was available but reported no NVIDIA GPUs"
    for gpu in gpus:
        assert gpu.name != "Unknown"
        assert gpu.driver_version
        assert gpu.vram_total_mb and gpu.vram_total_mb > 0


def test_real_cuda_evidence() -> None:
    _require_nvidia_smi()
    cuda = collect_cuda_info()

    assert cuda.driver_version, "NVIDIA driver version could not be collected"
    assert cuda.runtime_version or cuda.toolkit_version or cuda.driver_cuda_max_version, (
        "No CUDA runtime, toolkit, or driver maximum evidence found"
    )


def test_real_gpu_topology_is_a_safe_capability_result() -> None:
    _require_nvidia_smi()
    topology = collect_gpu_topology()

    # Older drivers may not implement ``nvidia-smi topo -m``. That is an
    # explicit capability state rather than a failed hardware validation.
    assert topology["status"] in {"available", "unavailable"}
    assert set(topology) == {"status", "reason", "gpu_count", "gpu_labels", "links"}
    assert "CPU Affinity" not in str(topology)
    assert "PCI" not in str(topology)
    if topology["status"] == "available":
        assert topology["gpu_count"] > 0
        assert all(label.startswith("GPU") for label in topology["gpu_labels"])


def test_real_pytorch_cuda_when_installed() -> None:
    _require_nvidia_smi()
    if importlib.util.find_spec("torch") is None:
        pytest.skip("PyTorch is not installed on this GPU machine.")

    pytorch = check_pytorch()
    assert pytorch["installed"] is True
    assert pytorch["cuda_available"] is True
    assert pytorch["device_count"] > 0
    assert pytorch["basic_compute_pass"] is True


def test_real_optional_runtime_detection() -> None:
    _require_nvidia_smi()
    # This test records evidence without pretending optional runtimes must be
    # installed. Their package-specific validation belongs on configured GPU CI.
    tensorrt = check_tensorrt()
    triton = check_triton()
    assert isinstance(tensorrt["installed"], bool)
    assert isinstance(triton["installed"], bool)


def test_real_tensorrt_when_explicitly_required() -> None:
    """Require TensorRT only on a runner deliberately configured with it."""
    _require_nvidia_smi()
    if os.environ.get("NAD_REQUIRE_TENSORRT") != "true":
        pytest.skip("TensorRT runtime validation was not explicitly requested.")

    tensorrt = check_tensorrt()
    assert tensorrt["installed"] is True
    assert tensorrt["python_bindings"] is True
    assert tensorrt["runtime_available"] is True
    assert tensorrt["builder_available"] is True
    assert tensorrt["error"] is None


def test_real_triton_readiness_when_configured() -> None:
    """Validate one real loopback Triton readiness response when requested."""
    endpoint = os.environ.get("NAD_TRITON_ENDPOINT")
    if not endpoint:
        pytest.skip("No local Triton endpoint was configured.")

    readiness = check_local_triton_readiness(endpoint, allow_request=True)
    assert readiness["status"] == "ready"


def test_real_nim_readiness_when_configured() -> None:
    """Validate one real loopback NIM readiness response when requested."""
    endpoint = os.environ.get("NAD_NIM_ENDPOINT")
    if not endpoint:
        pytest.skip("No local NIM endpoint was configured.")

    readiness = check_local_nim(endpoint, allow_request=True)
    assert readiness["status"] == "ready"
