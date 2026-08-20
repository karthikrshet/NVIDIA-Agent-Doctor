"""NVIDIA Agent Doctor — Benchmark runner."""

from __future__ import annotations

import time
from math import isqrt
from typing import Any

from nvidia_agent_doctor.security.credentials import redact_text

DEFAULT_MAX_MEMORY_MB = 128
DEFAULT_TIMEOUT_SECONDS = 15
_MAX_TRANSFER_MEMORY_MB = 64


def run_benchmarks(
    gpu_only: bool = False,
    profile_transfers: bool = False,
    max_memory_mb: int = DEFAULT_MAX_MEMORY_MB,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Run available benchmarks. Returns results dict.
    All benchmarks are lightweight and opt-in.
    """
    if not 16 <= max_memory_mb <= 1024 or not 1 <= timeout_seconds <= 300:
        raise ValueError("Invalid benchmark resource limits")
    results: dict[str, Any] = {}

    # GPU benchmark
    results["gpu_basic"] = _benchmark_gpu(max_memory_mb, timeout_seconds)

    if not gpu_only:
        results["system_memory"] = _benchmark_system_memory(max_memory_mb, timeout_seconds)
        results["cuda_basic"] = _benchmark_cuda(max_memory_mb, timeout_seconds)

    if profile_transfers:
        results["host_device_transfer"] = _benchmark_host_device_transfer(
            max_memory_mb, timeout_seconds
        )

    return results


def _benchmark_gpu(max_memory_mb: int, timeout_seconds: int) -> dict[str, Any]:
    """Basic GPU compute benchmark using PyTorch if available."""
    try:
        import torch

        if not torch.cuda.is_available():
            return {"skipped": True, "reason": "CUDA not available"}

        a: Any | None = None
        b: Any | None = None
        try:
            # Inputs and output are bounded by the configured memory budget.
            size = max(128, isqrt((max_memory_mb * 1024 * 1024) // 12))
            deadline = time.monotonic() + timeout_seconds
            a = torch.randn(size, size, device="cuda")
            b = torch.randn(size, size, device="cuda")
            torch.cuda.synchronize()
            times: list[float] = []
            for _ in range(3):
                if time.monotonic() >= deadline:
                    raise TimeoutError("GPU benchmark exceeded timeout")
                start = time.perf_counter()
                output = torch.mm(a, b)
                torch.cuda.synchronize()
                del output
                times.append(time.perf_counter() - start)
            avg_ms = round(sum(times) / len(times) * 1000, 2)
            return {
                "operation": f"matmul {size}x{size}",
                "avg_latency_ms": avg_ms,
                "tflops": round((2 * size**3) / (avg_ms / 1000) / 1e12, 3),
                "max_memory_mb": max_memory_mb,
            }
        except Exception as exc:
            return {"error": redact_text(str(exc))}
        finally:
            del a, b
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass
    except ImportError:
        return {"skipped": True, "reason": "PyTorch not installed"}
    except Exception as exc:
        return {"error": redact_text(str(exc))}


def _benchmark_cuda(max_memory_mb: int, timeout_seconds: int) -> dict[str, Any]:
    """Basic CUDA memory bandwidth benchmark."""
    try:
        import torch

        if not torch.cuda.is_available():
            return {"skipped": True, "reason": "CUDA not available"}

        src: Any | None = None
        try:
            size = (max_memory_mb * 1024 * 1024) // 8
            deadline = time.monotonic() + timeout_seconds
            src = torch.rand(size, device="cuda")
            times: list[float] = []
            for _ in range(3):
                if time.monotonic() >= deadline:
                    raise TimeoutError("CUDA copy benchmark exceeded timeout")
                start = time.perf_counter()
                dst = src.clone()
                torch.cuda.synchronize()
                del dst
                times.append(time.perf_counter() - start)
            avg_s = sum(times) / len(times)
            return {
                "operation": f"CUDA memory copy ({max_memory_mb // 2}MB)",
                "avg_latency_ms": round(avg_s * 1000, 2),
                "bandwidth_gb_s": round((size * 4 / avg_s) / 1e9, 2),
                "max_memory_mb": max_memory_mb,
            }
        except Exception as exc:
            return {"error": redact_text(str(exc))}
        finally:
            del src
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass
    except ImportError:
        return {"skipped": True, "reason": "PyTorch not installed"}
    except Exception as exc:
        return {"error": redact_text(str(exc))}


def _benchmark_host_device_transfer(max_memory_mb: int, timeout_seconds: int) -> dict[str, Any]:
    """Measure bounded host↔GPU copies without claiming a specific bus topology.

    The host buffer and GPU buffer use at most 64 MiB each. The GPU allocation
    remains within the caller's configured device-memory budget. This is opt-in
    because pinned host memory and synchronization can affect an active workload.
    """
    try:
        import torch

        if not torch.cuda.is_available():
            return {"skipped": True, "reason": "CUDA not available"}

        transfer_mb = min(max_memory_mb, _MAX_TRANSFER_MEMORY_MB)
        element_count = (transfer_mb * 1024 * 1024) // 4
        host: Any | None = None
        device: Any | None = None
        try:
            host = torch.empty(element_count, pin_memory=True)
            device = torch.empty_like(host, device="cuda")
            deadline = time.monotonic() + timeout_seconds
            h2d_times = _measure_copy(device, host, deadline, torch)
            d2h_times = _measure_copy(host, device, deadline, torch)
            bytes_transferred = element_count * 4
            h2d_seconds = sum(h2d_times) / len(h2d_times)
            d2h_seconds = sum(d2h_times) / len(d2h_times)
            return {
                "operation": "host-device transfer",
                "transport": "Measured host-device path; PCIe/NVLink topology is not inferred.",
                "transfer_mb": transfer_mb,
                "host_to_device_bandwidth_gb_s": round(bytes_transferred / h2d_seconds / 1e9, 2),
                "device_to_host_bandwidth_gb_s": round(bytes_transferred / d2h_seconds / 1e9, 2),
                "samples": 3,
                "max_gpu_memory_mb": transfer_mb,
            }
        except Exception as exc:
            return {"error": redact_text(str(exc))}
        finally:
            del host, device
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass
    except ImportError:
        return {"skipped": True, "reason": "PyTorch not installed"}
    except Exception as exc:
        return {"error": redact_text(str(exc))}


def _measure_copy(destination: Any, source: Any, deadline: float, torch: Any) -> list[float]:
    """Return three synchronized copy timings while enforcing the soft deadline."""
    times: list[float] = []
    for _ in range(3):
        if time.monotonic() >= deadline:
            raise TimeoutError("Host-device transfer benchmark exceeded timeout")
        torch.cuda.synchronize()
        start = time.perf_counter()
        destination.copy_(source, non_blocking=True)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - start
        if time.monotonic() >= deadline:
            raise TimeoutError("Host-device transfer benchmark exceeded timeout")
        times.append(elapsed)
    return times


def _benchmark_system_memory(max_memory_mb: int, timeout_seconds: int) -> dict[str, Any]:
    """Basic system memory bandwidth benchmark."""
    try:
        import array

        size = min(max_memory_mb, 32) * 1024 * 1024 // 4

        a = array.array("f", [1.0]) * size
        start = time.perf_counter()
        _copy = array.array("f", a)  # copy
        elapsed = time.perf_counter() - start
        if elapsed > timeout_seconds:
            raise TimeoutError("System memory benchmark exceeded timeout")

        bandwidth_gb_s = round((size * 4) / elapsed / 1e9, 2)
        return {
            "operation": f"System memory copy ({size * 4 // (1024 * 1024)}MB)",
            "avg_latency_ms": round(elapsed * 1000, 2),
            "bandwidth_gb_s": bandwidth_gb_s,
            "note": "Measured result at time of benchmark.",
        }
    except Exception as exc:
        return {"error": redact_text(str(exc))}
