"""Regression tests for untrusted local scanner inputs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nvidia_agent_doctor.integrations.mcp import discover_mcp_servers
from nvidia_agent_doctor.security.leak_check import run_leak_check
from nvidia_agent_doctor.skills.parser import parse_skill_file
from nvidia_agent_doctor.skills.scanner import scan_skills_directory


def test_leak_check_exercises_all_output_boundaries() -> None:
    result = run_leak_check()

    assert result["passed"] is True
    assert {check["boundary"] for check in result["checks"]} == {
        "json",
        "markdown",
        "html",
        "terminal",
        "exception",
    }


def test_malformed_mcp_config_is_ignored(tmp_path: Path) -> None:
    config = tmp_path / "mcp.json"
    config.write_text("{not valid json", encoding="utf-8")

    assert discover_mcp_servers([str(config)]) == []


def test_mcp_arguments_and_urls_are_redacted(tmp_path: Path) -> None:
    secret = "sk-hostileinput0123456789abcdefghijkl"
    config = tmp_path / "mcp.json"
    config.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "hostile": {
                        "command": "server",
                        "args": ["--token", secret],
                        "url": f"https://example.test/?api_key={secret}",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    servers = discover_mcp_servers([str(config)])

    assert len(servers) == 1
    assert secret not in str(servers[0].model_dump())


def test_skill_parser_rejects_oversized_input(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text("x" * 1_048_577, encoding="utf-8")

    assert parse_skill_file(skill) is None


def test_scanners_reject_symlinked_files(tmp_path: Path) -> None:
    target = tmp_path / "outside-skill.md"
    target.write_text("# skill", encoding="utf-8")
    link = tmp_path / "SKILL.md"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Symlinks are not available to this test process")

    assert parse_skill_file(link) is None
    assert scan_skills_directory(tmp_path) == []


def test_mcp_scanner_rejects_symlinked_configuration(tmp_path: Path) -> None:
    target = tmp_path / "outside-mcp.json"
    target.write_text('{"mcpServers": {"safe": {"command": "server"}}}', encoding="utf-8")
    link = tmp_path / "mcp.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Symlinks are not available to this test process")

    assert discover_mcp_servers([str(link)]) == []
