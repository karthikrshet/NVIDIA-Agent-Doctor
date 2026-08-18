"""Tests that pre-collected hardware data is accepted by analyzers."""

from __future__ import annotations

from unittest.mock import patch

from nvidia_agent_doctor.analyzers.environment import analyze_gpu


def test_gpu_analyzer_uses_supplied_snapshot_without_reprobing() -> None:
    with patch("nvidia_agent_doctor.analyzers.environment.nvidia_smi_available") as available:
        with patch("nvidia_agent_doctor.analyzers.environment.collect_gpu_info") as collect:
            section = analyze_gpu(gpu_info=[], smi_available=True)

    available.assert_not_called()
    collect.assert_not_called()
    assert section.checks[0].name == "nvidia_smi"
    assert section.checks[1].name == "gpu_detected"
