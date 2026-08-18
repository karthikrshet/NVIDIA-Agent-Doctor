"""NVIDIA Agent Doctor — GPU information collector via nvidia-smi."""

from __future__ import annotations

import shutil
import subprocess

from defusedxml import ElementTree

from nvidia_agent_doctor.core.models import GPUInfo


def collect_gpu_info() -> list[GPUInfo] | None:
    """Collect GPU info using nvidia-smi XML output.

    Returns a list of GPUInfo objects, or None if nvidia-smi is unavailable.
    Never raises.
    """
    xml_output = _run_nvidia_smi_xml()
    if xml_output is None:
        return None

    try:
        gpus = _parse_nvidia_smi_xml(xml_output)
        return _supplement_compute_capabilities(gpus)
    except Exception:
        # Fallback to query mode
        return _collect_via_query()


def nvidia_smi_available() -> bool:
    """Check whether nvidia-smi can list at least one usable GPU.

    ``--version`` is not accepted by some older Windows driver releases even
    when ordinary, XML, and query invocations work. NVIDIA documents ``-L`` as
    the portable GPU-listing operation, so it is a better capability probe.
    """
    smi_path = shutil.which("nvidia-smi")
    if smi_path is None:
        return False
    try:
        result = subprocess.run(
            [smi_path, "-L"], capture_output=True, text=True, timeout=10, check=False
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _run_nvidia_smi_xml() -> str | None:
    """Run nvidia-smi and return XML output, or None on failure."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "-q", "--xml-format"], capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def _parse_nvidia_smi_xml(xml_str: str) -> list[GPUInfo]:
    """Parse nvidia-smi XML output into GPUInfo objects."""
    root = ElementTree.fromstring(xml_str)
    driver_version = _xml_text(root, "driver_version")
    cuda_version = _xml_text(root, "cuda_version")

    gpus: list[GPUInfo] = []
    for idx, gpu_elem in enumerate(root.findall("gpu")):
        uuid = gpu_elem.get("id") or _xml_text(gpu_elem, "uuid")
        name = _xml_text(gpu_elem, "product_name") or "Unknown"
        compute_cap = _xml_text(gpu_elem, "compute_capability/major")
        compute_cap_minor = _xml_text(gpu_elem, "compute_capability/minor")
        if compute_cap and compute_cap_minor:
            compute_cap = f"{compute_cap}.{compute_cap_minor}"

        vram_total_mb = _parse_mb(_xml_text(gpu_elem, "fb_memory_usage/total"))
        vram_used_mb = _parse_mb(_xml_text(gpu_elem, "fb_memory_usage/used"))

        util_gpu = _parse_pct(_xml_text(gpu_elem, "utilization/gpu_util"))
        util_mem = _parse_pct(_xml_text(gpu_elem, "utilization/memory_util"))

        temp = _parse_int(_xml_text(gpu_elem, "temperature/gpu_temp"))

        power_draw = _parse_float(
            _xml_text(gpu_elem, "gpu_power_readings/power_draw")
            or _xml_text(gpu_elem, "power_readings/power_draw")
        )
        power_limit = _parse_float(
            _xml_text(gpu_elem, "gpu_power_readings/power_limit")
            or _xml_text(gpu_elem, "power_readings/power_limit")
        )

        persistence = _xml_text(gpu_elem, "persistence_mode")

        gpus.append(
            GPUInfo(
                index=idx,
                name=name,
                uuid=uuid,
                driver_version=driver_version,
                cuda_version=cuda_version,
                vram_total_mb=vram_total_mb,
                vram_used_mb=vram_used_mb,
                utilization_gpu_pct=util_gpu,
                utilization_memory_pct=util_mem,
                temperature_c=temp,
                power_draw_w=power_draw,
                power_limit_w=power_limit,
                compute_capability=compute_cap,
                persistence_mode=(persistence == "Enabled") if persistence else None,
            )
        )

    return gpus


def _collect_via_query() -> list[GPUInfo] | None:
    """Fallback: collect GPU info using nvidia-smi --query-gpu."""
    query_fields = [
        "index",
        "name",
        "driver_version",
        "memory.total",
        "memory.used",
        "utilization.gpu",
        "utilization.memory",
        "temperature.gpu",
        "compute_cap",
    ]
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                f"--query-gpu={','.join(query_fields)}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        gpus: list[GPUInfo] = []
        for line in result.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue
            idx = _safe_int(parts[0]) or len(gpus)
            gpus.append(
                GPUInfo(
                    index=idx,
                    name=parts[1] if len(parts) > 1 else "Unknown",
                    driver_version=parts[2] if len(parts) > 2 else None,
                    vram_total_mb=_safe_int(parts[3]) if len(parts) > 3 else None,
                    vram_used_mb=_safe_int(parts[4]) if len(parts) > 4 else None,
                    utilization_gpu_pct=_safe_int(parts[5]) if len(parts) > 5 else None,
                    utilization_memory_pct=_safe_int(parts[6]) if len(parts) > 6 else None,
                    temperature_c=_safe_int(parts[7]) if len(parts) > 7 else None,
                    compute_capability=parts[8] if len(parts) > 8 and parts[8] != "N/A" else None,
                )
            )
        return gpus or None
    except Exception:
        return None


def _supplement_compute_capabilities(gpus: list[GPUInfo]) -> list[GPUInfo]:
    """Fill XML omissions with a single documented nvidia-smi query.

    Some older driver XML schemas omit ``compute_capability`` even though the
    installed query interface supports ``compute_cap``. Query only when needed
    so normal modern XML collection remains a single subprocess call.
    """
    if not any(gpu.compute_capability is None for gpu in gpus):
        return gpus
    try:
        result = subprocess.run(
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
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return gpus
    if result.returncode != 0:
        return gpus

    compute_by_index: dict[int, str] = {}
    for line in result.stdout.splitlines():
        index_text, separator, compute_capability = line.partition(",")
        index = _safe_int(index_text.strip())
        value = compute_capability.strip()
        if separator and index is not None and value not in {"", "N/A"}:
            compute_by_index[index] = value
    for gpu in gpus:
        if gpu.compute_capability is None:
            gpu.compute_capability = compute_by_index.get(gpu.index)
    return gpus


# ── Parsing helpers ────────────────────────────────────────────────────────────


def _xml_text(elem: ElementTree.Element, path: str) -> str | None:
    child = elem.find(path)
    if child is not None and child.text:
        text = child.text.strip()
        return text if text not in ("N/A", "Unknown", "") else None
    return None


def _parse_mb(value: str | None) -> int | None:
    if not value:
        return None
    # Expected format: "24564 MiB" or "24564 MB"
    try:
        return int(value.split()[0])
    except (ValueError, IndexError):
        return None


def _parse_pct(value: str | None) -> int | None:
    if not value:
        return None
    # Expected format: "71 %"
    try:
        return int(value.split()[0])
    except (ValueError, IndexError):
        return None


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value.split()[0])
    except (ValueError, IndexError):
        return None


def _parse_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.split()[0])
    except (ValueError, IndexError):
        return None


def _safe_int(value: str) -> int | None:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def get_nvidia_smi_version() -> str | None:
    """Return nvidia-smi version string or None.

    Older drivers can reject the otherwise documented ``--version`` flag. In
    that case, the default read-only summary still contains the version.
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "NVIDIA-SMI" in line or "version" in line.lower():
                    return line.strip()
            return result.stdout.strip().splitlines()[0] if result.stdout.strip() else None
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
