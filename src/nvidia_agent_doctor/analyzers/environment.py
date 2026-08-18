"""NVIDIA Agent Doctor — Environment health analyzer."""

from __future__ import annotations

from nvidia_agent_doctor.collectors.cuda import collect_cuda_info
from nvidia_agent_doctor.collectors.docker import collect_docker_info
from nvidia_agent_doctor.collectors.gpu import collect_gpu_info, nvidia_smi_available
from nvidia_agent_doctor.collectors.python import collect_python_packages
from nvidia_agent_doctor.collectors.system import collect_system_info
from nvidia_agent_doctor.core.result import CheckResult, SectionResult
from nvidia_agent_doctor.core.severity import Severity


def analyze_system() -> SectionResult:
    """Analyze general system environment."""
    section = SectionResult(name="system", display_name="System")
    info = collect_system_info()
    section.metadata["system_info"] = info.model_dump()

    # OS check
    section.checks.append(CheckResult(
        name="os",
        severity=Severity.PASS,
        message=f"OS: {info.os_name} {info.os_release}",
        detail=f"Version: {info.os_version}",
    ))

    # Python version check
    import sys
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 11):
        section.checks.append(CheckResult(
            name="python_version",
            severity=Severity.WARNING,
            message=f"Python {major}.{minor} detected",
            detail="NVIDIA Agent Doctor requires Python 3.11+",
            recommendation="Upgrade to Python 3.11 or newer.",
        ))
    else:
        section.checks.append(CheckResult(
            name="python_version",
            severity=Severity.PASS,
            message=f"Python {major}.{minor}",
        ))

    # RAM
    if info.ram_total_gb is not None:
        if info.ram_total_gb < 4:
            section.checks.append(CheckResult(
                name="ram",
                severity=Severity.WARNING,
                message=f"RAM: {info.ram_total_gb} GB (low)",
                recommendation="AI workloads typically require at least 16 GB RAM.",
            ))
        else:
            section.checks.append(CheckResult(
                name="ram",
                severity=Severity.PASS,
                message=f"RAM: {info.ram_total_gb} GB",
            ))

    return section


def analyze_gpu() -> SectionResult:
    """Analyze NVIDIA GPU presence and health."""
    section = SectionResult(name="gpu", display_name="NVIDIA GPU")

    if not nvidia_smi_available():
        section.checks.append(CheckResult(
            name="nvidia_smi",
            severity=Severity.NOT_INSTALLED,
            message="nvidia-smi not found",
            detail=(
                "Possible reasons: NVIDIA driver not installed, "
                "unsupported container, no NVIDIA GPU, or permissions issue."
            ),
            recommendation="Install NVIDIA drivers if an NVIDIA GPU is present.",
        ))
        return section

    section.checks.append(CheckResult(
        name="nvidia_smi",
        severity=Severity.PASS,
        message="nvidia-smi detected",
    ))

    gpus = collect_gpu_info()
    if not gpus:
        section.checks.append(CheckResult(
            name="gpu_detected",
            severity=Severity.WARNING,
            message="nvidia-smi is available but no GPUs were detected",
            recommendation="Check NVIDIA driver installation and GPU seating.",
        ))
        return section

    section.metadata["gpu_count"] = len(gpus)
    section.metadata["gpus"] = [g.model_dump() for g in gpus]

    for gpu in gpus:
        prefix = f"GPU {gpu.index} ({gpu.name})"

        # VRAM
        if gpu.vram_total_mb is not None:
            section.checks.append(CheckResult(
                name=f"gpu_{gpu.index}_vram",
                severity=Severity.PASS,
                message=f"{prefix}: VRAM {gpu.vram_total_gb} GB",
            ))

        # Utilization
        if gpu.utilization_gpu_pct is not None:
            sev = Severity.WARNING if gpu.utilization_gpu_pct > 95 else Severity.PASS
            section.checks.append(CheckResult(
                name=f"gpu_{gpu.index}_utilization",
                severity=sev,
                message=f"{prefix}: Utilization {gpu.utilization_gpu_pct}%",
            ))

        # Temperature
        if gpu.temperature_c is not None:
            if gpu.temperature_c >= 90:
                sev = Severity.ERROR
                rec: str | None = (
                    "GPU temperature is critically high. "
                    "Check cooling solution and airflow immediately."
                )
            elif gpu.temperature_c >= 80:
                sev = Severity.WARNING
                rec = "GPU temperature is elevated. Monitor cooling."
            else:
                sev = Severity.PASS
                rec = None
            section.checks.append(CheckResult(
                name=f"gpu_{gpu.index}_temperature",
                severity=sev,
                message=f"{prefix}: Temperature {gpu.temperature_c}°C",
                recommendation=rec,
            ))

        # Driver version
        if gpu.driver_version:
            section.checks.append(CheckResult(
                name=f"gpu_{gpu.index}_driver",
                severity=Severity.PASS,
                message=f"{prefix}: Driver {gpu.driver_version}",
            ))

    return section


