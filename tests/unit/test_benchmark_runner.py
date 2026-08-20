"""Regression tests for bounded, redacted GPU benchmark behavior."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from nvidia_agent_doctor.benchmark.runner import (
    _benchmark_gpu,
    _benchmark_host_device_transfer,
    run_benchmarks,
)


def _fake_cuda_torch(mm: Mock) -> tuple[SimpleNamespace, Mock]:
    cuda = SimpleNamespace(
        is_available=Mock(return_value=True),
        synchronize=Mock(),
        empty_cache=Mock(),
    )
    torch = SimpleNamespace(
        cuda=cuda,
        randn=Mock(side_effect=[object(), object()]),
        mm=mm,
    )
    return torch, cuda.empty_cache


def test_gpu_benchmark_releases_cache_when_compute_fails() -> None:
    torch, empty_cache = _fake_cuda_torch(Mock(side_effect=RuntimeError("API_KEY=sk-abcdef")))

    with patch.dict(sys.modules, {"torch": torch}):
        result = _benchmark_gpu(max_memory_mb=16, timeout_seconds=5)

    assert result["error"] == "API_KEY=********"
    empty_cache.assert_called_once()


def test_gpu_benchmark_releases_cache_after_measured_run() -> None:
    torch, empty_cache = _fake_cuda_torch(Mock(return_value=object()))

    with patch.dict(sys.modules, {"torch": torch}):
        result = _benchmark_gpu(max_memory_mb=16, timeout_seconds=5)

    assert result["max_memory_mb"] == 16
    empty_cache.assert_called_once()


def test_host_device_transfer_is_bounded_and_releases_cache() -> None:
    host = Mock()
    device = Mock()
    cuda = SimpleNamespace(
        is_available=Mock(return_value=True),
        synchronize=Mock(),
        empty_cache=Mock(),
    )
    torch = SimpleNamespace(
        cuda=cuda,
        empty=Mock(return_value=host),
        empty_like=Mock(return_value=device),
    )

    with patch.dict(sys.modules, {"torch": torch}):
        result = _benchmark_host_device_transfer(max_memory_mb=1024, timeout_seconds=5)

    assert result["transfer_mb"] == 64
    assert result["max_gpu_memory_mb"] == 64
    assert device.copy_.call_count == 3
    assert host.copy_.call_count == 3
    cuda.empty_cache.assert_called_once()


def test_transfer_profile_is_only_added_when_explicitly_requested() -> None:
    with (
        patch("nvidia_agent_doctor.benchmark.runner._benchmark_gpu", return_value={}),
        patch("nvidia_agent_doctor.benchmark.runner._benchmark_system_memory", return_value={}),
        patch("nvidia_agent_doctor.benchmark.runner._benchmark_cuda", return_value={}),
        patch(
            "nvidia_agent_doctor.benchmark.runner._benchmark_host_device_transfer",
            return_value={},
        ) as transfer,
    ):
        default_results = run_benchmarks(max_memory_mb=16, timeout_seconds=5)
        profiled_results = run_benchmarks(
            profile_transfers=True, max_memory_mb=16, timeout_seconds=5
        )

    assert "host_device_transfer" not in default_results
    assert "host_device_transfer" in profiled_results
    transfer.assert_called_once_with(16, 5)


@pytest.mark.parametrize("memory_mb,timeout_seconds", [(15, 5), (16, 0), (1025, 5), (16, 301)])
def test_benchmark_resource_limits_are_enforced(memory_mb: int, timeout_seconds: int) -> None:
    with pytest.raises(ValueError, match="resource limits"):
        run_benchmarks(max_memory_mb=memory_mb, timeout_seconds=timeout_seconds)
