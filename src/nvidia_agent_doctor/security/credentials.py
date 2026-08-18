"""NVIDIA Agent Doctor — Security credentials detection and redaction."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

# Patterns that suggest a value is a secret
_SECRET_KEY_PATTERNS = re.compile(
    r"(api[_-]?key|apikey|secret|password|passwd|token|credential|auth|"
    r"private[_-]?key|access[_-]?key|client[_-]?secret|bearer|"
    r"ngc[_-]?api[_-]?key|openai[_-]?key|hf[_-]?token|"
    r"huggingface[_-]?token|anthropic|gemini[_-]?key)",
    re.IGNORECASE,
)

_SECRET_VALUE_PATTERNS = [
    re.compile(r"^sk-[A-Za-z0-9]{20,}$"),  # OpenAI-style keys
    re.compile(r"^nvapi-[A-Za-z0-9_-]{20,}$"),  # NVIDIA API keys
    re.compile(r"^hf_[A-Za-z0-9]{20,}$"),  # HuggingFace tokens
    re.compile(r"^ghp_[A-Za-z0-9]{36}$"),  # GitHub personal tokens
    re.compile(r"^[A-Za-z0-9+/]{40,}={0,2}$"),  # Base64-encoded secrets
    re.compile(r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*$"),  # JWT
]

REDACTED = "********"


def redact_secrets(key: str, value: str) -> str:
    """
    Return REDACTED if the key or value looks like a secret.
    Otherwise return the original value.
    """
    if not value:
        return value

    # Key-based detection
    if _SECRET_KEY_PATTERNS.search(key):
        return REDACTED

    # Value-based detection
    for pattern in _SECRET_VALUE_PATTERNS:
        if pattern.match(value.strip()):
            return REDACTED

    return value


def redact_env_dict(env: dict[str, str]) -> dict[str, str]:
    """Return a copy of the env dict with secrets redacted."""
    return {k: redact_secrets(k, v) for k, v in env.items()}


def scan_environment_for_exposed_secrets() -> list[dict[str, Any]]:
    """
    Scan current environment variables for exposed secrets.
    Returns a list of findings (never includes actual values).
    """
    findings: list[dict[str, Any]] = []
    for key, value in os.environ.items():
        if _SECRET_KEY_PATTERNS.search(key) and value:
            findings.append(
                {
                    "variable": key,
                    "detected_reason": "Key name matches secret pattern",
                    "value": REDACTED,
                    "severity": "MEDIUM",
                    "recommendation": (
                        f"Ensure {key} is not exposed in logs, container images, "
                        "or shared environments. Use a secrets manager."
                    ),
                }
            )
    return findings


def scan_file_for_secrets(path: Path) -> list[dict[str, Any]]:
    """
    Scan a text file for lines that may contain secrets.
    Returns findings without including the actual secret values.
    Never raises.
    """
    findings: list[dict[str, Any]] = []
    try:
        content = path.read_text(errors="replace")
        for lineno, line in enumerate(content.splitlines(), 1):
            # Key=Value pattern
            match = re.search(r'([A-Za-z_][A-Za-z0-9_]*)\s*[=:]\s*([^\s#\'"]{8,})', line)
            if match:
                key = match.group(1)
                if _SECRET_KEY_PATTERNS.search(key):
                    findings.append(
                        {
                            "file": str(path),
                            "line": lineno,
                            "variable": key,
                            "value": REDACTED,
                            "severity": "HIGH",
                            "recommendation": (
                                f"Remove {key} from {path.name} and use environment "
                                "variables or a secrets manager."
                            ),
                        }
                    )
    except (OSError, PermissionError):
        pass
    return findings
