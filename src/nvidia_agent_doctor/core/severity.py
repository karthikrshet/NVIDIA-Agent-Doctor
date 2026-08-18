"""NVIDIA Agent Doctor — Core severity definitions."""

from __future__ import annotations

from enum import StrEnum


class Severity(StrEnum):
    """Diagnostic severity levels for check results."""

    PASS = "PASS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    NOT_INSTALLED = "NOT_INSTALLED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"

    @property
    def is_healthy(self) -> bool:
        """Returns True for statuses that don't indicate problems."""
        return self in (Severity.PASS, Severity.NOT_APPLICABLE)

    @property
    def is_problem(self) -> bool:
        """Returns True for statuses that indicate actionable problems."""
        return self in (Severity.WARNING, Severity.ERROR)

    @property
    def affects_score(self) -> bool:
        """Returns True if this status should affect the overall health score."""
        return self not in (Severity.NOT_INSTALLED, Severity.NOT_APPLICABLE, Severity.UNKNOWN)

    @property
    def score_penalty(self) -> int:
        """Returns the health score penalty for this severity level."""
        penalties = {
            Severity.PASS: 0,
            Severity.WARNING: 5,
            Severity.ERROR: 20,
            Severity.NOT_INSTALLED: 0,
            Severity.NOT_APPLICABLE: 0,
            Severity.UNKNOWN: 2,
        }
        return penalties[self]

    @property
    def icon(self) -> str:
        """Returns a terminal icon for this severity level."""
        icons = {
            Severity.PASS: "OK",
            Severity.WARNING: "WARN",
            Severity.ERROR: "ERROR",
            Severity.NOT_INSTALLED: "-",
            Severity.NOT_APPLICABLE: "N/A",
            Severity.UNKNOWN: "?",
        }
        return icons[self]

    @property
    def color(self) -> str:
        """Returns a Rich color name for this severity level."""
        colors = {
            Severity.PASS: "green",
            Severity.WARNING: "yellow",
            Severity.ERROR: "red",
            Severity.NOT_INSTALLED: "dim",
            Severity.NOT_APPLICABLE: "dim",
            Severity.UNKNOWN: "blue",
        }
        return colors[self]


class SecuritySeverity(StrEnum):
    """Security finding severity levels."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def color(self) -> str:
        colors = {
            SecuritySeverity.INFO: "cyan",
            SecuritySeverity.LOW: "blue",
            SecuritySeverity.MEDIUM: "yellow",
            SecuritySeverity.HIGH: "red",
            SecuritySeverity.CRITICAL: "bright_red",
        }
        return colors[self]

    @property
    def score(self) -> int:
        """Numeric risk score for aggregation."""
        scores = {
            SecuritySeverity.INFO: 1,
            SecuritySeverity.LOW: 3,
            SecuritySeverity.MEDIUM: 5,
            SecuritySeverity.HIGH: 8,
            SecuritySeverity.CRITICAL: 10,
        }
        return scores[self]
