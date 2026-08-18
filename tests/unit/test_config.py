"""Configuration validation and override tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from nvidia_agent_doctor.core.config import ConfigError, load_config


def test_explicit_config_is_loaded(tmp_path: Path) -> None:
    config = tmp_path / "nad.toml"
    config.write_text("[skills]\nscan_depth = 7\n")

    result = load_config(config)

    assert result.skills.scan_depth == 7


@pytest.mark.parametrize(
    "contents",
    ["[skills\nscan_depth = 2", "[skills]\nunknown_option = true"],
)
def test_invalid_config_never_silently_falls_back(tmp_path: Path, contents: str) -> None:
    config = tmp_path / "invalid.toml"
    config.write_text(contents)

    with pytest.raises(ConfigError):
        load_config(config)
