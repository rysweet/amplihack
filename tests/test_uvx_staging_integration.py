"""Integration tests for UVX staging with enhanced settings management."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from amplihack.utils.uvx_models import UVXConfiguration
from amplihack.utils.uvx_staging_v2 import UVXStager


class TestUVXStagingIntegration(unittest.TestCase):
    """Integration tests for UVX staging with settings enhancements."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.source_dir = self.temp_dir / "source"
        self.target_dir = self.temp_dir / "target"

        # Create directory structure
        self.source_dir.mkdir(parents=True)
        self.target_dir.mkdir(parents=True)

        # Create mock .claude directory structure
        self.source_claude_dir = self.source_dir / ".claude"
        self.source_claude_dir.mkdir()

        # Create test settings.json (project version, not UVX-optimized)
        self.source_settings = self.source_claude_dir / "settings.json"
        project_settings = {
            "permissions": {
                "allow": ["Bash", "TodoWrite", "WebSearch", "WebFetch"],
                "deny": [],
                "defaultMode": "bypassPermissions",  # Good, but missing tools
                "additionalDirectories": [".claude", "Specs"],
            },
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": ".claude/tools/amplihack/hooks/session_start.py",
                                "timeout": 10000,
                            }
                        ]
                    }
                ]
            },
        }
        with open(self.source_settings, "w", encoding="utf-8") as f:
            json.dump(project_settings, f, indent=2)

        # Create other files in .claude directory
        tools_dir = self.source_claude_dir / "tools" / "amplihack" / "hooks"
        tools_dir.mkdir(parents=True)
        (tools_dir / "session_start.py").write_text("# Session start hook")
        (tools_dir / "stop.py").write_text("# Stop hook")

        self.config = UVXConfiguration(overwrite_existing=True)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_fresh_uvx_installation_creates_enhanced_settings(self):
        """Test that fresh UVX installation creates enhanced settings.json."""
        stager = UVXStager(self.config)
        result = stager._stage_claude_directory(self.source_claude_dir, self.target_dir / ".claude")

        self.assertTrue(result, "Should successfully stage .claude directory")

        # Check that settings.json was created
        target_settings = self.target_dir / ".claude" / "settings.json"
        self.assertTrue(target_settings.exists(), "settings.json should exist")

        # Verify enhanced settings content
        with open(target_settings, encoding="utf-8") as f:
            settings = json.load(f)

        # Should have bypass permissions
        self.assertEqual(settings["permissions"]["defaultMode"], "bypassPermissions")

        # Should have comprehensive tool allowlist
        allow_list = settings["permissions"]["allow"]
        expected_tools = [
            "Bash",
            "TodoWrite",
            "WebFetch",
            "WebSearch",
            "Grep",
            "Glob",
            "Read",
            "Edit",
            "MultiEdit",
        ]
        for tool in expected_tools:
            self.assertIn(
                tool, allow_list, f"{tool} should be in allow list for fresh UVX installation"
            )

        # Should have all amplihack hooks
        hooks = settings["hooks"]
        required_hooks = ["SessionStart", "Stop", "PostToolUse", "PreCompact"]
        for hook in required_hooks:
            self.assertIn(hook, hooks, f"{hook} should be configured")

    def test_existing_settings_with_bypass_preserved(self):
        """Test that existing settings with bypass permissions are preserved."""
        # Create target directory with existing settings that have bypass permissions
        target_claude_dir = self.target_dir / ".claude"
        target_claude_dir.mkdir(parents=True)
        target_settings = target_claude_dir / "settings.json"

        existing_good_settings = {
            "permissions": {
                "allow": ["Bash", "CustomTool"],
                "deny": [],
                "defaultMode": "bypassPermissions",  # Already has bypass
                "additionalDirectories": ["custom"],
            },
            "customProperty": "userValue",
        }
        with open(target_settings, "w", encoding="utf-8") as f:
            json.dump(existing_good_settings, f)

        stager = UVXStager(self.config)
        result = stager._stage_claude_directory(self.source_claude_dir, target_claude_dir)

        self.assertTrue(result, "Should successfully stage .claude directory")

        # Verify that existing settings were preserved (copied from source)
        with open(target_settings, encoding="utf-8") as f:
            final_settings = json.load(f)

        # Should still have bypass permissions
        self.assertEqual(final_settings["permissions"]["defaultMode"], "bypassPermissions")

    def test_existing_settings_without_bypass_enhanced(self):
        """Test that existing settings without bypass permissions are enhanced."""
        # Create target directory with settings that need enhancement
        target_claude_dir = self.target_dir / ".claude"
        target_claude_dir.mkdir(parents=True)
        target_settings = target_claude_dir / "settings.json"

        limited_settings = {
            "permissions": {
                "allow": ["Bash"],
                "deny": [],
                "defaultMode": "askPermissions",  # Needs enhancement
                "additionalDirectories": [],
            }
        }
        with open(target_settings, "w", encoding="utf-8") as f:
            json.dump(limited_settings, f)

        stager = UVXStager(self.config)
        result = stager._stage_claude_directory(self.source_claude_dir, target_claude_dir)

        self.assertTrue(result, "Should successfully stage .claude directory")

        # Verify that settings were enhanced with UVX template
        with open(target_settings, encoding="utf-8") as f:
            enhanced_settings = json.load(f)

        # Should now have bypass permissions
        self.assertEqual(enhanced_settings["permissions"]["defaultMode"], "bypassPermissions")

        # Should have comprehensive tool allowlist
        allow_list = enhanced_settings["permissions"]["allow"]
        essential_tools = ["Bash", "TodoWrite", "WebFetch", "Grep", "Read", "Edit"]
        for tool in essential_tools:
            self.assertIn(tool, allow_list, f"{tool} should be in enhanced allow list")

    def test_backup_created_for_existing_settings(self):
        """Test that backup is created when replacing existing settings."""
        # Create target directory with existing settings
        target_claude_dir = self.target_dir / ".claude"
        target_claude_dir.mkdir(parents=True)
        target_settings = target_claude_dir / "settings.json"

        original_settings = {"test": "original"}
        with open(target_settings, "w", encoding="utf-8") as f:
            json.dump(original_settings, f)

        stager = UVXStager(self.config)
        result = stager._stage_claude_directory(self.source_claude_dir, target_claude_dir)

        self.assertTrue(result, "Should successfully stage .claude directory")

        # Check that backup was created
        backup_file = target_claude_dir / "settings.json.backup.uvx"
        self.assertTrue(backup_file.exists(), "Backup file should be created")

        # Verify backup contains original settings
        with open(backup_file, encoding="utf-8") as f:
            backup_settings = json.load(f)

        self.assertEqual(
            backup_settings, original_settings, "Backup should contain original settings"
        )

    def test_other_claude_files_copied_normally(self):
        """Test that non-settings.json files in .claude are copied normally."""
        # Create additional files in source .claude directory
        (self.source_claude_dir / "other_config.json").write_text('{"other": "config"}')
        agents_dir = self.source_claude_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "test_agent.md").write_text("# Test Agent")

        stager = UVXStager(self.config)
        result = stager._stage_claude_directory(self.source_claude_dir, self.target_dir / ".claude")

        self.assertTrue(result, "Should successfully stage .claude directory")

        # Verify other files were copied
        target_claude_dir = self.target_dir / ".claude"
        self.assertTrue((target_claude_dir / "other_config.json").exists())
        self.assertTrue((target_claude_dir / "agents" / "test_agent.md").exists())
        self.assertTrue(
            (target_claude_dir / "tools" / "amplihack" / "hooks" / "session_start.py").exists()
        )

        # Verify content is preserved
        other_config_content = (target_claude_dir / "other_config.json").read_text()
        self.assertEqual(other_config_content, '{"other": "config"}')

    def test_error_handling_fallback_to_source_settings(self):
        """Test that if UVX settings creation fails, source settings are used as fallback."""
        # Mock the UVX settings manager to fail
        with patch("amplihack.utils.uvx_staging_v2.uvx_settings_manager") as mock_manager:
            mock_manager.should_use_uvx_template.return_value = True
            mock_manager.create_uvx_settings.return_value = False  # Simulate failure

            stager = UVXStager(self.config)
            result = stager._stage_claude_directory(
                self.source_claude_dir, self.target_dir / ".claude"
            )

            self.assertTrue(result, "Should still succeed using fallback")

            # Verify that source settings were copied as fallback
            target_settings = self.target_dir / ".claude" / "settings.json"
            self.assertTrue(target_settings.exists(), "Settings file should exist")

            # Should contain source settings (not UVX enhanced)
            with open(target_settings, encoding="utf-8") as f:
                settings = json.load(f)

            # Should match source settings structure
            self.assertIn("permissions", settings)


