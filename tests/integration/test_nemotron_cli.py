"""CLI contract tests for Nemotron detection."""

from __future__ import annotations

from typer.testing import CliRunner

from nvidia_agent_doctor.cli.main import app


def test_nemotron_help_does_not_advertise_unimplemented_benchmark() -> None:
    result = CliRunner().invoke(app, ["nemotron", "--help"])

    assert result.exit_code == 0
    assert "benchmark" not in result.output.lower()
    assert "check" in result.output.lower()
