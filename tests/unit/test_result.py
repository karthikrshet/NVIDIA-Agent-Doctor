"""Tests for DiagnosticReport and related result models."""

from __future__ import annotations

import pytest
from nvidia_agent_doctor.core.result import CheckResult, DiagnosticReport, SectionResult
from nvidia_agent_doctor.core.severity import Severity, SecuritySeverity


def make_section(name: str, severities: list[Severity]) -> SectionResult:
    section = SectionResult(name=name, display_name=name)
    for i, sev in enumerate(severities):
        section.checks.append(CheckResult(
            name=f"check_{i}",
            severity=sev,
            message=f"Check {i}",
        ))
    return section


class TestSectionResult:
    def test_overall_severity_all_pass(self) -> None:
        section = make_section("test", [Severity.PASS, Severity.PASS])
        assert section.overall_severity == Severity.PASS

    def test_overall_severity_error_wins(self) -> None:
        section = make_section("test", [Severity.PASS, Severity.ERROR, Severity.WARNING])
        assert section.overall_severity == Severity.ERROR

    def test_score_100_all_pass(self) -> None:
        section = make_section("test", [Severity.PASS, Severity.PASS])
        assert section.score == 100

    def test_score_none_if_all_not_installed(self) -> None:
        section = make_section("test", [Severity.NOT_INSTALLED, Severity.NOT_APPLICABLE])
        assert section.score is None

    def test_warnings_filter(self) -> None:
        section = make_section("test", [Severity.WARNING, Severity.PASS, Severity.WARNING])
        assert len(section.warnings) == 2

    def test_errors_filter(self) -> None:
        section = make_section("test", [Severity.ERROR, Severity.PASS])
        assert len(section.errors) == 1

    def test_recommendations_collected(self) -> None:
        section = SectionResult(name="test", display_name="Test")
        section.checks.append(CheckResult(
            name="c1", severity=Severity.WARNING,
            message="msg", recommendation="Do X"
        ))
        assert "Do X" in section.recommendations


class TestDiagnosticReport:
    def test_overall_score_default(self) -> None:
        report = DiagnosticReport()
        assert report.overall_score == 100

    def test_overall_score_with_sections(self) -> None:
        report = DiagnosticReport()
        report.add_section(make_section("gpu", [Severity.PASS]))
        report.add_section(make_section("cuda", [Severity.PASS]))
        assert report.overall_score == 100

    def test_exit_code_healthy(self) -> None:
        report = DiagnosticReport()
        report.add_section(make_section("gpu", [Severity.PASS]))
        assert report.exit_code == 0

    def test_exit_code_warnings(self) -> None:
        report = DiagnosticReport()
        report.add_section(make_section("gpu", [Severity.WARNING]))
        assert report.exit_code == 1

    def test_exit_code_errors(self) -> None:
        report = DiagnosticReport()
        report.add_section(make_section("gpu", [Severity.ERROR]))
        assert report.exit_code == 2

    def test_total_warnings(self) -> None:
        report = DiagnosticReport()
        report.add_section(make_section("gpu", [Severity.WARNING, Severity.WARNING]))
        report.add_section(make_section("cuda", [Severity.WARNING]))
        assert report.total_warnings == 3

    def test_json_serialization(self) -> None:
        import json
        report = DiagnosticReport()
        report.add_section(make_section("test", [Severity.PASS]))
        data = json.dumps(report.to_json_dict(), default=str)
        parsed = json.loads(data)
        assert "tool" in parsed
        assert "sections" in parsed
        assert parsed["tool"]["name"] == "nvidia-agent-doctor"

    def test_all_recommendations_deduped(self) -> None:
        report = DiagnosticReport()
        section = SectionResult(name="test", display_name="Test")
        section.checks.append(CheckResult(
            name="c1", severity=Severity.WARNING,
            message="m1", recommendation="Do X"
        ))
        section.checks.append(CheckResult(
            name="c2", severity=Severity.WARNING,
            message="m2", recommendation="Do X"  # duplicate
        ))
        report.add_section(section)
        recs = report.all_recommendations
        assert recs.count("Do X") == 1
