"""NVIDIA Agent Doctor — PyTorch integration."""

from __future__ import annotations

import re
from importlib import metadata
from typing import Any

from nvidia_agent_doctor.security.credentials import redact_text


def check_pytorch(probe_runtime: bool = True) -> dict[str, Any]:
    """
    Inspect PyTorch and, when requested, run a lightweight runtime health check.

    ``probe_runtime=False`` reads only installed-package metadata. This avoids
    importing PyTorch or initializing CUDA during the default doctor command.
    A metadata-only result deliberately does not claim that CUDA is available.

    Returns a dict with version info and basic compute check results.
    Never raises.
    """
    result: dict[str, Any] = {
        "installed": False,
        "version": None,
        "cuda_version": None,
        "cuda_build_metadata": None,
        "runtime_probed": False,
        "cuda_available": False,
        "device_count": 0,
        "devices": [],
        "bf16_support": None,
        "fp16_support": None,
        "basic_compute_pass": None,
        "error": None,
    }

    if not probe_runtime:
        try:
            version = metadata.version("torch")
        except metadata.PackageNotFoundError:
            return result
        except Exception as exc:
            result["error"] = redact_text(str(exc))
            return result

        result["installed"] = True
        result["version"] = version
        result["cuda_build_metadata"] = _cuda_build_from_distribution_version(version)
        return result

    try:
        import torch

        result["installed"] = True
        result["version"] = torch.__version__
        result["runtime_probed"] = True
        result["cuda_version"] = getattr(torch.version, "cuda", None)
        result["cuda_available"] = torch.cuda.is_available()

        if torch.cuda.is_available():
            count = torch.cuda.device_count()
            result["device_count"] = count
            devices = []
            for i in range(count):
                try:
                    devices.append(torch.cuda.get_device_name(i))
                except Exception:
                    devices.append("Unknown")
            result["devices"] = devices

            # Compute capability for FP16/BF16 detection
            try:
                props = torch.cuda.get_device_properties(0)
                major = props.major
                result["bf16_support"] = major >= 8  # Ampere+
                result["fp16_support"] = major >= 7  # Volta+
                result["compute_capability"] = f"{props.major}.{props.minor}"
            except Exception:
                pass

            # Lightweight compute check: allocate small tensor and do a dot product
            a: Any | None = None
            b: Any | None = None
            try:
                a = torch.tensor([1.0, 2.0, 3.0], device="cuda")
                b = torch.tensor([4.0, 5.0, 6.0], device="cuda")
                dot = torch.dot(a, b).item()
                result["basic_compute_pass"] = abs(dot - 32.0) < 0.001
            except Exception as exc:
                result["basic_compute_pass"] = False
                result["compute_error"] = redact_text(str(exc))
            finally:
                del a, b
                try:
                    torch.cuda.empty_cache()
                except Exception:
                    pass

    except ImportError:
        pass
    except Exception as exc:
        result["error"] = redact_text(str(exc))

    return result


def _cuda_build_from_distribution_version(version: str) -> str | None:
    """Return an informational CUDA build label from a PyTorch wheel version.

    This is package metadata only: it is not proof that the installed runtime
    can initialize CUDA on the current host.
    """
    match = re.search(r"\+cu(\d{3,4})$", version)
    if not match:
        return None
    digits = match.group(1)
    if len(digits) == 3:
        return f"{digits[:2]}.{digits[2]}"
    return f"{digits[:2]}.{digits[2:]}"
