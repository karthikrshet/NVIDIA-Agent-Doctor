"""Tests for the guided interactive console."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from nvidia_agent_doctor.cli.main import app

runner = CliRunner()


def test_interactive_requires_terminal() -> None:
    with patch("nvidia_agent_doctor.cli.interactive.sys.stdin.isatty", return_value=False):
        result = runner.invoke(app, ["interactive"])

    assert result.exit_code == 4
    assert "requires an attached terminal" in result.output
