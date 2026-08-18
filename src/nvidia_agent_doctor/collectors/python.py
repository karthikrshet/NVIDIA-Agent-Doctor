"""NVIDIA Agent Doctor — Python package version collector."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from typing import Any

from nvidia_agent_doctor.core.models import PythonPackageInfo

_PACKAGES_TO_CHECK = [
    "torch",
    "tensorrt",
    "tritonclient",
    "nemo",
    "transformers",
    "accelerate",
    "diffusers",
    "onnxruntime",
    "onnxruntime_gpu",
    "cupy",
    "numba",
    "jax",
]


def collect_python_packages(extra_packages: list[str] | None = None) -> list[PythonPackageInfo]:
    """Collect installed Python package versions. Never raises."""
    packages = _PACKAGES_TO_CHECK + (extra_packages or [])
    results: list[PythonPackageInfo] = []

    for pkg in packages:
        info = _check_package(pkg)
        results.append(info)

    return results


def _check_package(package_name: str) -> PythonPackageInfo:
    """Check if a package is installed and gather metadata."""
    # Normalize package name for import
    import_name = package_name.replace("-", "_").replace("onnxruntime_gpu", "onnxruntime")

    spec = importlib.util.find_spec(import_name)
    if spec is None:
        return PythonPackageInfo(package=package_name, installed=False)

    version = _get_package_version(package_name, import_name)
    extra: dict[str, Any] = {}

    # Special handling for PyTorch
    if import_name == "torch":
        extra = _get_torch_info()

    return PythonPackageInfo(
        package=package_name,
        version=version,
        installed=True,
        cuda_version=extra.pop("cuda_version", None),
        extra=extra,
    )


def _get_package_version(package_name: str, import_name: str) -> str | None:
    """Get package version via importlib.metadata or __version__ attribute."""
    try:
        from importlib.metadata import version

        return version(package_name)
    except Exception:
        pass

    try:
        mod = __import__(import_name)
        return getattr(mod, "__version__", None)
    except Exception:
        pass

    # Last resort: pip show
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            capture_output=True,
            text=True,
            timeout=15,
        )
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass

    return None


def _get_torch_info() -> dict[str, Any]:
    """Gather PyTorch-specific info (CUDA availability, device count, etc.)."""
    extra: dict[str, Any] = {}
    try:
        import torch

        extra["cuda_version"] = getattr(torch.version, "cuda", None)
        extra["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            extra["device_count"] = torch.cuda.device_count()
            devices = []
            for i in range(torch.cuda.device_count()):
                try:
                    devices.append(torch.cuda.get_device_name(i))
                except Exception:
                    devices.append("Unknown")
            extra["devices"] = devices

            # BF16 / FP16 support detection
            try:
                props = torch.cuda.get_device_properties(0)
                # BF16 supported on Ampere (SM 8.0) and above
                compute_major = props.major
                extra["bf16_support"] = compute_major >= 8
                extra["fp16_support"] = compute_major >= 7
                extra["compute_capability"] = f"{props.major}.{props.minor}"
            except Exception:
                pass
        else:
            extra["device_count"] = 0
            extra["devices"] = []
    except ImportError:
        pass
    except Exception:
        pass
    return extra
