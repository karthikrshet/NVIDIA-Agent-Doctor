"""NVIDIA Agent Doctor — Core result data models."""

from __future__ import annotations

import datetime
from typing import Any, cast

from pydantic import BaseModel, Field

from nvidia_agent_doctor.core.severity import SecuritySeverity, Severity


class CheckResult(BaseModel):
    """Result of a single diagnostic check."""

    name: str
    severity: Severity
    message: str
    detail: str | None = None
    recommendation: str | None = None
    fix_command: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        return self.recommendation is not None or self.fix_command is not None


class SecurityFinding(BaseModel):
    """A single security finding."""

    title: str
    severity: SecuritySeverity
    description: str
    recommendation: str
    component: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SectionResult(BaseModel):
    """Aggregated results for a diagnostic section (e.g. GPU, CUDA)."""

    name: str
    display_name: str
    checks: list[CheckResult] = Field(default_factory=list)
    security_findings: list[SecurityFinding] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def overall_severity(self) -> Severity:
        """Worst severity across all checks."""
        if not self.checks:
            return Severity.UNKNOWN
        priority = [
            Severity.ERROR,
            Severity.WARNING,
            Severity.UNKNOWN,
            Severity.PASS,
            Severity.NOT_APPLICABLE,
            Severity.NOT_INSTALLED,
        ]
        for sev in priority:
            if any(c.severity == sev for c in self.checks):
                return sev
        return Severity.UNKNOWN

    @property
    def score(self) -> int | None:
        """0-100 health score. Returns None if no scoreable checks."""
        scoreable = [c for c in self.checks if c.severity.affects_score]
        if not scoreable:
            return None
        total_penalty = sum(c.severity.score_penalty for c in scoreable)
        max_penalty = len(scoreable) * Severity.ERROR.score_penalty
        if max_penalty == 0:
            return 100
        return max(0, round(100 - (total_penalty / max_penalty) * 100))

    @property
    def warnings(self) -> list[CheckResult]:
        return [c for c in self.checks if c.severity == Severity.WARNING]

    @property
    def errors(self) -> list[CheckResult]:
        return [c for c in self.checks if c.severity == Severity.ERROR]

    @property
    def recommendations(self) -> list[str]:
        return [c.recommendation for c in self.checks if c.recommendation]


class ToolInfo(BaseModel):
    """Metadata about the nad tool itself."""

    name: str = "nvidia-agent-doctor"
    version: str = "0.1.0"
    disclaimer: str = (
        "NVIDIA Agent Doctor is an independent open-source project and is not affiliated "
        "with or endorsed by NVIDIA Corporation."
    )
    privacy: str = "No telemetry. No cloud upload. All diagnostics are local-only."


class DiagnosticReport(BaseModel):
    """Top-level diagnostic report containing all sections."""

    tool: ToolInfo = Field(default_factory=ToolInfo)
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    sections: dict[str, SectionResult] = Field(default_factory=dict)
    security_findings: list[SecurityFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    @property
    def overall_score(self) -> int:
        """Weighted average of all section scores (excluding None scores)."""
        scores = [s.score for s in self.sections.values() if s.score is not None]
        if not scores:
            return 100
        return round(sum(scores) / len(scores))

    @property
    def total_warnings(self) -> int:
        return sum(len(s.warnings) for s in self.sections.values())

    @property
    def total_errors(self) -> int:
        return sum(len(s.errors) for s in self.sections.values())

    @property
    def total_security_findings(self) -> int:
        return len(self.security_findings) + sum(
            len(s.security_findings) for s in self.sections.values()
        )

    @property
    def all_recommendations(self) -> list[str]:
        recs = list(self.recommendations)
        for section in self.sections.values():
            recs.extend(section.recommendations)
        return list(dict.fromkeys(recs))  # deduplicate, preserve order

    @property
    def exit_code(self) -> int:
        """CLI exit code based on overall health.

        0 = healthy
        1 = warnings
        2 = errors
        3 = security issues
        4 = invalid configuration (set externally)
        """
        if self.total_errors > 0:
            return 2
        high_security = [
            f
            for f in self.security_findings
            if f.severity in (SecuritySeverity.HIGH, SecuritySeverity.CRITICAL)
        ]
        if high_security:
            return 3
        if self.total_warnings > 0:
            return 1
        return 0

    def add_section(self, section: SectionResult) -> None:
        self.sections[section.name] = section

    def to_json_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict with secrets redacted."""
        from nvidia_agent_doctor.security.credentials import redact_data

        return cast(dict[str, Any], redact_data(self.model_dump(mode="json")))

    def redacted_copy(self) -> DiagnosticReport:
        """Return a safe copy suitable for any output format."""
        return self.model_validate(self.to_json_dict())
