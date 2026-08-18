"""Security and cleanup tests for the optional PyTorch integration."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from nvidia_agent_doctor.integrations.pytorch import check_pytorch


def test_pytorch_compute_failure_is_redacted_and_releases_cuda_cache() -> None:
    cuda = SimpleNamespace(
        is_available=Mock(return_value=True),
        device_count=Mock(return_value=1),
        get_device_name=Mock(return_value="RTX test"),
        get_device_properties=Mock(return_value=SimpleNamespace(major=8, minor=6)),
        empty_cache=Mock(),
    )
    torch = SimpleNamespace(
        __version__="test",
        version=SimpleNamespace(cuda="11.8"),
        cuda=cuda,
        tensor=Mock(side_effect=RuntimeError("TOKEN=top-secret")),
    )

    with patch.dict(sys.modules, {"torch": torch}):
        result = check_pytorch()

    assert result["basic_compute_pass"] is False
    assert result["compute_error"] == "TOKEN=********"
    cuda.empty_cache.assert_called_once()
