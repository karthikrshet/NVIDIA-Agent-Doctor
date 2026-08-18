"""Safe, review-first remediation planning."""

from __future__ import annotations

import platform
from typing import Any, cast

from nvidia_agent_doctor.core.result import DiagnosticReport
from nvidia_agent_doctor.core.severity import Severity
from nvidia_agent_doctor.security.credentials import redact_data


def build_remediation_plan(report: DiagnosticReport) -> list[dict[str, Any]]:
    """Build non-executing remediation steps from actionable findings.

    Package, driver, and CUDA changes can alter a developer workstation. This
    function therefore never emits an executable side effect; callers must
    explicitly review and perform the suggested action themselves.
    """
    steps: list[dict[str, Any]] = []
    for section in report.sections.values():
        for check in section.checks:
            if check.severity not in (Severity.WARNING, Severity.ERROR):
                continue
            if not check.recommendation and not check.fix_command:
                continue
            step: dict[str, Any] = {
                "component": section.name,
                "check": check.name,
                "status": "manual-review-required",
                "reason": check.message,
                "recommendation": check.recommendation,
            }
            if check.name == "cuda_env_vars":
                step["suggested_action"] = _cuda_environment_guidance()
            elif check.fix_command:
                step["suggested_action"] = "Review the following command before using it manually."
                step["command"] = check.fix_command
            steps.append(step)
    return cast(list[dict[str, Any]], redact_data(steps))


def _cuda_environment_guidance() -> str:
    system = platform.system()
    if system == "Windows":
        return "Set CUDA_PATH in System Properties after confirming the installed toolkit directory."
    if system == "Darwin":
        return "Set CUDA_HOME in your shell profile only after confirming the installed toolkit directory."
    return "Set CUDA_HOME in your shell profile only after confirming the installed toolkit directory."
