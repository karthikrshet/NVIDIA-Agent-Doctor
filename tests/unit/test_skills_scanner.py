"""Tests for agent skills scanner."""

from __future__ import annotations

from pathlib import Path

import pytest
from nvidia_agent_doctor.skills.parser import parse_skill_file
from nvidia_agent_doctor.skills.scanner import scan_skill, scan_skills_directory
from nvidia_agent_doctor.core.severity import SecuritySeverity


class TestSkillParser:
    def test_parse_good_skill(self, tmp_path: Path, sample_skill_good: str) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(sample_skill_good)
        skill = parse_skill_file(skill_file)
        assert skill is not None
        assert skill.name == "my-safe-skill"
        assert skill.version == "1.0"
        assert skill.author == "Test Author"

    def test_parse_dangerous_skill(self, tmp_path: Path, sample_skill_dangerous: str) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(sample_skill_dangerous)
        skill = parse_skill_file(skill_file)
        assert skill is not None
        # Should detect shell commands
        assert len(skill.shell_commands) > 0
        # Should detect credential references
        assert len(skill.credential_references) > 0

    def test_parse_nonexistent_returns_none(self, tmp_path: Path) -> None:
        result = parse_skill_file(tmp_path / "does_not_exist.md")
        assert result is None

    def test_skill_name_falls_back_to_filename(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("# No frontmatter\nJust instructions.")
        skill = parse_skill_file(skill_file)
        assert skill is not None
        assert skill.name == "SKILL"


class TestSkillScanner:
    def test_dangerous_skill_gets_high_risk(self, tmp_path: Path, sample_skill_dangerous: str) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(sample_skill_dangerous)
        skill = parse_skill_file(skill_file)
        assert skill is not None
        result = scan_skill(skill)
        assert result.risk_level in (SecuritySeverity.HIGH, SecuritySeverity.MEDIUM)

    def test_safe_skill_gets_info_risk(self, tmp_path: Path, sample_skill_good: str) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(sample_skill_good)
        skill = parse_skill_file(skill_file)
        assert skill is not None
        result = scan_skill(skill)
        # Safe skill should have INFO or LOW level
        assert result.risk_level.score <= SecuritySeverity.MEDIUM.score

    def test_scan_directory_finds_skills(self, tmp_path: Path, sample_skill_good: str) -> None:
        skill_dir = tmp_path / "skills" / "skill-a"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(sample_skill_good)

        results = scan_skills_directory(tmp_path)
        assert len(results) == 1
        assert results[0].skill.name == "my-safe-skill"

    def test_scan_empty_directory(self, tmp_path: Path) -> None:
        results = scan_skills_directory(tmp_path)
        assert results == []
