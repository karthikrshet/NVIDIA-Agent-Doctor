"""Contract checks for sanitized, evidence-backed hardware fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from nvidia_agent_doctor.core.models import GPUInfo

_FIXTURE = (
    Path(__file__).parents[1]
    / "fixtures"
    / "recorded_hardware"
    / "rtx3050_windows_driver511_65.json"
)
_DOCKER_FIXTURE = (
    Path(__file__).parents[1]
    / "fixtures"
    / "recorded_hardware"
    / "rtx3050_docker_cuda116_linux.json"
)
_TRANSFER_FIXTURE = (
    Path(__file__).parents[1]
    / "fixtures"
    / "recorded_benchmarks"
    / "rtx3050_windows_host_device_transfer.json"
)


def test_recorded_single_gpu_fixture_is_sanitized_real_evidence() -> None:
    fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))

    assert fixture["provenance"]["kind"] == "sanitized-real-hardware-capture"
    assert fixture["gpu_count"] == 1
    gpu = GPUInfo.model_validate(fixture["gpus"][0])
    assert gpu.name == "NVIDIA GeForce RTX 3050 Laptop GPU"
    assert gpu.driver_version == "511.65"
    assert gpu.cuda_version == "11.6"
    assert gpu.vram_total_mb == 4096
    assert gpu.compute_capability == "8.6"
    assert gpu.uuid is None

    pytorch = fixture["pytorch"]
    assert pytorch["version"] == "2.7.1+cu118"
    assert pytorch["cuda_build"] == "11.8"
    assert pytorch["cuda_available"] is True
    assert pytorch["device_count"] == 1
    assert pytorch["compute_capability"] == "8.6"
    assert pytorch["basic_compute_pass"] is True


def test_recorded_docker_gpu_fixture_is_sanitized_real_linux_evidence() -> None:
    fixture = json.loads(_DOCKER_FIXTURE.read_text(encoding="utf-8"))

    assert fixture["provenance"]["kind"] == "sanitized-real-hardware-capture"
    assert fixture["provenance"]["image"] == "nvidia/cuda:11.6.2-base-ubuntu20.04"
    assert fixture["gpu_count"] == 1
    assert fixture["gpus"] == [
        {
            "name": "NVIDIA GeForce RTX 3050 Laptop GPU",
            "driver_version": "511.65",
            "memory_mb": "4096",
        }
    ]


def test_recorded_host_device_transfer_fixture_is_sanitized_real_benchmark_evidence() -> None:
    fixture = json.loads(_TRANSFER_FIXTURE.read_text(encoding="utf-8"))

    assert fixture["provenance"]["kind"] == "sanitized-real-benchmark-capture"
    assert fixture["gpu"] == "NVIDIA GeForce RTX 3050 Laptop GPU"
    assert fixture["parameters"] == {
        "max_memory_mb": 16,
        "timeout_seconds": 15,
        "transfer_mb": 16,
        "samples": 3,
    }
    transfer = fixture["results"]["host_device_transfer"]
    assert transfer["host_to_device_bandwidth_gb_s"] > 0
    assert transfer["device_to_host_bandwidth_gb_s"] > 0
    assert "not inferred" in transfer["transport"]
