"""Regression tests for bounded, redacted GPU benchmark behavior."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from nvidia_agent_doctor.benchmark.runner import _benchmark_gpu, run_benchmarks


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


@pytest.mark.parametrize("memory_mb,timeout_seconds", [(15, 5), (16, 0), (1025, 5), (16, 301)])
def test_benchmark_resource_limits_are_enforced(memory_mb: int, timeout_seconds: int) -> None:
    with pytest.raises(ValueError, match="resource limits"):
        run_benchmarks(max_memory_mb=memory_mb, timeout_seconds=timeout_seconds)
