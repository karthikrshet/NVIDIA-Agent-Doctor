"""NVIDIA Agent Doctor — Data models for system components."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GPUInfo(BaseModel):
    """Information about a single NVIDIA GPU."""

    index: int
    name: str = "Unknown"
    uuid: str | None = None
    driver_version: str | None = None
    cuda_version: str | None = None
    vram_total_mb: int | None = None
    vram_used_mb: int | None = None
    utilization_gpu_pct: int | None = None
    utilization_memory_pct: int | None = None
    temperature_c: int | None = None
    power_draw_w: float | None = None
    power_limit_w: float | None = None
    compute_capability: str | None = None
    persistence_mode: bool | None = None

    @property
    def vram_total_gb(self) -> float | None:
        if self.vram_total_mb is None:
            return None
        return round(self.vram_total_mb / 1024, 1)

    @property
    def vram_used_gb(self) -> float | None:
        if self.vram_used_mb is None:
            return None
        return round(self.vram_used_mb / 1024, 1)

    @property
    def vram_utilization_pct(self) -> int | None:
        if self.vram_total_mb is None or self.vram_used_mb is None or self.vram_total_mb == 0:
            return None
        return round((self.vram_used_mb / self.vram_total_mb) * 100)


class CUDAInfo(BaseModel):
    """Information about the CUDA installation."""

    toolkit_version: str | None = None
    runtime_version: str | None = None
    driver_version: str | None = None
    nvcc_path: str | None = None
    nvcc_available: bool = False
    cuda_home: str | None = None
    cuda_path: str | None = None
    ld_library_path: str | None = None
    cuda_visible_devices: str | None = None
    libraries_found: list[str] = Field(default_factory=list)
    compatible: bool | None = None
    compatibility_notes: list[str] = Field(default_factory=list)


class SystemInfo(BaseModel):
    """General system information."""

    os_name: str = "Unknown"
    os_version: str = "Unknown"
    os_release: str = "Unknown"
    architecture: str = "Unknown"
    hostname: str = "Unknown"
    cpu_count: int | None = None
    cpu_model: str | None = None
    ram_total_gb: float | None = None
    ram_available_gb: float | None = None
    python_version: str = "Unknown"
    python_executable: str = "Unknown"


class PythonPackageInfo(BaseModel):
    """Installed Python package version info."""

    package: str
    version: str | None = None
    installed: bool = False
    cuda_version: str | None = None  # for pytorch builds
    extra: dict[str, Any] = Field(default_factory=dict)


class DockerInfo(BaseModel):
    """Docker / container runtime information."""

    docker_available: bool = False
    docker_version: str | None = None
    docker_server_version: str | None = None
    nvidia_runtime_available: bool = False
    in_container: bool = False
    container_id: str | None = None


class MCPServerInfo(BaseModel):
    """Information about a single MCP server."""

    name: str
    transport: str | None = None
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env_vars: dict[str, str] = Field(default_factory=dict)  # values redacted in output
    url: str | None = None
    config_path: str = "unknown"


class SkillInfo(BaseModel):
    """Information about a parsed agent skill."""

    name: str
    path: str
    description: str | None = None
    version: str | None = None
    author: str | None = None
    raw_instructions: str = ""
    referenced_scripts: list[str] = Field(default_factory=list)
    shell_commands: list[str] = Field(default_factory=list)
    network_patterns: list[str] = Field(default_factory=list)
    file_patterns: list[str] = Field(default_factory=list)
    credential_references: list[str] = Field(default_factory=list)
    external_urls: list[str] = Field(default_factory=list)


class OpenShellInfo(BaseModel):
    """OpenShell runtime information."""

    installed: bool = False
    cli_available: bool = False
    version: str | None = None
    runtime_running: bool | None = None
    sandbox_active: bool | None = None
    policy_configured: bool | None = None
    network_configured: bool | None = None
    credentials_configured: bool | None = None
    observability_configured: bool | None = None
    config_path: str | None = None
