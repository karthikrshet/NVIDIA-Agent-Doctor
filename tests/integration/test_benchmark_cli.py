"""Regression tests for benchmark command exit behavior."""

from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from nvidia_agent_doctor.cli.main import app

runner = CliRunner()


def test_benchmark_json_returns_error_exit_code_for_measurement_failure() -> None:
    """A benchmark error must not be silently reported as success."""
    with patch(
        "nvidia_agent_doctor.benchmark.runner.run_benchmarks",
        return_value={"gpu_basic": {"error": "CUDA operation failed"}},
    ):
        result = runner.invoke(app, ["benchmark", "run", "--yes", "--json"])

    assert result.exit_code == 2
    assert json.loads(result.stdout) == {"gpu_basic": {"error": "CUDA operation failed"}}


def test_benchmark_skip_remains_successful() -> None:
    """An optional unavailable accelerator is a skip, not an execution failure."""
    with patch(
        "nvidia_agent_doctor.benchmark.runner.run_benchmarks",
        return_value={"gpu_basic": {"skipped": True, "reason": "CUDA not available"}},
    ):
        result = runner.invoke(app, ["benchmark", "run", "--yes", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["gpu_basic"]["skipped"] is True
