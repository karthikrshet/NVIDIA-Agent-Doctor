"""Local integrity and manifest checks for untrusted agent skills."""

from __future__ import annotations

import hashlib
import re
from base64 import b64decode
from binascii import Error as BinasciiError
from pathlib import Path
from typing import Any

_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
_MAX_FILE_BYTES = 8 * 1_048_576
_MAX_SIGNATURE_BYTES = 256
_MAX_PUBLIC_KEY_BYTES = 16 * 1_024


def verify_skill(
    skill_path: Path,
    signature_path: Path | None = None,
    public_key_path: Path | None = None,
) -> dict[str, Any]:
    """Verify local integrity material and a nearby SKILLCARD.yaml manifest.

    A plain digest provides integrity checking, not publisher authentication.
    Ed25519 verification establishes that the supplied key signed the content;
    it does not establish key ownership or implement OpenSSF Model Signing.
    """
    result: dict[str, Any] = {
        "skill": str(skill_path),
        "integrity": {"status": "missing", "method": "sha256-detached-digest"},
        "skillcard": {"status": "missing"},
        "verified": False,
    }
    if not _is_regular_bounded_file(skill_path, _MAX_FILE_BYTES):
        result["integrity"] = {
            "status": "invalid",
            "reason": "Skill must be a regular file under 8 MiB.",
        }
        return result

    signature = signature_path or skill_path.with_name("skill.sig")
    if public_key_path is None:
        result["integrity"] = _verify_sha256_digest(skill_path, signature)
    else:
        result["integrity"] = _verify_ed25519_signature(skill_path, signature, public_key_path)

    skillcard = skill_path.with_name("SKILLCARD.yaml")
    result["skillcard"] = _validate_skillcard(skillcard)
    result["verified"] = (
        result["integrity"].get("status") == "verified"
        and result["skillcard"].get("status") == "valid"
    )
    return result


def _is_regular_bounded_file(path: Path, max_bytes: int) -> bool:
    """Return whether untrusted input is a small, non-symlink regular file."""
    try:
        return not path.is_symlink() and path.is_file() and path.stat().st_size <= max_bytes
    except OSError:
        return False


def _verify_sha256_digest(skill_path: Path, signature_path: Path) -> dict[str, str]:
    if not _is_regular_bounded_file(signature_path, _MAX_SIGNATURE_BYTES):
        return {"status": "missing", "method": "sha256-detached-digest"}
    try:
        digests = signature_path.read_text(encoding="ascii", errors="strict").strip().split()
        if len(digests) != 1:
            raise ValueError("Expected exactly one digest.")
        expected = digests[0]
    except (OSError, UnicodeDecodeError, ValueError):
        return {"status": "invalid", "reason": "skill.sig must contain one SHA-256 digest."}
    if not _SHA256.fullmatch(expected):
        return {"status": "invalid", "reason": "skill.sig must contain one SHA-256 digest."}
    try:
        actual = hashlib.sha256(skill_path.read_bytes()).hexdigest()
    except OSError:
        return {"status": "invalid", "reason": "Skill could not be read safely."}
    return {
        "status": "verified" if actual.lower() == expected.lower() else "mismatch",
        "method": "sha256-detached-digest",
    }


def _verify_ed25519_signature(
    skill_path: Path, signature_path: Path, public_key_path: Path
) -> dict[str, str]:
    """Verify a raw or base64 detached Ed25519 signature without key discovery."""
    method = "ed25519-detached-signature"
    if not _is_regular_bounded_file(signature_path, _MAX_SIGNATURE_BYTES):
        return {"status": "missing", "method": method, "reason": "Detached signature not found."}
    if not _is_regular_bounded_file(public_key_path, _MAX_PUBLIC_KEY_BYTES):
        return {
            "status": "invalid",
            "method": method,
            "reason": "Public key must be a small regular PEM file.",
        }
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        public_key = load_pem_public_key(public_key_path.read_bytes())
        if not isinstance(public_key, Ed25519PublicKey):
            return {
                "status": "invalid",
                "method": method,
                "reason": "Public key must be Ed25519 PEM.",
            }
        signature = _read_signature(signature_path)
        public_key.verify(signature, skill_path.read_bytes())
    except InvalidSignature:
        return {"status": "mismatch", "method": method}
    except (OSError, TypeError, ValueError):
        return {
            "status": "invalid",
            "method": method,
            "reason": "Invalid Ed25519 key or signature.",
        }
    return {
        "status": "verified",
        "method": method,
        "identity": "The supplied public key verified this content; key ownership is not asserted.",
    }


def _read_signature(path: Path) -> bytes:
    """Accept exactly a raw 64-byte or single base64-encoded Ed25519 signature."""
    data = path.read_bytes()
    if len(data) == 64:
        return data
    encoded = data.strip()
    try:
        decoded = b64decode(encoded, validate=True)
    except (BinasciiError, ValueError) as exc:
        raise ValueError("Signature must be raw 64-byte or base64-encoded Ed25519 data.") from exc
    if len(decoded) != 64:
        raise ValueError("Signature must decode to 64 bytes.")
    return decoded


def _validate_skillcard(path: Path) -> dict[str, Any]:
    if not _is_regular_bounded_file(path, _MAX_FILE_BYTES):
        return {"status": "missing"}
    try:
        import yaml
    except ImportError:
        return {"status": "invalid", "reason": "PyYAML is required to validate SKILLCARD.yaml."}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError):
        return {"status": "invalid", "reason": "SKILLCARD.yaml could not be safely parsed."}
    if not isinstance(data, dict):
        return {"status": "invalid", "reason": "Manifest must be a mapping."}
    required_lists = ("permissions", "dependencies", "risks")
    missing = [key for key in ("name", *required_lists) if key not in data]
    wrong_type = [key for key in required_lists if key in data and not isinstance(data[key], list)]
    if missing or wrong_type or not isinstance(data.get("name"), str):
        return {
            "status": "invalid",
            "reason": "Required fields: name (string), permissions/dependencies/risks (lists).",
        }
    return {"status": "valid", "declared_permissions": len(data["permissions"])}
