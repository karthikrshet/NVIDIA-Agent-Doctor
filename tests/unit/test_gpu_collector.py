"""Tests for GPU collector (uses mock nvidia-smi output)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import ParseError

import pytest
from defusedxml.common import DefusedXmlException

from nvidia_agent_doctor.collectors.gpu import (
    _parse_nvidia_smi_xml,
    collect_gpu_info,
    nvidia_smi_available,
)


class TestNvidiaSmiXmlParser:
    def test_parse_one_gpu(self, nvidia_smi_xml_one_gpu: str) -> None:
        gpus = _parse_nvidia_smi_xml(nvidia_smi_xml_one_gpu)
        assert len(gpus) == 1
        gpu = gpus[0]
        assert gpu.name == "NVIDIA GeForce RTX 4090"
        assert gpu.driver_version == "545.23.08"
        assert gpu.cuda_version == "12.3"
        assert gpu.vram_total_mb == 24564
        assert gpu.vram_used_mb == 512
        assert gpu.utilization_gpu_pct == 15
        assert gpu.temperature_c == 42
        assert gpu.compute_capability == "8.9"

    def test_parse_hot_gpu(self, nvidia_smi_xml_hot_gpu: str) -> None:
        gpus = _parse_nvidia_smi_xml(nvidia_smi_xml_hot_gpu)
        assert len(gpus) == 1
        gpu = gpus[0]
        assert gpu.temperature_c == 93
        assert gpu.utilization_gpu_pct == 99

    def test_vram_gb_computed(self, nvidia_smi_xml_one_gpu: str) -> None:
        gpus = _parse_nvidia_smi_xml(nvidia_smi_xml_one_gpu)
        gpu = gpus[0]
        assert gpu.vram_total_gb is not None
        assert gpu.vram_total_gb > 20  # ~24 GB

    def test_invalid_xml_returns_empty(self) -> None:
        with pytest.raises((DefusedXmlException, ParseError)):
            _parse_nvidia_smi_xml("not xml at all {{}")


class TestNvidiaSmiAvailable:
    def test_available_when_command_succeeds(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            assert nvidia_smi_available() is True

    def test_not_available_when_command_fails(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert nvidia_smi_available() is False


class TestCollectGpuInfo:
    def test_returns_none_when_unavailable(self) -> None:
        with patch("nvidia_agent_doctor.collectors.gpu._run_nvidia_smi_xml", return_value=None):
            with patch("nvidia_agent_doctor.collectors.gpu._collect_via_query", return_value=None):
                result = collect_gpu_info()
                assert result is None

    def test_returns_gpus_from_xml(self, nvidia_smi_xml_one_gpu: str) -> None:
        with patch(
            "nvidia_agent_doctor.collectors.gpu._run_nvidia_smi_xml",
            return_value=nvidia_smi_xml_one_gpu,
        ):
            result = collect_gpu_info()
            assert result is not None
            assert len(result) == 1
            assert result[0].name == "NVIDIA GeForce RTX 4090"
