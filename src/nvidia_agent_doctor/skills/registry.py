"""NVIDIA Agent Doctor — Cross-skill risk graph builder."""

from __future__ import annotations

from typing import Any

from nvidia_agent_doctor.core.severity import SecuritySeverity
from nvidia_agent_doctor.skills.scanner import SkillScanResult


class RiskEdge:
    """An edge in the skill risk graph."""

    def __init__(
        self,
        source: str,
        target: str,
        risk_type: str,
        severity: SecuritySeverity,
        description: str,
    ) -> None:
        self.source = source
        self.target = target
        self.risk_type = risk_type
        self.severity = severity
        self.description = description


class SkillRiskGraph:
    """Cross-skill risk graph showing potential data-flow risks."""

    def __init__(self, results: list[SkillScanResult]) -> None:
        self.results = results
        self.edges: list[RiskEdge] = []
        self._build()

    def _build(self) -> None:
        """Build risk edges between skills that have complementary capabilities."""
        # Skills with filesystem read access
        fs_readers = [
            r
            for r in self.results
            if r.skill.file_patterns
            or any(
                "cat" in cmd or "read" in cmd or "open(" in cmd for cmd in r.skill.shell_commands
            )
        ]

        # Skills with network send capability
        network_senders = [
            r
            for r in self.results
            if r.skill.network_patterns
            or any(
                "curl" in cmd or "wget" in cmd or "requests" in cmd
                for cmd in r.skill.shell_commands
            )
        ]

        # Skills with credential access
        cred_accessors = [r for r in self.results if r.skill.credential_references]

        # Filesystem → Network risk
        for fs_skill in fs_readers:
            for net_skill in network_senders:
                if fs_skill is not net_skill:
                    self.edges.append(
                        RiskEdge(
                            source=fs_skill.skill.name,
                            target=net_skill.skill.name,
                            risk_type="filesystem_to_network",
                            severity=SecuritySeverity.MEDIUM,
                            description=(
                                f"'{fs_skill.skill.name}' reads local files; "
                                f"'{net_skill.skill.name}' can send network requests. "
                                "Combined, these skills could form a data exfiltration path."
                            ),
                        )
                    )

        # Credentials → Network risk
        for cred_skill in cred_accessors:
            for net_skill in network_senders:
                if cred_skill is not net_skill:
                    self.edges.append(
                        RiskEdge(
                            source=cred_skill.skill.name,
                            target=net_skill.skill.name,
                            risk_type="credentials_to_network",
                            severity=SecuritySeverity.HIGH,
                            description=(
                                f"'{cred_skill.skill.name}' accesses credentials; "
                                f"'{net_skill.skill.name}' can send network requests. "
                                "This combination requires careful review."
                            ),
                        )
                    )

    @property
    def high_risk_edges(self) -> list[RiskEdge]:
        return [
            e
            for e in self.edges
            if e.severity in (SecuritySeverity.HIGH, SecuritySeverity.CRITICAL)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "skills": [r.skill.name for r in self.results],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "risk_type": e.risk_type,
                    "severity": e.severity.value,
                    "description": e.description,
                }
                for e in self.edges
            ],
            "high_risk_count": len(self.high_risk_edges),
            "note": (
                "Risk graph is based on heuristic analysis. "
                "A potential risk path does not indicate confirmed malicious behavior. "
                "All findings require human review."
            ),
        }

    def render_ascii(self) -> str:
        """Render a simple ASCII representation of the risk graph."""
        if not self.results:
            return "No skills found."

        lines = ["Agent Risk Graph", "=" * 40]
        lines.append("Agent")
        for result in self.results:
            prefix = "├──" if result is not self.results[-1] else "└──"
            lines.append(f" {prefix} Skill: {result.skill.name} [{result.risk_level.value}]")
            if result.skill.file_patterns:
                lines.append(" │     └── filesystem access")
            if result.skill.network_patterns or any(
                "curl" in c for c in result.skill.shell_commands
            ):
                lines.append(" │     └── network access")
            if result.skill.credential_references:
                lines.append(" │     └── credential references")

        if self.high_risk_edges:
            lines.append("")
            lines.append("Cross-Skill Risk Paths:")
            for edge in self.high_risk_edges:
                lines.append(f"  [{edge.severity.value}] {edge.source} → {edge.target}")
                lines.append(f"    {edge.description}")

        return "\n".join(lines)
