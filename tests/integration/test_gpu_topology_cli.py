"""Integration tests for the privacy-preserving GPU topology command."""

from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from nvidia_agent_doctor.cli.main import app


def test_gpu_topology_json_renders_only_structured_topology() -> None:
    topology = {
        "status": "available",
        "reason": None,
        "gpu_count": 2,
        "gpu_labels": ["GPU0", "GPU1"],
        "links": [{"from": "GPU0", "to": "GPU1", "link": "NV2"}],
    }
    with patch("nvidia_agent_doctor.collectors.gpu.collect_gpu_topology", return_value=topology):
        result = CliRunner().invoke(app, ["gpu", "topology", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == topology
