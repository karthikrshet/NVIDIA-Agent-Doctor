"""NVIDIA Agent Doctor — SKILL.md parser."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from nvidia_agent_doctor.core.models import SkillInfo

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Heuristic patterns
_SHELL_CMD_PATTERN = re.compile(
    r"```(?:bash|sh|shell|zsh|powershell|cmd)\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)
_URL_PATTERN = re.compile(r"https?://[^\s\"`'\"]+")
_FILE_PATH_PATTERN = re.compile(r"(?:read|write|open|access|cat|touch|rm|cp|mv)\s+([/~][^\s]+)")
_CREDENTIAL_PATTERN = re.compile(
    r"\b(API_KEY|TOKEN|PASSWORD|SECRET|CREDENTIAL|AUTH_KEY|"
    r"OPENAI_API_KEY|ANTHROPIC_API_KEY|HF_TOKEN|NVIDIA_API_KEY|NGC_API_KEY)\b",
    re.IGNORECASE,
)
_SCRIPT_PATTERN = re.compile(r"(?:run|execute|call)\s+([\w/.-]+\.(?:py|sh|js|ts|rb))")


def parse_skill_file(path: Path) -> SkillInfo | None:
    """
    Parse a SKILL.md file into a SkillInfo object.
    Returns None if the file cannot be read or parsed.
    """
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    metadata = _parse_frontmatter(content)
    instructions = _strip_frontmatter(content)

    return SkillInfo(
        name=metadata.get("name") or path.stem,
        path=str(path),
        description=metadata.get("description"),
        version=str(metadata.get("version")) if metadata.get("version") else None,
        author=metadata.get("author"),
        raw_instructions=instructions,
        referenced_scripts=_find_scripts(instructions),
        shell_commands=_find_shell_commands(instructions),
        network_patterns=_find_urls(instructions),
        file_patterns=_find_file_accesses(instructions),
        credential_references=_find_credential_references(instructions),
        external_urls=_find_urls(instructions),
    )


def _parse_frontmatter(content: str) -> dict[str, Any]:
    """Extract YAML frontmatter from SKILL.md content."""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}
    try:
        import yaml

        data = yaml.safe_load(match.group(1))
        return data if isinstance(data, dict) else {}
    except Exception:
        # Minimal key: value parser fallback
        result: dict[str, Any] = {}
        for line in match.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                result[k.strip()] = v.strip()
        return result


def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from content."""
    match = _FRONTMATTER_RE.match(content)
    if match:
        return content[match.end() :]
    return content


def _find_shell_commands(text: str) -> list[str]:
    """Extract shell commands from code blocks."""
    commands: list[str] = []
    for match in _SHELL_CMD_PATTERN.finditer(text):
        block = match.group(1).strip()
        # Extract individual commands (non-comment, non-empty lines)
        for line in block.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                commands.append(line)
    return commands[:50]  # Limit to 50


def _find_urls(text: str) -> list[str]:
    return list(dict.fromkeys(_URL_PATTERN.findall(text)))[:20]


def _find_file_accesses(text: str) -> list[str]:
    return list(dict.fromkeys(_FILE_PATH_PATTERN.findall(text)))[:20]


def _find_credential_references(text: str) -> list[str]:
    return list(dict.fromkeys(_CREDENTIAL_PATTERN.findall(text)))[:20]


def _find_scripts(text: str) -> list[str]:
    return list(dict.fromkeys(_SCRIPT_PATTERN.findall(text)))[:20]
