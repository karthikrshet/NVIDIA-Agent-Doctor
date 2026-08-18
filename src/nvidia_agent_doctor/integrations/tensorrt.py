"""NVIDIA Agent Doctor — TensorRT integration."""

from __future__ import annotations

from typing import Any

from nvidia_agent_doctor.security.credentials import redact_text


def check_tensorrt() -> dict[str, Any]:
    """
    Detect TensorRT installation and perform a basic health check.
    Never raises.
    """
    result: dict[str, Any] = {
        "installed": False,
        "version": None,
        "cuda_compatible": None,
        "python_bindings": False,
        "builder_available": None,
        "runtime_available": None,
        "pytorch_cuda_available": None,
        "error": None,
    }

    try:
        import tensorrt as trt

        result["installed"] = True
        result["python_bindings"] = True
        result["version"] = getattr(trt, "__version__", None)

        # Check builder
        try:
            logger = trt.Logger(trt.Logger.WARNING)
            builder = trt.Builder(logger)
            result["builder_available"] = builder is not None
            del builder
        except Exception as exc:
            result["builder_available"] = False
            result["builder_error"] = redact_text(str(exc))

        # Check runtime
        try:
            logger = trt.Logger(trt.Logger.WARNING)
            runtime = trt.Runtime(logger)
            result["runtime_available"] = runtime is not None
            del runtime
        except Exception as exc:
            result["runtime_available"] = False
            result["runtime_error"] = redact_text(str(exc))

        # PyTorch CUDA availability is useful context, but it does not prove a
        # TensorRT/CUDA support-matrix combination. Leave cuda_compatible
        # unknown unless a future authoritative verifier establishes it.
        try:
            import torch

            result["pytorch_cuda_available"] = torch.cuda.is_available()
        except ImportError:
            result["cuda_compatible"] = None
        except Exception as exc:
            result["pytorch_cuda_error"] = redact_text(str(exc))

    except ImportError:
        pass
    except Exception as exc:
        result["installed"] = True
        result["error"] = redact_text(str(exc))

    return result
