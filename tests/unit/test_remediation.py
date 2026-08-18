"""Tests for review-only remediation planning."""

from __future__ import annotations

from nvidia_agent_doctor.core.remediation import build_remediation_plan
from nvidia_agent_doctor.core.result import CheckResult, DiagnosticReport, SectionResult
from nvidia_agent_doctor.core.severity import Severity


def test_remediation_plan_never_marks_steps_as_automatic() -> None:
    report = DiagnosticReport()
    report.add_section(
        SectionResult(
            name="cuda",
            display_name="CUDA",
            checks=[
                CheckResult(
                    name="cuda_env_vars",
                    severity=Severity.WARNING,
                    message="CUDA_HOME and CUDA_PATH are not set",
                    recommendation="Configure the environment.",
                )
            ],
        )
    )

    plan = build_remediation_plan(report)

    assert len(plan) == 1
    assert plan[0]["status"] == "manual-review-required"
    assert "automatically" not in str(plan).lower()
