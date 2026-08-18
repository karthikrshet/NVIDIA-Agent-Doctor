"""NVIDIA Agent Doctor — Configuration loader."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ConfigError(ValueError):
    """Raised when a user-supplied configuration cannot be safely applied."""


class StrictConfigModel(BaseModel):
    """Base model that rejects misspelled or unsupported configuration keys."""

    model_config = ConfigDict(extra="forbid")


class BenchmarkConfig(StrictConfigModel):
    max_memory_mb: int = Field(default=128, ge=16, le=1024)
    timeout_seconds: int = Field(default=15, ge=1, le=300)


class MCPConfig(StrictConfigModel):
    config_paths: list[str] = Field(default_factory=list)


class SkillsConfig(StrictConfigModel):
    scan_depth: int = 3


class NADConfig(StrictConfigModel):
    """Top-level configuration for settings actively consumed by the CLI."""

    benchmark: BenchmarkConfig = Field(default_factory=BenchmarkConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)


def _load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file or raise a precise configuration error."""
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"Invalid configuration at {path}: {exc}") from exc


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

    if config_path is not None and not config_path.is_file():
        raise ConfigError(f"Configuration file not found: {config_path}")

    for candidate in candidates:
        if candidate.exists():
            try:
                return NADConfig.model_validate(_load_toml(candidate))
            except ValidationError as exc:
                raise ConfigError(f"Invalid configuration at {candidate}: {exc}") from exc
    return NADConfig()
