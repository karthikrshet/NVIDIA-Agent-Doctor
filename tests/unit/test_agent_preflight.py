"""Tests for safe agent workflow static preflight."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from nvidia_agent_doctor.agent_test import run_agent_preflight
from nvidia_agent_doctor.core.models import MCPServerInfo


def test_preflight_never_executes_configured_mcp_command(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skills.mkdir()
    server = MCPServerInfo(name="server", command="missing-server")

    with patch("nvidia_agent_doctor.agent_test.discover_mcp_servers", return_value=[server]):
        with patch("nvidia_agent_doctor.agent_test.shutil.which", return_value=None) as which:
            result = run_agent_preflight(skills, [], 3)

    which.assert_called_once_with("missing-server")
    assert result["executed"] is False
    assert result["exit_code"] == 1
    assert result["checks"][-1]["status"] == "WARNING"


def test_preflight_reports_missing_skills_as_error(tmp_path: Path) -> None:
    with patch("nvidia_agent_doctor.agent_test.discover_mcp_servers", return_value=[]):
        result = run_agent_preflight(tmp_path / "missing", [], 3)

    assert result["exit_code"] == 2
    assert result["checks"][0]["status"] == "ERROR"
