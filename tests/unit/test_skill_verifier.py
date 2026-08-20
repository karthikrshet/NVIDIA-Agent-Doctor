"""Tests for local skill integrity and manifest verification."""

from __future__ import annotations

import hashlib
from base64 import b64encode
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

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


def test_missing_skill_path_returns_a_safe_invalid_result(tmp_path: Path) -> None:
    result = verify_skill(tmp_path / "missing-skill.md")

    assert result["verified"] is False
    assert result["integrity"]["status"] == "invalid"
    assert result["integrity"]["reason"] == "Skill must be a regular file under 8 MiB."


def test_verifies_ed25519_signature_and_valid_skillcard(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text("# Signed skill\n", encoding="utf-8")
    private_key = Ed25519PrivateKey.generate()
    (tmp_path / "skill.sig").write_bytes(private_key.sign(skill.read_bytes()))
    (tmp_path / "signer.pem").write_bytes(
        private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )
    (tmp_path / "SKILLCARD.yaml").write_text(
        "name: signed\npermissions: []\ndependencies: []\nrisks: []\n", encoding="utf-8"
    )

    result = verify_skill(skill, tmp_path / "skill.sig", tmp_path / "signer.pem")

    assert result["verified"] is True
    assert result["integrity"]["method"] == "ed25519-detached-signature"
    assert result["integrity"]["status"] == "verified"


def test_rejects_invalid_ed25519_signature_without_leaking_data(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text("# Signed skill\n", encoding="utf-8")
    private_key = Ed25519PrivateKey.generate()
    (tmp_path / "skill.sig").write_bytes(b64encode(b"not-an-ed25519-signature"))
    (tmp_path / "signer.pem").write_bytes(
        private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )

    result = verify_skill(skill, tmp_path / "skill.sig", tmp_path / "signer.pem")

    assert result["verified"] is False
    assert result["integrity"]["status"] == "invalid"
    assert "# Signed skill" not in str(result)


def test_verifies_base64_ed25519_signature(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text("# Base64 signed skill\n", encoding="utf-8")
    private_key = Ed25519PrivateKey.generate()
    (tmp_path / "skill.sig").write_bytes(b64encode(private_key.sign(skill.read_bytes())))
    (tmp_path / "signer.pem").write_bytes(
        private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )
    (tmp_path / "SKILLCARD.yaml").write_text(
        "name: signed\npermissions: []\ndependencies: []\nrisks: []\n", encoding="utf-8"
    )

    result = verify_skill(skill, tmp_path / "skill.sig", tmp_path / "signer.pem")

    assert result["verified"] is True
    assert result["integrity"]["status"] == "verified"


def test_ed25519_signature_from_another_key_is_not_verified(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text("# Signed skill\n", encoding="utf-8")
    signing_key = Ed25519PrivateKey.generate()
    unrelated_key = Ed25519PrivateKey.generate()
    (tmp_path / "skill.sig").write_bytes(signing_key.sign(skill.read_bytes()))
    (tmp_path / "signer.pem").write_bytes(
        unrelated_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )

    result = verify_skill(skill, tmp_path / "skill.sig", tmp_path / "signer.pem")

    assert result["verified"] is False
    assert result["integrity"]["status"] == "mismatch"
