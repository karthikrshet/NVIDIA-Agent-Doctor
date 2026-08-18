"""NVIDIA Agent Doctor — CUDA installation collector."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from nvidia_agent_doctor.core.models import CUDAInfo

# NVIDIA's CUDA Compatibility Guide publishes these minimum driver major
# versions for minor-version compatibility. Keep this small, sourced table at
# the major-family level; exact release compatibility remains an NVIDIA matrix
# lookup and is not guessed here.
_MIN_DRIVER_MAJOR_BY_CUDA_MAJOR = {"11": 450, "12": 525, "13": 580}
_CUDA_COMPATIBILITY_URL = "https://docs.nvidia.com/deploy/cuda-compatibility/"


def collect_cuda_info(nvidia_smi_available: bool | None = None) -> CUDAInfo:
    """Collect CUDA installation details from environment and filesystem. Never raises."""
    cuda_home = os.environ.get("CUDA_HOME")
    cuda_path = os.environ.get("CUDA_PATH")
    ld_lib = os.environ.get("LD_LIBRARY_PATH")
    cuda_visible = os.environ.get("CUDA_VISIBLE_DEVICES")

    nvcc_path = shutil.which("nvcc")
    nvcc_available = nvcc_path is not None
    toolkit_version = _detect_toolkit_version(nvcc_path, cuda_home, cuda_path)

    smi_available = shutil.which("nvidia-smi") is not None if nvidia_smi_available is None else nvidia_smi_available
    runtime_version = _detect_runtime_version(smi_available)
    driver_version = _detect_driver_cuda_version(smi_available)

    libraries = _find_cuda_libraries(cuda_home, cuda_path, ld_lib)

    compatible, notes = _check_compatibility(toolkit_version, runtime_version, driver_version)

    return CUDAInfo(
        toolkit_version=toolkit_version,
        runtime_version=runtime_version,
        driver_version=driver_version,
        nvcc_path=nvcc_path,
        nvcc_available=nvcc_available,
        cuda_home=cuda_home,
        cuda_path=cuda_path,
        ld_library_path=ld_lib,
        cuda_visible_devices=cuda_visible,
        libraries_found=libraries,
        compatible=compatible,
        compatibility_notes=notes,
    )


def _detect_toolkit_version(
    nvcc_path: str | None,
    cuda_home: str | None,
    cuda_path: str | None,
) -> str | None:
    """Attempt to detect CUDA toolkit version via nvcc --version."""
    if nvcc_path:
        try:
            result = subprocess.run(
                [nvcc_path, "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return _parse_nvcc_version(result.stdout)
        except Exception:
            pass

    # Search for version file in CUDA_HOME / CUDA_PATH
    for base in [cuda_home, cuda_path]:
        if not base:
            continue
        version_file = Path(base) / "version.txt"
        if version_file.exists():
            try:
                content = version_file.read_text().strip()
                match = re.search(r"(\d+\.\d+(?:\.\d+)?)", content)
                if match:
                    return match.group(1)
            except OSError:
                pass

        # Modern CUDA uses version.json
        version_json = Path(base) / "version.json"
        if version_json.exists():
            try:
                import json

                data = json.loads(version_json.read_text())
                cuda_data = data.get("cuda", {})
                version = cuda_data.get("version")
                if version:
                    return str(version)
            except Exception:
                pass

    return None


def _parse_nvcc_version(output: str) -> str | None:
    """Extract version from nvcc --version output."""
    match = re.search(r"release (\d+\.\d+(?:\.\d+)?)", output)
    if match:
        return match.group(1)
    return None


def _detect_runtime_version(nvidia_smi_available: bool = True) -> str | None:
    """Detect CUDA runtime version via libcudart or torch."""
    # Try via PyTorch if available
    if not nvidia_smi_available:
        return None
    try:
        import torch

        if hasattr(torch, "version") and hasattr(torch.version, "cuda"):
            cuda_ver = torch.version.cuda
            if cuda_ver:
                return str(cuda_ver)
    except ImportError:
        pass

    # Try via nvidia-smi
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            match = re.search(r"CUDA Version:\s+(\d+\.\d+)", result.stdout)
            if match:
                return match.group(1)
    except Exception:
        pass

    return None


def _detect_driver_cuda_version(nvidia_smi_available: bool = True) -> str | None:
    """Detect the max CUDA version supported by the installed driver."""
    if not nvidia_smi_available:
        return None
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            driver = result.stdout.strip().splitlines()[0].strip()
            if driver:
                return driver
    except Exception:
        pass
    return None


def _find_cuda_libraries(
    cuda_home: str | None,
    cuda_path: str | None,
    ld_lib_path: str | None,
) -> list[str]:
    """Search for common CUDA libraries."""
    important_libs = [
        "libcudart",
        "libcublas",
        "libcufft",
        "libcurand",
        "libcusolver",
        "libcusparse",
        "libnccl",
        "libnvrtc",
    ]
    found: list[str] = []

    search_dirs: list[Path] = []
    for base in [cuda_home, cuda_path]:
        if base:
            search_dirs.extend(
                [
                    Path(base) / "lib64",
                    Path(base) / "lib",
                ]
            )

    if ld_lib_path:
        for p in ld_lib_path.split(":"):
            if p:
                search_dirs.append(Path(p))

    for lib in important_libs:
        for d in search_dirs:
            try:
                matches = list(d.glob(f"{lib}*"))
                if matches:
                    found.append(lib)
                    break
            except (PermissionError, OSError):
                continue

    return found


def _check_compatibility(
    toolkit: str | None,
    runtime: str | None,
    driver: str | None,
) -> tuple[bool | None, list[str]]:
    """
    Very basic compatibility check. We do NOT invent rules.
    We only flag obvious major version mismatches.
    """
    if toolkit is None and runtime is None:
        return None, []

    notes: list[str] = []

    if toolkit and runtime:
        tk_major = _major_version(toolkit)
        rt_major = _major_version(runtime)
        if tk_major and rt_major and tk_major != rt_major:
            notes.append(
                f"CUDA toolkit major version ({toolkit}) differs from "
                f"detected runtime version ({runtime}). This may cause "
                "runtime compatibility issues. Refer to NVIDIA CUDA "
                "release notes for your specific combination."
            )
            return False, notes

    cuda_version = toolkit or runtime
    if cuda_version and driver:
        cuda_major = _major_version(cuda_version)
        required_driver = _MIN_DRIVER_MAJOR_BY_CUDA_MAJOR.get(cuda_major or "")
        driver_major = _major_version(driver)
        if required_driver and driver_major:
            try:
                if int(driver_major) < required_driver:
                    notes.append(
                        f"NVIDIA driver {driver} is below the documented minimum "
                        f"{required_driver} for CUDA {cuda_major}.x minor-version compatibility. "
                        f"See {_CUDA_COMPATIBILITY_URL}"
                    )
                    return False, notes
            except ValueError:
                notes.append(
                    f"Could not parse NVIDIA driver version {driver}; verify it against "
                    f"{_CUDA_COMPATIBILITY_URL}"
                )

    compatible = not notes
    return compatible if (toolkit or runtime) else None, notes


def _major_version(version_str: str) -> str | None:
    parts = version_str.split(".")
    return parts[0] if parts else None
