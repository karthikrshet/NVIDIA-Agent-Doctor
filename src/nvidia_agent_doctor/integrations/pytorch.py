"""NVIDIA Agent Doctor — PyTorch integration."""

from __future__ import annotations

from typing import Any

from nvidia_agent_doctor.security.credentials import redact_text


def check_pytorch() -> dict[str, Any]:
    """
    Perform a lightweight PyTorch health check.
    Returns a dict with version info and basic compute check results.
    Never raises.
    """
    result: dict[str, Any] = {
        "installed": False,
        "version": None,
        "cuda_version": None,
        "cuda_available": False,
        "device_count": 0,
        "devices": [],
        "bf16_support": None,
        "fp16_support": None,
        "basic_compute_pass": None,
        "error": None,
    }

    try:
        import torch

        result["installed"] = True
        result["version"] = torch.__version__
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
