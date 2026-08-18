"""NVIDIA Agent Doctor — Benchmark runner."""

from __future__ import annotations

import time
from typing import Any


def run_benchmarks(gpu_only: bool = False) -> dict[str, Any]:
    """
    Run available benchmarks. Returns results dict.
    All benchmarks are lightweight and opt-in.
    """
    results: dict[str, Any] = {}

    # GPU benchmark
    results["gpu_basic"] = _benchmark_gpu()

    if not gpu_only:
        results["system_memory"] = _benchmark_system_memory()
        results["cuda_basic"] = _benchmark_cuda()

    return results


def _benchmark_gpu() -> dict[str, Any]:
    """Basic GPU compute benchmark using PyTorch if available."""
    try:
        import torch
        if not torch.cuda.is_available():
            return {"skipped": True, "reason": "CUDA not available"}

        # Warm up
        size = 2048
        a = torch.randn(size, size, device="cuda")
        b = torch.randn(size, size, device="cuda")
        torch.cuda.synchronize()

        # Benchmark matrix multiply (3 runs)
        times: list[float] = []
        for _ in range(3):
            start = time.perf_counter()
            _ = torch.mm(a, b)
            torch.cuda.synchronize()
            times.append(time.perf_counter() - start)

        avg_ms = round(sum(times) / len(times) * 1000, 2)
        flops = 2 * size**3  # FLOPs for matmul
        tflops = round(flops / (avg_ms / 1000) / 1e12, 3)

        return {
            "operation": f"matmul {size}x{size}",
            "avg_latency_ms": avg_ms,
            "tflops": tflops,
            "note": "Measured result on this hardware at time of benchmark.",
        }
    except ImportError:
        return {"skipped": True, "reason": "PyTorch not installed"}
    except Exception as e:
        return {"error": str(e)}


def _benchmark_cuda() -> dict[str, Any]:
    """Basic CUDA memory bandwidth benchmark."""
    try:
        import torch
        if not torch.cuda.is_available():
            return {"skipped": True, "reason": "CUDA not available"}

        # Allocate 512MB tensor
        size = 128 * 1024 * 1024  # 128M float32 = 512MB
        src = torch.rand(size, device="cuda")
        torch.cuda.synchronize()

        times: list[float] = []
        for _ in range(3):
            start = time.perf_counter()
            dst = src.clone()
            torch.cuda.synchronize()
            times.append(time.perf_counter() - start)
        del src, dst

        avg_s = sum(times) / len(times)
        bytes_copied = size * 4  # float32 = 4 bytes
        bandwidth_gb_s = round((bytes_copied / avg_s) / 1e9, 2)

        return {
            "operation": "CUDA memory copy (512MB)",
            "avg_latency_ms": round(avg_s * 1000, 2),
            "bandwidth_gb_s": bandwidth_gb_s,
            "note": "Measured result on this hardware at time of benchmark.",
        }
    except ImportError:
        return {"skipped": True, "reason": "PyTorch not installed"}
    except Exception as e:
        return {"error": str(e)}


def _benchmark_system_memory() -> dict[str, Any]:
    """Basic system memory bandwidth benchmark."""
    try:
        import array
        size = 64 * 1024 * 1024  # 64M integers = 256MB

        a = array.array("f", [1.0] * size)
        start = time.perf_counter()
        b = array.array("f", a)  # copy
        elapsed = time.perf_counter() - start

        bandwidth_gb_s = round((size * 4) / elapsed / 1e9, 2)
        return {
            "operation": "System memory copy (256MB)",
            "avg_latency_ms": round(elapsed * 1000, 2),
            "bandwidth_gb_s": bandwidth_gb_s,
            "note": "Measured result at time of benchmark.",
        }
    except Exception as e:
        return {"error": str(e)}
