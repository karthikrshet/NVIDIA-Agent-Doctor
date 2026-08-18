"""Tests for local skill integrity and manifest verification."""

from __future__ import annotations

import hashlib
from pathlib import Path

from nvidia_agent_doctor.skills.verifier import verify_skill


def test_verifies_matching_digest_and_valid_skillcard(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    content = "# Test skill\n"
    skill.write_text(content, encoding="utf-8")
    (tmp_path / "skill.sig").write_text(
        hashlib.sha256(skill.read_bytes()).hexdigest(), encoding="ascii"
    )
    (tmp_path / "SKILLCARD.yaml").write_text(
        "name: test\npermissions: []\ndependencies: []\nrisks: []\n", encoding="utf-8"
    )

    result = verify_skill(skill)

    assert result["verified"] is True
    assert result["integrity"]["status"] == "verified"
    assert result["skillcard"]["status"] == "valid"


def test_digest_mismatch_is_not_verified(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text("# Test skill\n", encoding="utf-8")
    (tmp_path / "skill.sig").write_text("0" * 64, encoding="ascii")

    result = verify_skill(skill)

    assert result["verified"] is False
    assert result["integrity"]["status"] == "mismatch"
