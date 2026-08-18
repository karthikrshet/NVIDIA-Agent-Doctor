"""Local integrity and manifest checks for untrusted agent skills."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
_MAX_FILE_BYTES = 8 * 1_048_576


def verify_skill(skill_path: Path, signature_path: Path | None = None) -> dict[str, Any]:
    """Verify a detached SHA-256 digest and a nearby SKILLCARD.yaml manifest.

    A plain digest provides integrity checking, not publisher authentication.
    Public-key signing formats (including OMS) are deliberately not inferred
    or treated as verified without their issuer metadata and verifier.
    """
    result: dict[str, Any] = {
        "skill": str(skill_path),
        "integrity": {"status": "missing", "method": "sha256-detached-digest"},
        "skillcard": {"status": "missing"},
        "verified": False,
    }
    if (
        skill_path.is_symlink()
        or not skill_path.is_file()
        or skill_path.stat().st_size > _MAX_FILE_BYTES
    ):
        result["integrity"] = {
            "status": "invalid",
            "reason": "Skill must be a regular file under 8 MiB.",
        }
        return result

    signature = signature_path or skill_path.with_name("skill.sig")
    if signature.is_symlink() or not signature.is_file() or signature.stat().st_size > 256:
        result["integrity"] = {"status": "missing", "method": "sha256-detached-digest"}
    else:
        expected = signature.read_text(encoding="ascii", errors="ignore").strip().split()[0]
        if not _SHA256.fullmatch(expected):
            result["integrity"] = {
                "status": "invalid",
                "reason": "skill.sig must contain one SHA-256 digest.",
            }
        else:
            actual = hashlib.sha256(skill_path.read_bytes()).hexdigest()
            result["integrity"] = {
                "status": "verified" if actual.lower() == expected.lower() else "mismatch",
                "method": "sha256-detached-digest",
            }

    skillcard = skill_path.with_name("SKILLCARD.yaml")
    result["skillcard"] = _validate_skillcard(skillcard)
    result["verified"] = (
        result["integrity"].get("status") == "verified"
        and result["skillcard"].get("status") == "valid"
    )
    return result


def _validate_skillcard(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_FILE_BYTES:
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
