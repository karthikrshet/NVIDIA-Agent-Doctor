"""Regression tests for documented CLI status-code behaviour."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from nvidia_agent_doctor.cli.main import app
from nvidia_agent_doctor.core.models import MCPServerInfo
from nvidia_agent_doctor.core.result import (
    CheckResult,
    DiagnosticReport,
    SectionResult,
    SecurityFinding,
)
from nvidia_agent_doctor.core.severity import SecuritySeverity, Severity

runner = CliRunner()


def _section(name: str, severity: Severity) -> SectionResult:
    return SectionResult(
        name=name,
        display_name=name.title(),
        checks=[CheckResult(name="check", severity=severity, message="test")],
    )


def test_cuda_warning_returns_exit_code_one_with_valid_json() -> None:
    with patch(
        "nvidia_agent_doctor.analyzers.environment.analyze_cuda",
        return_value=_section("cuda", Severity.WARNING),
    ):
        result = runner.invoke(app, ["cuda", "check", "--json"])

    assert result.exit_code == 1
    assert json.loads(result.output)["summary"]["exit_code"] == 1


def test_security_high_finding_returns_exit_code_three() -> None:
    section = _section("security", Severity.PASS)
    section.security_findings.append(
        SecurityFinding(
            title="Unsafe local configuration",
            severity=SecuritySeverity.HIGH,
            description="Potential security risk requiring review.",
            recommendation="Review the configuration.",
            component="security",
        )
    )
    with patch("nvidia_agent_doctor.analyzers.security.analyze_security", return_value=section):
        result = runner.invoke(app, ["security", "scan", "--json"])

    assert result.exit_code == 3
    assert json.loads(result.output)["summary"]["exit_code"] == 3


def test_report_rejects_unknown_format_before_collecting_diagnostics() -> None:
    with patch("nvidia_agent_doctor.cli.doctor._run_doctor") as run_doctor:
        result = runner.invoke(app, ["report", "generate", "--format", "yaml"])

    assert result.exit_code == 2
    assert "unsupported report format" in result.output
    run_doctor.assert_not_called()


def test_report_output_error_is_handled_without_traceback(tmp_path: Path) -> None:
    with patch("nvidia_agent_doctor.cli.doctor._run_doctor", return_value=DiagnosticReport()):
        result = runner.invoke(
            app,
            ["report", "generate", "--format", "json", "--output", str(tmp_path)],
        )

    assert result.exit_code == 2
    assert "could not write report" in result.output
    assert "Traceback" not in result.output


def test_mcp_high_risk_arguments_are_redacted_and_return_exit_code_three() -> None:
    secret = "sk-mcpsecret0123456789abcdefghijkl"
    server = MCPServerInfo(
        name="hostile",
        command="bash",
        args=[f"--allow-write=API_KEY={secret}"],
        url=f"http://user:{secret}@example.test/service?access_token={secret}",
    )
    with patch("nvidia_agent_doctor.integrations.mcp.discover_mcp_servers", return_value=[server]):
        result = runner.invoke(app, ["mcp", "scan", "--json"])

    assert result.exit_code == 3
    assert secret not in result.output
    assert "********" in result.output

    with patch("nvidia_agent_doctor.integrations.mcp.discover_mcp_servers", return_value=[server]):
        terminal_result = runner.invoke(app, ["mcp", "scan", "--verbose"])

    assert terminal_result.exit_code == 3
    assert secret not in terminal_result.output
    assert "********" in terminal_result.output


def test_high_risk_skill_scan_returns_exit_code_three(
    tmp_path: Path, sample_skill_dangerous: str
) -> None:
    (tmp_path / "SKILL.md").write_text(sample_skill_dangerous, encoding="utf-8")

    result = runner.invoke(app, ["skills", "scan", str(tmp_path), "--json"])

    assert result.exit_code == 3
    assert json.loads(result.output)[0]["risk_level"] == "HIGH"
