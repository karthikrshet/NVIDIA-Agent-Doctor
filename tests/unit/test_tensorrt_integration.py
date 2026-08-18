"""Regression tests for honest and redacted TensorRT detection."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

from nvidia_agent_doctor.integrations.tensorrt import check_tensorrt


def test_tensorrt_probe_redacts_errors_without_claiming_cuda_compatibility() -> None:
    tensorrt = ModuleType("tensorrt")

    class Logger:
        WARNING = 0

        def __init__(self, _: int) -> None:
            pass

    def fail_builder(_: Logger) -> None:
        raise RuntimeError("API_KEY=super-secret")

    def fail_runtime(_: Logger) -> None:
        raise RuntimeError("TOKEN=also-secret")

    tensorrt.Logger = Logger  # type: ignore[attr-defined]
    tensorrt.Builder = fail_builder  # type: ignore[attr-defined]
    tensorrt.Runtime = fail_runtime  # type: ignore[attr-defined]
    tensorrt.__version__ = "test"  # type: ignore[attr-defined]
    torch = SimpleNamespace(cuda=SimpleNamespace(is_available=Mock(return_value=True)))

    with patch.dict(sys.modules, {"tensorrt": tensorrt, "torch": torch}):
        result = check_tensorrt()

    assert result["installed"] is True
    assert result["pytorch_cuda_available"] is True
    assert result["cuda_compatible"] is None
    assert result["builder_error"] == "API_KEY=********"
    assert result["runtime_error"] == "TOKEN=********"