def analyze_cuda() -> SectionResult:
    """Analyze CUDA installation."""
    section = SectionResult(name="cuda", display_name="CUDA")
    info = collect_cuda_info()
    section.metadata["cuda_info"] = info.model_dump()

    if not info.nvcc_available and info.toolkit_version is None:
        section.checks.append(CheckResult(
            name="cuda_toolkit",
            severity=Severity.NOT_INSTALLED,
            message="CUDA toolkit not detected",
            detail="nvcc not found and no CUDA_HOME/CUDA_PATH configured.",
            recommendation=(
                "Install CUDA toolkit from https://developer.nvidia.com/cuda-downloads "
                "or set CUDA_HOME environment variable."
            ),
        ))
    else:
        section.checks.append(CheckResult(
            name="cuda_toolkit",
            severity=Severity.PASS,
            message=f"CUDA toolkit: {info.toolkit_version or 'detected'}",
            detail=f"nvcc: {info.nvcc_path or 'not in PATH'}",
        ))

    # Runtime version
    if info.runtime_version:
        section.checks.append(CheckResult(
            name="cuda_runtime",
            severity=Severity.PASS,
            message=f"CUDA runtime: {info.runtime_version}",
        ))

    # Compatibility
    if info.compatible is False:
        for note in info.compatibility_notes:
            section.checks.append(CheckResult(
                name="cuda_compatibility",
                severity=Severity.WARNING,
                message="CUDA version mismatch detected",
                detail=note,
                recommendation=(
                    "Use matching CUDA toolkit and runtime versions. "
                    "See https://docs.nvidia.com/cuda/cuda-installation-guide for guidance."
                ),
            ))
    elif info.compatible is True and (info.toolkit_version or info.runtime_version):
        section.checks.append(CheckResult(
            name="cuda_compatibility",
            severity=Severity.PASS,
            message="CUDA toolkit and runtime versions appear compatible",
        ))

    # Environment variables
    if not info.cuda_home and not info.cuda_path:
        section.checks.append(CheckResult(
            name="cuda_env_vars",
            severity=Severity.WARNING,
            message="CUDA_HOME and CUDA_PATH are not set",
            recommendation=(
                "Set CUDA_HOME to your CUDA installation directory "
                "(e.g., /usr/local/cuda)."
            ),
            fix_command='export CUDA_HOME="/usr/local/cuda"',
        ))
    else:
        section.checks.append(CheckResult(
            name="cuda_env_vars",
            severity=Severity.PASS,
            message=f"CUDA_HOME: {info.cuda_home or info.cuda_path}",
        ))

    return section


def analyze_pytorch() -> SectionResult:
    """Analyze PyTorch installation."""
    from nvidia_agent_doctor.integrations.pytorch import check_pytorch

    section = SectionResult(name="pytorch", display_name="PyTorch")
    info = check_pytorch()
    section.metadata["pytorch_info"] = info

    if not info["installed"]:
        section.checks.append(CheckResult(
            name="pytorch_installed",
            severity=Severity.NOT_INSTALLED,
            message="PyTorch not installed",
            recommendation=(
                "Install PyTorch from https://pytorch.org/get-started/locally/ "
                "with the appropriate CUDA version."
            ),
        ))
        return section

    section.checks.append(CheckResult(
        name="pytorch_installed",
        severity=Severity.PASS,
        message=f"PyTorch {info['version']}",
        detail=f"CUDA build: {info.get('cuda_version') or 'CPU-only'}",
    ))

    if info["cuda_available"]:
        devices = info.get("devices", [])
        device_str = ", ".join(devices) if devices else "unknown"
        section.checks.append(CheckResult(
            name="pytorch_cuda",
            severity=Severity.PASS,
            message=f"CUDA available: {info['device_count']} device(s)",
            detail=f"Device(s): {device_str}",
        ))

        # Basic compute
        if info.get("basic_compute_pass") is True:
            section.checks.append(CheckResult(
                name="pytorch_compute",
                severity=Severity.PASS,
                message="Basic GPU computation: PASS",
            ))
        elif info.get("basic_compute_pass") is False:
            section.checks.append(CheckResult(
                name="pytorch_compute",
                severity=Severity.ERROR,
                message="Basic GPU computation: FAILED",
                detail=info.get("compute_error"),
                recommendation="Check CUDA toolkit and PyTorch compatibility.",
            ))
    else:
        section.checks.append(CheckResult(
            name="pytorch_cuda",
            severity=Severity.WARNING,
            message="CUDA not available in PyTorch",
            detail="PyTorch is installed but cannot detect CUDA.",
            recommendation=(
                "Install a CUDA-enabled PyTorch build from pytorch.org. "
                "Ensure CUDA drivers and toolkit are properly installed."
            ),
        ))

    return section


def analyze_docker() -> SectionResult:
    """Analyze Docker runtime."""
    section = SectionResult(name="docker", display_name="Docker")
    info = collect_docker_info()
    section.metadata["docker_info"] = info.model_dump()

    if info.in_container:
        section.checks.append(CheckResult(
            name="in_container",
            severity=Severity.PASS,
            message="Running inside a container",
            detail=f"Container ID: {info.container_id or 'unknown'}",
        ))

    if not info.docker_available:
        section.checks.append(CheckResult(
            name="docker_available",
            severity=Severity.NOT_INSTALLED,
            message="Docker not available",
            detail="Docker CLI not found or daemon not running.",
        ))
        return section

    section.checks.append(CheckResult(
        name="docker_available",
        severity=Severity.PASS,
        message=f"Docker: {info.docker_version or 'detected'}",
        detail=f"Server: {info.docker_server_version or 'unknown'}",
    ))

    if info.nvidia_runtime_available:
        section.checks.append(CheckResult(
            name="nvidia_runtime",
            severity=Severity.PASS,
            message="NVIDIA container runtime detected",
        ))
    else:
        section.checks.append(CheckResult(
            name="nvidia_runtime",
            severity=Severity.NOT_INSTALLED,
            message="NVIDIA container runtime not detected",
            recommendation=(
                "Install nvidia-container-toolkit to run GPU containers: "
                "https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
            ),
        ))

    return section
