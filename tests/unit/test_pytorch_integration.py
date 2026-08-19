"""Security and cleanup tests for the optional PyTorch integration."""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError
from types import SimpleNamespace
from unittest.mock import Mock, patch

from nvidia_agent_doctor.analyzers.environment import analyze_pytorch
from nvidia_agent_doctor.core.severity import Severity
from nvidia_agent_doctor.integrations.pytorch import check_pytorch


def test_pytorch_compute_failure_is_redacted_and_releases_cuda_cache() -> None:
    cuda = SimpleNamespace(
        is_available=Mock(return_value=True),
        device_count=Mock(return_value=1),
        get_device_name=Mock(return_value="RTX test"),
        get_device_properties=Mock(return_value=SimpleNamespace(major=8, minor=6)),
        empty_cache=Mock(),
    )
    torch = SimpleNamespace(
        __version__="test",
        version=SimpleNamespace(cuda="11.8"),
        cuda=cuda,
        tensor=Mock(side_effect=RuntimeError("TOKEN=top-secret")),
    )

    with patch.dict(sys.modules, {"torch": torch}):
        result = check_pytorch()

    assert result["basic_compute_pass"] is False
    assert result["compute_error"] == "TOKEN=********"
    cuda.empty_cache.assert_called_once()


def test_pytorch_metadata_probe_does_not_import_or_initialize_torch() -> None:
    with patch(
        "nvidia_agent_doctor.integrations.pytorch.metadata.version",
        return_value="2.7.1+cu118",
    ):
        with patch.dict(sys.modules, {"torch": None}):
            result = check_pytorch(probe_runtime=False)

    assert result["installed"] is True
    assert result["version"] == "2.7.1+cu118"
    assert result["cuda_build_metadata"] == "11.8"
    assert result["runtime_probed"] is False
    assert result["basic_compute_pass"] is None


def test_pytorch_metadata_probe_reports_absent_package() -> None:
    with patch(
        "nvidia_agent_doctor.integrations.pytorch.metadata.version",
        side_effect=PackageNotFoundError,
    ):
        result = check_pytorch(probe_runtime=False)

    assert result["installed"] is False
    assert result["runtime_probed"] is False


def test_pytorch_metadata_only_result_is_unknown_not_a_cuda_warning() -> None:
    section = analyze_pytorch(
        {
            "installed": True,
            "version": "2.7.1+cu118",
            "cuda_version": None,
            "cuda_build_metadata": "11.8",
            "runtime_probed": False,
            "cuda_available": False,
        }
    )

    assert section.checks[-1].name == "pytorch_runtime"
    assert section.checks[-1].severity is Severity.UNKNOWN
