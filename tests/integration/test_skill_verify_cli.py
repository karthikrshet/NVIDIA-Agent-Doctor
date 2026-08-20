"""End-to-end tests for local skill provenance verification."""

from __future__ import annotations

import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from typer.testing import CliRunner

from nvidia_agent_doctor.cli.main import app

runner = CliRunner()


def test_skills_verify_ed25519_signature_returns_verified_json(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text("# Signed skill\n", encoding="utf-8")
    private_key = Ed25519PrivateKey.generate()
    signature = tmp_path / "skill.sig"
    signature.write_bytes(private_key.sign(skill.read_bytes()))
    public_key = tmp_path / "signer.pem"
    public_key.write_bytes(
        private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )
    (tmp_path / "SKILLCARD.yaml").write_text(
        "name: signed\npermissions: []\ndependencies: []\nrisks: []\n", encoding="utf-8"
    )

    result = runner.invoke(
        app,
        [
            "skills",
            "verify",
            str(skill),
            "--signature",
            str(signature),
            "--public-key",
            str(public_key),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["verified"] is True
    assert payload["integrity"] == {
        "status": "verified",
        "method": "ed25519-detached-signature",
        "identity": "The supplied public key verified this content; key ownership is not asserted.",
    }


def test_skills_verify_json_redacts_secret_like_path_segments(tmp_path: Path) -> None:
    secret = "super-secret-value"
    skill = tmp_path / f"API_KEY={secret}-skill.md"
    skill.write_text("# Unsigned skill\n", encoding="utf-8")

    result = runner.invoke(app, ["skills", "verify", str(skill), "--json"])

    assert result.exit_code == 3
    assert secret not in result.output
    assert "API_KEY=********" in result.output
