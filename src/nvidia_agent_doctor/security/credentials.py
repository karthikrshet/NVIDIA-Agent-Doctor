"""NVIDIA Agent Doctor — Security credentials detection and redaction."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

# Patterns that suggest a value is a secret
_SECRET_KEY_PATTERN = (
    r"(?:api[_-]?key|apikey|secret|password|passwd|token|credential|"
    r"auth(?:orization|entication)?(?:$|[_-])|"
    r"private[_-]?key|access[_-]?key|client[_-]?secret|bearer|"
    r"ngc[_-]?api[_-]?key|openai[_-]?key|hf[_-]?token|"
    r"huggingface[_-]?token|anthropic|gemini[_-]?key)"
)
_SECRET_KEY_PATTERNS = re.compile(_SECRET_KEY_PATTERN, re.IGNORECASE)

_SECRET_VALUE_PATTERNS = [
    re.compile(r"^sk-[A-Za-z0-9]{20,}$"),  # OpenAI-style keys
    re.compile(r"^nvapi-[A-Za-z0-9_-]{20,}$"),  # NVIDIA API keys
    re.compile(r"^hf_[A-Za-z0-9]{20,}$"),  # HuggingFace tokens
    re.compile(r"^ghp_[A-Za-z0-9]{36}$"),  # GitHub personal tokens
    re.compile(r"^[A-Za-z0-9+/]{40,}={0,2}$"),  # Base64-encoded secrets
    re.compile(r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*$"),  # JWT
]
_INLINE_SECRET_VALUE_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bnvapi-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*\b"),
]
_SENSITIVE_ASSIGNMENT = re.compile(
    rf"\b({_SECRET_KEY_PATTERN})\s*([=:])\s*([^\s,;]+)", re.IGNORECASE
)

REDACTED = "********"


def redact_text(value: str) -> str:
    """Redact known secret values and key/value assignments in arbitrary text."""
    redacted = value
    for pattern in _SECRET_VALUE_PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    for pattern in _INLINE_SECRET_VALUE_PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    return _SENSITIVE_ASSIGNMENT.sub(_redact_assignment, redacted)


def _redact_assignment(match: re.Match[str]) -> str:
    """Redact a matched sensitive assignment without retaining its value."""
    key, separator, value = match.groups()
    del value
    return f"{key}{separator}{REDACTED}"


def _redact_url(value: str) -> str:
    """Redact credentials and sensitive query parameters from an HTTP(S) URL."""
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        return redact_text(value)
    hostname = parsed.hostname or ""
    netloc = hostname if parsed.port is None else f"{hostname}:{parsed.port}"
    if parsed.username or parsed.password:
        netloc = f"{REDACTED}@{netloc}"
    query = "&".join(
        f"{item_key}={REDACTED if _SECRET_KEY_PATTERNS.search(item_key) else redact_text(item)}"
        for item_key, item in parse_qsl(parsed.query, keep_blank_values=True)
    )
    return urlunsplit((parsed.scheme, netloc, parsed.path, query, parsed.fragment))


def redact_data(value: Any, key: str | None = None) -> Any:
    """Recursively sanitize untrusted data without changing its structure."""
    if isinstance(value, dict):
        return {
            str(item_key): redact_data(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [redact_data(item, key) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_data(item, key) for item in value)
    if isinstance(value, str):
        if key and _SECRET_KEY_PATTERNS.search(key):
            return REDACTED
        if value.startswith(("http://", "https://")):
            return _redact_url(value)
        redacted = redact_text(value)
        redacted = re.sub(
            r"(?i)(--?(?:api[_-]?key|token|secret|password|passwd|credential|auth)[a-z0-9_-]*)"
            r"([=:])[^\s,;]+",
            rf"\1\2{REDACTED}",
            redacted,
        )
        return REDACTED if redact_secrets(key or "", redacted) == REDACTED else redacted
    return value


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
