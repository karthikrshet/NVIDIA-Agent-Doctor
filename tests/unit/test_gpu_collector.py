"""Tests for GPU collector (uses mock nvidia-smi output)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import ParseError

import pytest
from defusedxml.common import DefusedXmlException

from nvidia_agent_doctor.collectors.gpu import (
    _parse_nvidia_smi_xml,
    collect_gpu_info,
    get_nvidia_smi_version,
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
        mock_result.stdout = "GPU 0: NVIDIA Test GPU (UUID: GPU-test)"
        with patch("nvidia_agent_doctor.collectors.gpu.shutil.which", return_value="nvidia-smi"):
            with patch("subprocess.run", return_value=mock_result) as run:
                assert nvidia_smi_available() is True

        run.assert_called_once_with(
            ["nvidia-smi", "-L"], capture_output=True, text=True, timeout=10, check=False
        )

    def test_not_available_when_list_has_no_gpu_output(self) -> None:
        mock_result = MagicMock(returncode=0, stdout="")
        with patch("nvidia_agent_doctor.collectors.gpu.shutil.which", return_value="nvidia-smi"):
            with patch("subprocess.run", return_value=mock_result):
                assert nvidia_smi_available() is False

    def test_not_available_when_command_fails(self) -> None:
        with patch("nvidia_agent_doctor.collectors.gpu.shutil.which", return_value="nvidia-smi"):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                assert nvidia_smi_available() is False

    def test_not_available_when_binary_is_not_on_path(self) -> None:
        with patch("nvidia_agent_doctor.collectors.gpu.shutil.which", return_value=None):
            with patch("subprocess.run") as run:
                assert nvidia_smi_available() is False

        run.assert_not_called()


def test_version_falls_back_to_default_summary_for_older_drivers() -> None:
    unsupported_version = MagicMock(returncode=2, stdout="", stderr="invalid option")
    summary = MagicMock(
        returncode=0,
        stdout="NVIDIA-SMI 511.65 Driver Version: 511.65 CUDA Version: 11.6\n",
    )
    with patch(
        "nvidia_agent_doctor.collectors.gpu.subprocess.run",
        side_effect=[unsupported_version, summary],
    ) as run:
        assert (
            get_nvidia_smi_version()
            == "NVIDIA-SMI 511.65 Driver Version: 511.65 CUDA Version: 11.6"
        )

    assert run.call_count == 2


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

    def test_supplements_missing_compute_capability_from_query(
        self, nvidia_smi_xml_one_gpu: str
    ) -> None:
        xml_without_compute_capability = nvidia_smi_xml_one_gpu.replace(
            "<compute_capability>\n            <major>8</major>\n            <minor>9</minor>\n        </compute_capability>\n",
            "",
        )
        query_result = MagicMock(returncode=0, stdout="0, 8.9\n")
        with patch(
            "nvidia_agent_doctor.collectors.gpu._run_nvidia_smi_xml",
            return_value=xml_without_compute_capability,
        ):
            with patch(
                "nvidia_agent_doctor.collectors.gpu.subprocess.run", return_value=query_result
            ) as run:
                result = collect_gpu_info()

        assert result is not None
        assert result[0].compute_capability == "8.9"
        run.assert_called_once_with(
            [
                "nvidia-smi",
                "--query-gpu=index,compute_cap",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
