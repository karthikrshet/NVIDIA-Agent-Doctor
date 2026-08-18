"""NVIDIA Agent Doctor — Configuration loader."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class DoctorConfig(BaseModel):
    strict: bool = False


class SecurityConfig(BaseModel):
    enabled: bool = True
    credential_scan: bool = True


class BenchmarkConfig(BaseModel):
    enabled: bool = False
    warmup_runs: int = 3
    benchmark_runs: int = 10


class OpenShellConfig(BaseModel):
    enabled: bool = True


class MCPConfig(BaseModel):
    enabled: bool = True
    config_paths: list[str] = Field(default_factory=list)


class SkillsConfig(BaseModel):
    enabled: bool = True
    scan_depth: int = 3


class ReportConfig(BaseModel):
    default_format: str = "terminal"
    output_dir: str = "."


class LoggingConfig(BaseModel):
    level: str = "WARNING"


class NADConfig(BaseModel):
    """Top-level configuration for NVIDIA Agent Doctor."""

    doctor: DoctorConfig = Field(default_factory=DoctorConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    benchmark: BenchmarkConfig = Field(default_factory=BenchmarkConfig)
    openshell: OpenShellConfig = Field(default_factory=OpenShellConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def _load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file, returning an empty dict on any error."""
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def load_config(config_path: Path | None = None) -> NADConfig:
    """Load configuration from .nvidia-agent-doctor.toml, with fallback defaults.

    Search order:
    1. Explicit path (--config CLI flag)
    2. ./.nvidia-agent-doctor.toml
    3. ~/.nvidia-agent-doctor.toml
    4. Built-in defaults
    """
    candidates: list[Path] = []
    if config_path is not None:
        candidates.append(config_path)

    candidates.extend(
        [
            Path.cwd() / ".nvidia-agent-doctor.toml",
            Path.home() / ".nvidia-agent-doctor.toml",
        ]
    )

    raw: dict[str, Any] = {}
    for candidate in candidates:
        if candidate.exists():
            raw = _load_toml(candidate)
            break

    try:
        return NADConfig.model_validate(raw)
    except Exception:
        return NADConfig()
