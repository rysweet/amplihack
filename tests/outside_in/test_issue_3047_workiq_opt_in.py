"""Outside-in behavioral validation for issue #3047 — workiq disabled by default.

Validates that:
1. The workiq MCP server is marked disabled in .mcp.json
2. No other MCP servers were accidentally disabled
3. The work-iq SKILL.md documents the opt-in requirement
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def mcp_config() -> dict:
    mcp_path = REPO_ROOT / ".mcp.json"
    assert mcp_path.exists(), ".mcp.json must exist at repo root"
    return json.loads(mcp_path.read_text())


@pytest.fixture()
def skill_md() -> str:
    skill_path = REPO_ROOT / ".claude" / "skills" / "work-iq" / "SKILL.md"
    assert skill_path.exists(), "work-iq SKILL.md must exist"
    return skill_path.read_text()


class TestWorkiqDisabledByDefault:
    """Verify workiq MCP server ships disabled."""

    def test_workiq_has_disabled_true(self, mcp_config: dict) -> None:
        servers = mcp_config.get("mcpServers", {})
        assert "workiq" in servers, "workiq server must be declared in .mcp.json"
        assert servers["workiq"].get("disabled") is True, "workiq server must have 'disabled': true"

    def test_no_other_servers_accidentally_disabled(self, mcp_config: dict) -> None:
        servers = mcp_config.get("mcpServers", {})
        accidentally_disabled = [
            name
            for name, cfg in servers.items()
            if name != "workiq" and cfg.get("disabled") is True
        ]
        assert accidentally_disabled == [], (
            f"Other servers should not be disabled: {accidentally_disabled}"
        )


class TestSkillDocumentationOptIn:
    """Verify the work-iq skill doc tells users how to enable."""

    def test_skill_md_mentions_disabled_by_default(self, skill_md: str) -> None:
        assert "disabled by default" in skill_md.lower(), (
            "SKILL.md must mention that workiq is disabled by default"
        )

    def test_skill_md_has_enable_instructions(self, skill_md: str) -> None:
        lower = skill_md.lower()
        assert "enable" in lower, "SKILL.md must contain enable instructions"
        # Should reference the mcp-manager or manual toggle
        assert ".mcp.json" in skill_md, "SKILL.md must reference .mcp.json for manual enablement"

    def test_skill_md_has_required_first_heading(self, skill_md: str) -> None:
        assert "Enable MCP Server (Required First)" in skill_md, (
            "SKILL.md must have a clear 'Enable MCP Server (Required First)' heading"
        )
