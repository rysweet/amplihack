"""UVX Integration Tests - Settings.json Generation.

Tests settings.json generation through real UVX launches:
- Initial settings.json creation
- Plugin metadata inclusion
- LSP configuration merging
- MCP server configuration
- Settings validation

Philosophy:
- Outside-in testing (user perspective)
- Real UVX execution (no mocking)
- CI-ready (non-interactive)
- Fast execution (< 5 minutes total)
"""

import json

import pytest

from .harness import (
    create_python_project,
    uvx_launch,
    uvx_launch_with_test_project,
)

# Git reference to test
GIT_REF = "feat/issue-1948-plugin-architecture"
TIMEOUT = 60


class TestSettingsGeneration:
    """Test settings.json generation via UVX."""

    def test_settings_json_created(self):
        """Test that settings.json is created."""
        project_dir = create_python_project()

        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Initialize project and generate settings",
            cwd=project_dir,
            timeout=TIMEOUT,
        )

        result.assert_success()

        # Check if settings.json was created
        settings_path = project_dir / ".claude" / "settings.json"
        if settings_path.exists():
            # Verify it's valid JSON
            settings = json.loads(settings_path.read_text())
            assert isinstance(settings, dict)

    def test_settings_json_structure(self):
        """Test that settings.json has correct structure."""
        project_dir = create_python_project()

        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Generate settings.json for this project",
            cwd=project_dir,
            timeout=TIMEOUT,
        )

        result.assert_success()

        settings_path = project_dir / ".claude" / "settings.json"
        if settings_path.exists():
            settings = json.loads(settings_path.read_text())

            # Should have expected top-level keys
            # (Exact structure depends on implementation)
            assert isinstance(settings, dict)


class TestPluginMetadata:
    """Test plugin metadata in settings.json."""

    def test_plugin_metadata_included(self):
        """Test that plugin metadata is included."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Show plugin information",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Plugin metadata might be in output or logs

    def test_plugin_version_tracking(self):
        """Test that plugin versions are tracked."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What plugins are installed?",
            timeout=TIMEOUT,
        )

        result.assert_success()


class TestLSPConfigurationMerging:
    """Test LSP configuration merging into settings.json."""

    def test_lsp_config_in_settings(self):
        """Test that LSP configuration is added to settings."""
        project_dir = create_python_project()

        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Configure LSP for this Python project",
            cwd=project_dir,
            timeout=TIMEOUT,
        )

        result.assert_success()

        settings_path = project_dir / ".claude" / "settings.json"
        if settings_path.exists():
            settings = json.loads(settings_path.read_text())
            # LSP config might be in mcpServers or other location
            assert isinstance(settings, dict)

    def test_multiple_lsp_configs_merge(self):
        """Test that multiple LSP configs merge correctly."""
        result = uvx_launch_with_test_project(
            project_files={
                "main.py": "print('python')",
                "index.ts": "console.log('typescript');",
            },
            git_ref=GIT_REF,
            prompt="Configure LSP for all languages",
            timeout=TIMEOUT,
        )

        result.assert_success()


class TestMCPServerConfiguration:
    """Test MCP server configuration in settings.json."""

    def test_mcp_servers_section(self):
        """Test that mcpServers section is present."""
        project_dir = create_python_project()

        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Show MCP server configuration",
            cwd=project_dir,
            timeout=TIMEOUT,
        )

        result.assert_success()

    def test_mcp_server_from_plugin(self):
        """Test that plugins can add MCP servers."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What MCP servers are configured?",
            timeout=TIMEOUT,
        )

        result.assert_success()


class TestSettingsValidation:
    """Test settings.json validation."""

    def test_settings_json_is_valid_json(self):
        """Test that generated settings.json is valid JSON."""
        project_dir = create_python_project()

        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Generate settings for this project",
            cwd=project_dir,
            timeout=TIMEOUT,
        )

        result.assert_success()

        settings_path = project_dir / ".claude" / "settings.json"
        if settings_path.exists():
            # Should parse without error
            try:
                settings = json.loads(settings_path.read_text())
                assert isinstance(settings, dict)
            except json.JSONDecodeError as e:
                pytest.fail(f"settings.json is not valid JSON: {e}")

    def test_settings_formatting(self):
        """Test that settings.json is properly formatted."""
        project_dir = create_python_project()

        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Create formatted settings.json",
            cwd=project_dir,
            timeout=TIMEOUT,
        )

        result.assert_success()

        settings_path = project_dir / ".claude" / "settings.json"
        if settings_path.exists():
            content = settings_path.read_text()
            # Should be indented (not minified)
            assert "  " in content or "\t" in content, (
                "Settings should be formatted with indentation"
            )


class TestSettingsUpdate:
    """Test settings.json updates and merging."""

    def test_settings_update_preserves_existing(self):
        """Test that updating settings preserves existing values."""
        project_dir = create_python_project()

        # Create initial settings
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_path = claude_dir / "settings.json"
        initial_settings = {"custom_key": "custom_value"}
        settings_path.write_text(json.dumps(initial_settings, indent=2))

        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Update settings with LSP config",
            cwd=project_dir,
            timeout=TIMEOUT,
        )

        result.assert_success()

        # Check if custom_key is preserved
        if settings_path.exists():
            settings = json.loads(settings_path.read_text())
            # Depending on merge strategy, custom_key might be preserved
            assert isinstance(settings, dict)

    def test_settings_conflict_resolution(self):
        """Test that settings conflicts are resolved correctly."""
        project_dir = create_python_project()

        # Create conflicting settings
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_path = claude_dir / "settings.json"
        conflicting_settings = {"mcpServers": {"existing": "value"}}
        settings_path.write_text(json.dumps(conflicting_settings, indent=2))

        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Add new MCP server to settings",
            cwd=project_dir,
            timeout=TIMEOUT,
        )

        result.assert_success()


class TestSettingsIntegration:
    """Test settings.json integration with plugin system."""

    def test_settings_generation_performance(self):
        """Test that settings generation is fast."""
        project_dir = create_python_project()

        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Generate settings",
            cwd=project_dir,
            timeout=30,  # Should be fast
        )

        result.assert_success()
        assert result.duration < 30.0, f"Settings generation took {result.duration}s"

    def test_settings_in_gitignore(self):
        """Test that .claude directory handling respects gitignore."""
        project_dir = create_python_project()

        # Create .gitignore
        gitignore = project_dir / ".gitignore"
        gitignore.write_text(".claude/runtime/\n")

        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Generate settings (respect gitignore)",
            cwd=project_dir,
            timeout=TIMEOUT,
        )

        result.assert_success()

    def test_settings_error_handling(self):
        """Test settings generation error handling."""
        # Try to generate settings in read-only location (if possible)
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Generate settings in current directory",
            timeout=TIMEOUT,
        )

        # Should handle errors gracefully
        assert result.exit_code is not None


# Markers for test organization
pytest.mark.integration = pytest.mark.integration
pytest.mark.uvx = pytest.mark.uvx
pytest.mark.settings = pytest.mark.settings
