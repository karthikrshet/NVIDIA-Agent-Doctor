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
