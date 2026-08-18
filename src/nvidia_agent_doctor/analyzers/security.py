"""NVIDIA Agent Doctor — Security analyzer."""

from __future__ import annotations

from nvidia_agent_doctor.core.result import CheckResult, SectionResult, SecurityFinding
from nvidia_agent_doctor.core.severity import SecuritySeverity, Severity
from nvidia_agent_doctor.security.credentials import scan_environment_for_exposed_secrets
from nvidia_agent_doctor.security.permissions import (
    check_nvidia_config_permissions,
    check_ssh_key_permissions,
    is_running_as_root,
)


def analyze_security() -> SectionResult:
    """Perform baseline security analysis."""
    section = SectionResult(name="security", display_name="Security")

    # Root check
    if is_running_as_root():
        section.checks.append(
            CheckResult(
                name="running_as_root",
                severity=Severity.WARNING,
                message="Running as root",
                detail="Running NVIDIA workloads as root increases attack surface.",
                recommendation=("Run AI workloads as a non-root user with minimal privileges."),
            )
        )
        section.security_findings.append(
            SecurityFinding(
                title="Process running as root",
                severity=SecuritySeverity.MEDIUM,
                description="NVIDIA Agent Doctor is running as root.",
                recommendation="Use a dedicated non-root user for AI workloads.",
                component="system",
            )
        )
    else:
        section.checks.append(
            CheckResult(
                name="running_as_root",
                severity=Severity.PASS,
                message="Not running as root",
            )
        )

    # Environment secret scan
    secret_findings = scan_environment_for_exposed_secrets()
    if secret_findings:
        section.checks.append(
            CheckResult(
                name="env_secrets",
                severity=Severity.WARNING,
                message=f"{len(secret_findings)} potentially sensitive env var(s) detected",
                detail="Values redacted. Use 'nad security scan' for full details.",
            )
        )
        for finding in secret_findings:
            section.security_findings.append(
                SecurityFinding(
                    title=f"Sensitive env var: {finding['variable']}",
                    severity=SecuritySeverity.MEDIUM,
                    description=finding["detected_reason"],
                    recommendation=finding["recommendation"],
                    component="environment",
                )
            )
    else:
        section.checks.append(
            CheckResult(
                name="env_secrets",
                severity=Severity.PASS,
                message="No obvious secrets in environment variables",
            )
        )

    # SSH key permissions
    ssh_findings = check_ssh_key_permissions()
    if ssh_findings:
        for finding in ssh_findings:
            sev = Severity.WARNING if finding["severity"] == "MEDIUM" else Severity.ERROR
            section.checks.append(
                CheckResult(
                    name="ssh_permissions",
                    severity=sev,
                    message=finding["description"],
                    recommendation=finding["recommendation"],
                )
            )
    else:
        section.checks.append(
            CheckResult(
                name="ssh_permissions",
                severity=Severity.PASS,
                message="SSH key permissions appear correct",
            )
        )

    # Config file permissions
    config_findings = check_nvidia_config_permissions()
    if config_findings:
        for finding in config_findings:
            sev = Severity.WARNING if finding["severity"] in ("MEDIUM", "LOW") else Severity.ERROR
            section.checks.append(
                CheckResult(
                    name="config_permissions",
                    severity=sev,
                    message=finding["description"],
                    recommendation=finding["recommendation"],
                )
            )
    else:
        section.checks.append(
            CheckResult(
                name="config_permissions",
                severity=Severity.PASS,
                message="Config file permissions appear correct",
            )
        )

    return section
