"""Tests for core severity models."""

from __future__ import annotations

import pytest
from nvidia_agent_doctor.core.severity import Severity, SecuritySeverity


class TestSeverity:
    def test_pass_is_healthy(self) -> None:
        assert Severity.PASS.is_healthy is True

    def test_warning_is_not_healthy(self) -> None:
        assert Severity.WARNING.is_healthy is False

    def test_error_is_problem(self) -> None:
        assert Severity.ERROR.is_problem is True

    def test_not_installed_does_not_affect_score(self) -> None:
        assert Severity.NOT_INSTALLED.affects_score is False

    def test_not_applicable_does_not_affect_score(self) -> None:
        assert Severity.NOT_APPLICABLE.affects_score is False

    def test_pass_has_zero_penalty(self) -> None:
        assert Severity.PASS.score_penalty == 0

    def test_error_has_highest_penalty(self) -> None:
        assert Severity.ERROR.score_penalty > Severity.WARNING.score_penalty

    def test_icons_not_empty(self) -> None:
        for sev in Severity:
            assert len(sev.icon) > 0

    def test_colors_valid_strings(self) -> None:
        for sev in Severity:
            assert isinstance(sev.color, str)

    def test_string_value(self) -> None:
        assert Severity.PASS.value == "PASS"
        assert Severity.WARNING.value == "WARNING"


class TestSecuritySeverity:
    def test_critical_has_highest_score(self) -> None:
        assert SecuritySeverity.CRITICAL.score > SecuritySeverity.HIGH.score

    def test_info_has_lowest_score(self) -> None:
        scores = [s.score for s in SecuritySeverity]
        assert SecuritySeverity.INFO.score == min(scores)

    def test_colors_defined(self) -> None:
        for sev in SecuritySeverity:
            assert isinstance(sev.color, str)
