"""NVIDIA Agent Doctor — Agent skills scanner (heuristic static analysis)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from nvidia_agent_doctor.core.models import SkillInfo
from nvidia_agent_doctor.core.severity import SecuritySeverity
from nvidia_agent_doctor.skills.parser import parse_skill_file


# Heuristic patterns for high-risk behaviors
_DANGEROUS_COMMANDS = {
    "rm -rf": "Recursive deletion command detected",
    "curl": "Network data transfer detected (curl)",
    "wget": "Network data transfer detected (wget)",
    "dd ": "Disk write command detected (dd)",
    "chmod 777": "World-writeable permission set",
    "sudo ": "Privilege escalation detected",
    "base64 -d": "Base64 decoding (potential obfuscation)",
    "eval ": "Dynamic code evaluation detected",
    "exec(": "Dynamic code execution detected",
    "__import__": "Dynamic import detected",
    "/dev/tcp": "Raw TCP socket access detected",
    "nc -e": "Netcat reverse shell pattern detected",
    "mkfifo": "Named pipe creation detected",
}

_NETWORK_EXFIL_PATTERNS = [
    re.compile(r"curl\s+.*\$\{?\w+\}?"),           # curl with variable
    re.compile(r"wget\s+.*\$\{?\w+\}?"),           # wget with variable
    re.compile(r"nc\s+.*-e"),                       # netcat with exec
    re.compile(r"python.*http\.server"),            # python http server
]


class SkillScanResult:
    def __init__(self, skill: SkillInfo) -> None:
        self.skill = skill
        self.findings: list[dict[str, Any]] = []
        self.risk_level: SecuritySeverity = SecuritySeverity.INFO

    def add_finding(
        self,
        severity: SecuritySeverity,
        title: str,
        description: str,
        recommendation: str,
    ) -> None:
        self.findings.append({
            "severity": severity,
            "title": title,
            "description": description,
            "recommendation": recommendation,
        })
        if severity.score > self.risk_level.score:
            self.risk_level = severity


def scan_skill(skill: SkillInfo) -> SkillScanResult:
    """
    Perform heuristic static analysis on a skill.

    DISCLAIMER: This is heuristic/static analysis only. It cannot detect
    all malicious code and may produce false positives. Results require
    human review.
    """
    result = SkillScanResult(skill)
    text = skill.raw_instructions

    # Check for dangerous commands
    for pattern, desc in _DANGEROUS_COMMANDS.items():
        if pattern in text:
            severity = (
                SecuritySeverity.HIGH
                if pattern in ("rm -rf", "nc -e", "eval ", "exec(", "/dev/tcp")
                else SecuritySeverity.MEDIUM
            )
            result.add_finding(
                severity=severity,
                title=f"Potentially dangerous command: {pattern.strip()}",
                description=f"{desc} in skill '{skill.name}'.",
                recommendation=(
                    "Review this command carefully. Ensure it is intentional "
                    "and scoped to the minimum necessary access."
                ),
            )

    # Check for network exfiltration patterns
    for pattern in _NETWORK_EXFIL_PATTERNS:
        if pattern.search(text):
            result.add_finding(
                severity=SecuritySeverity.HIGH,
                title="Potential data exfiltration pattern",
                description=(
                    f"Skill '{skill.name}' contains a pattern that could "
                    "be used for data exfiltration."
                ),
                recommendation=(
                    "Verify this network access is intentional and "
                    "necessary. Consider restricting network scope."
                ),
            )

    # Check credential references
    if skill.credential_references:
        result.add_finding(
            severity=SecuritySeverity.MEDIUM,
            title="Credential variable references",
            description=(
                f"Skill '{skill.name}' references potentially sensitive "
                f"variables: {skill.credential_references}."
            ),
            recommendation=(
                "Ensure credentials are passed securely (environment variables, "
                "secrets manager) and are not hardcoded in skill instructions."
            ),
        )

    # Check for broad filesystem access
    broad_paths = [p for p in skill.file_patterns if p in ("/", "/etc", "/home", "/root", "/var")]
    if broad_paths:
        result.add_finding(
            severity=SecuritySeverity.HIGH,
            title="Broad filesystem access",
            description=(
                f"Skill '{skill.name}' accesses broad filesystem paths: {broad_paths}."
            ),
            recommendation="Restrict file access to the minimum required paths.",
        )

    # Check external URLs
    external_urls = [
        u for u in skill.external_urls
        if not any(safe in u for safe in ["github.com", "pypi.org", "nvidia.com"])
    ]
    if len(external_urls) > 5:
        result.add_finding(
            severity=SecuritySeverity.LOW,
            title="Multiple external URL references",
            description=(
                f"Skill '{skill.name}' references {len(external_urls)} external URLs."
            ),
            recommendation=(
                "Review external URLs to ensure they are trusted and necessary."
            ),
        )

    if not result.findings:
        result.add_finding(
            severity=SecuritySeverity.INFO,
            title="No obvious security issues detected",
            description=(
                f"Skill '{skill.name}' passed basic heuristic checks. "
                "This does not guarantee the skill is safe."
            ),
            recommendation="Periodically review skill instructions and dependencies.",
        )

    return result


def scan_skills_directory(
    directory: Path,
    max_depth: int = 3,
) -> list[SkillScanResult]:
    """
    Scan a directory for SKILL.md files and analyze each one.
    Returns a list of SkillScanResult objects.
    """
    results: list[SkillScanResult] = []

    pattern_files = list(directory.rglob("SKILL.md")) + list(directory.rglob("skill.md"))
    pattern_files = sorted(set(pattern_files))

    for skill_file in pattern_files:
        # Check depth
        try:
            relative = skill_file.relative_to(directory)
            if len(relative.parts) > max_depth + 1:
                continue
        except ValueError:
            continue

        skill = parse_skill_file(skill_file)
        if skill:
            result = scan_skill(skill)
            results.append(result)

    return results