class TestUVXPermissionValidation(unittest.TestCase):
    """Test validation of UVX permission enhancements."""

    def test_comprehensive_tool_allowlist(self):
        """Test that UVX template includes comprehensive tool allowlist."""
        from amplihack.utils.uvx_settings_manager import uvx_settings_manager

        template = uvx_settings_manager.get_template_settings()
        self.assertIsNotNone(template)

        allow_list = template["permissions"]["allow"]

        # Core Claude Code tools
        essential_tools = [
            "Bash",  # Command execution
            "TodoWrite",  # Task management
            "WebFetch",  # Web content
            "WebSearch",  # Search functionality
            "Grep",  # Code search
            "Glob",  # File pattern matching
            "Read",  # File reading
            "Edit",  # File editing
            "MultiEdit",  # Batch editing
            "Write",  # File writing
            "NotebookEdit",  # Jupyter support
        ]

        for tool in essential_tools:
            self.assertIn(tool, allow_list, f"{tool} should be pre-approved in UVX template")

        # MCP tools for IDE integration
        mcp_tools = ["mcp__ide__getDiagnostics", "mcp__ide__executeCode"]

        for tool in mcp_tools:
            self.assertIn(tool, allow_list, f"{tool} should be pre-approved for IDE integration")

    def test_bypass_permissions_enabled(self):
        """Test that UVX template has bypass permissions enabled."""
        from amplihack.utils.uvx_settings_manager import uvx_settings_manager

        template = uvx_settings_manager.get_template_settings()
        self.assertEqual(template["permissions"]["defaultMode"], "bypassPermissions")
        self.assertEqual(template["permissions"]["deny"], [])

    def test_comprehensive_directory_access(self):
        """Test that UVX template includes comprehensive directory access."""
        from amplihack.utils.uvx_settings_manager import uvx_settings_manager

        template = uvx_settings_manager.get_template_settings()
        additional_dirs = template["permissions"]["additionalDirectories"]

        expected_dirs = [".claude", "Specs", ".git", "src", "tests", "docs"]
        for dir_name in expected_dirs:
            self.assertIn(dir_name, additional_dirs, f"{dir_name} should have directory access")


if __name__ == "__main__":
    unittest.main()
