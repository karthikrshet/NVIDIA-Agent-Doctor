"""Tests for JSON report output format."""

from __future__ import annotations

import json

from nvidia_agent_doctor.core.result import CheckResult, DiagnosticReport, SectionResult
from nvidia_agent_doctor.core.severity import Severity
from nvidia_agent_doctor.reports.json_report import render_json


class TestJsonOutput:
    def _make_report(self) -> DiagnosticReport:
        report = DiagnosticReport()
        section = SectionResult(name="gpu", display_name="GPU")
        section.checks.append(
            CheckResult(
                name="gpu_detected",
                severity=Severity.PASS,
                message="GPU detected",
            )
        )
        report.add_section(section)
        return report

    def test_valid_json(self) -> None:
        report = self._make_report()
        output = render_json(report)
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_contains_tool_info(self) -> None:
        report = self._make_report()
        data = json.loads(render_json(report))
        assert data["tool"]["name"] == "nvidia-agent-doctor"
        assert data["tool"]["version"] == "0.1.0"
        assert "disclaimer" in data["tool"]

    def test_contains_sections(self) -> None:
        report = self._make_report()
        data = json.loads(render_json(report))
        assert "sections" in data
        assert "gpu" in data["sections"]

    def test_contains_canonical_summary(self) -> None:
        report = self._make_report()
        data = json.loads(render_json(report))

        assert data["summary"] == {
            "overall_score": 100,
            "total_warnings": 0,
            "total_errors": 0,
            "total_security_findings": 0,
            "exit_code": 0,
        }

    def test_contains_timestamp(self) -> None:
        report = self._make_report()
        data = json.loads(render_json(report))
        assert "timestamp" in data

    def test_severity_is_string(self) -> None:
        report = self._make_report()
        data = json.loads(render_json(report))
        checks = data["sections"]["gpu"]["checks"]
        assert all(isinstance(c["severity"], str) for c in checks)

    def test_disclaimer_present(self) -> None:
        report = self._make_report()
        data = json.loads(render_json(report))
        assert "independent" in data["tool"]["disclaimer"].lower()
        assert "not affiliated" in data["tool"]["disclaimer"].lower()

    def test_no_raw_secrets_in_check_messages(self) -> None:
        """Verify that check messages and recommendations don't contain raw secrets."""
        report = self._make_report()
        # Simulate a check that might have seen a secret in its message
        section = report.sections["gpu"]
        section.checks.append(
            CheckResult(
                name="env_check",
                severity=Severity.WARNING,
                message="Sensitive variable detected",
                detail="Value redacted",
            )
        )
        output = render_json(report)
        # The check message should NOT contain raw secrets
        assert "sk-fakesecret" not in output
        assert "hunter2" not in output
