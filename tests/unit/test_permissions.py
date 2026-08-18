"""Platform-specific permission-analysis tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from nvidia_agent_doctor.security.permissions import check_file_permissions


def test_windows_permission_bits_do_not_create_posix_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows ACLs, not POSIX mode bits, determine effective permissions."""
    target = tmp_path / "config.toml"
    target.write_text("[doctor]\n")
    monkeypatch.setattr("nvidia_agent_doctor.security.permissions.os.name", "nt")

    result = check_file_permissions(target)

    assert result["supported"] is False
    assert result["findings"] == []
