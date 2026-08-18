"""NVIDIA Agent Doctor — TensorRT integration."""

from __future__ import annotations

from typing import Any


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
        "error": None,
    }

    try:
        import tensorrt as trt  # type: ignore[import]
        result["installed"] = True
        result["python_bindings"] = True
        result["version"] = getattr(trt, "__version__", None)

        # Check builder
        try:
            logger = trt.Logger(trt.Logger.WARNING)
            builder = trt.Builder(logger)
            result["builder_available"] = builder is not None
            del builder
        except Exception as e:
            result["builder_available"] = False
            result["builder_error"] = str(e)

        # Check runtime
        try:
            logger = trt.Logger(trt.Logger.WARNING)
            runtime = trt.Runtime(logger)
            result["runtime_available"] = runtime is not None
            del runtime
        except Exception as e:
            result["runtime_available"] = False
            result["runtime_error"] = str(e)

        # CUDA compatibility check via torch if available
        try:
            import torch
            if torch.cuda.is_available():
                result["cuda_compatible"] = True
        except ImportError:
            result["cuda_compatible"] = None

    except ImportError:
        pass
    except Exception as e:
        result["installed"] = True
        result["error"] = str(e)

    return result
