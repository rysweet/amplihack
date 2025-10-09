"""Test cases for UVX settings manager functionality."""

import json
import tempfile
import unittest
from pathlib import Path

from src.amplihack.utils.uvx_settings_manager import UVXSettingsManager


class TestUVXSettingsManager(unittest.TestCase):
    """Test UVX settings manager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = UVXSettingsManager()
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_should_use_uvx_template_no_existing_file(self):
        """Test UVX template usage when no settings.json exists."""
        non_existent_path = self.temp_dir / "settings.json"
        result = self.manager.should_use_uvx_template(non_existent_path)
        self.assertTrue(result, "Should use UVX template when no settings.json exists")

    def test_should_use_uvx_template_no_bypass_permissions(self):
        """Test UVX template usage when existing settings lack bypass permissions."""
        settings_path = self.temp_dir / "settings.json"

        # Create settings without bypass permissions
        basic_settings = {
            "permissions": {"allow": ["Bash"], "deny": [], "defaultMode": "askPermissions"}
        }

        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(basic_settings, f)

        result = self.manager.should_use_uvx_template(settings_path)
        self.assertTrue(result, "Should use UVX template when bypass permissions not enabled")

    def test_should_not_use_uvx_template_with_bypass_permissions(self):
        """Test UVX template is not used when bypass permissions already exist."""
        settings_path = self.temp_dir / "settings.json"

        # Create settings with bypass permissions
        bypass_settings = {
            "permissions": {
                "allow": ["Bash", "TodoWrite"],
                "deny": [],
                "defaultMode": "bypassPermissions",
            }
        }

        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(bypass_settings, f)

        result = self.manager.should_use_uvx_template(settings_path)
        self.assertFalse(
            result, "Should not use UVX template when bypass permissions already enabled"
        )

    def test_create_uvx_settings_fresh_installation(self):
        """Test creating UVX settings for fresh installation."""
        settings_path = self.temp_dir / "settings.json"

        result = self.manager.create_uvx_settings(settings_path, preserve_existing=False)
        self.assertTrue(result, "Should successfully create UVX settings")
        self.assertTrue(settings_path.exists(), "Settings file should be created")

        # Verify settings content
        with open(settings_path, encoding="utf-8") as f:
            settings = json.load(f)

        self.assertEqual(settings["permissions"]["defaultMode"], "bypassPermissions")
        self.assertIn("Bash", settings["permissions"]["allow"])
        self.assertIn("TodoWrite", settings["permissions"]["allow"])
        self.assertIn("WebFetch", settings["permissions"]["allow"])

    def test_create_uvx_settings_preserves_existing(self):
        """Test that existing settings are backed up when creating UVX settings."""
        settings_path = self.temp_dir / "settings.json"
        backup_path = self.temp_dir / "settings.json.backup.uvx"

        # Create original settings
        original_settings = {"test": "original"}
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(original_settings, f)

        result = self.manager.create_uvx_settings(settings_path, preserve_existing=True)
        self.assertTrue(result, "Should successfully create UVX settings")
        self.assertTrue(backup_path.exists(), "Backup should be created")

        # Verify backup contains original settings
        with open(backup_path, encoding="utf-8") as f:
            backup_settings = json.load(f)

        self.assertEqual(
            backup_settings, original_settings, "Backup should contain original settings"
        )

    def test_merge_with_existing_settings(self):
        """Test merging UVX template with existing user settings."""
        settings_path = self.temp_dir / "settings.json"

        # Existing user settings
        existing_settings = {
            "permissions": {"allow": ["CustomTool"], "deny": [], "defaultMode": "askPermissions"},
            "customProperty": "userValue",
            "hooks": {"CustomHook": [{"type": "command", "command": "custom.py"}]},
        }

        result = self.manager.merge_with_existing_settings(settings_path, existing_settings)
        self.assertTrue(result, "Should successfully merge settings")
        self.assertTrue(settings_path.exists(), "Merged settings file should exist")

        # Verify merged settings
        with open(settings_path, encoding="utf-8") as f:
            merged_settings = json.load(f)

        # Should have UVX permissions (bypass mode)
        self.assertEqual(merged_settings["permissions"]["defaultMode"], "bypassPermissions")

        # Should include both custom and UVX tools
        allow_list = merged_settings["permissions"]["allow"]
        self.assertIn("CustomTool", allow_list)  # User's tool preserved
        self.assertIn("Bash", allow_list)  # UVX tool added
        self.assertIn("TodoWrite", allow_list)  # UVX tool added

        # Should preserve user's custom property
        self.assertEqual(merged_settings["customProperty"], "userValue")

        # Should have both custom and amplihack hooks
        hooks = merged_settings["hooks"]
        self.assertIn("CustomHook", hooks)  # User's hook preserved
        self.assertIn("SessionStart", hooks)  # Amplihack hook added

    def test_get_template_settings(self):
        """Test getting template settings dictionary."""
        template = self.manager.get_template_settings()

        self.assertIsNotNone(template, "Template should be loaded successfully")
        self.assertIn("permissions", template)
        self.assertIn("hooks", template)
        self.assertEqual(template["permissions"]["defaultMode"], "bypassPermissions")

    def test_invalid_json_handling(self):
        """Test handling of corrupted settings.json files."""
        settings_path = self.temp_dir / "settings.json"

        # Create invalid JSON file
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json")

        result = self.manager.should_use_uvx_template(settings_path)
        self.assertTrue(result, "Should use UVX template when existing settings are corrupted")


class TestUVXSettingsIntegration(unittest.TestCase):
    """Integration tests for UVX settings functionality."""

    def test_fresh_uvx_installation_flow(self):
        """Test complete flow for fresh UVX installation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            settings_path = temp_path / ".claude" / "settings.json"

            manager = UVXSettingsManager()

            # Step 1: Check if UVX template should be used (fresh install)
            should_use_template = manager.should_use_uvx_template(settings_path)
            self.assertTrue(should_use_template, "Should use UVX template for fresh installation")

            # Step 2: Create UVX settings
            success = manager.create_uvx_settings(settings_path)
            self.assertTrue(success, "Should create UVX settings successfully")

            # Step 3: Verify settings work as expected
            with open(settings_path, encoding="utf-8") as f:
                final_settings = json.load(f)

            # Should have bypass permissions enabled
            self.assertEqual(final_settings["permissions"]["defaultMode"], "bypassPermissions")

            # Should have comprehensive tool allowlist
            expected_tools = [
                "Bash",
                "TodoWrite",
                "WebFetch",
                "WebSearch",
                "Grep",
                "Glob",
                "Read",
                "Edit",
            ]
            allow_list = final_settings["permissions"]["allow"]
            for tool in expected_tools:
                self.assertIn(tool, allow_list, f"{tool} should be in allow list")

            # Should have amplihack hooks configured
            hooks = final_settings["hooks"]
            self.assertIn("SessionStart", hooks)
            self.assertIn("Stop", hooks)
            self.assertIn("PostToolUse", hooks)

    def test_existing_user_settings_preservation(self):
        """Test that existing user customizations are preserved during UVX setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            settings_path = temp_path / ".claude" / "settings.json"

            # Create existing user settings
            user_settings = {
                "permissions": {
                    "allow": ["UserTool1", "UserTool2"],
                    "deny": ["DangerousTool"],
                    "defaultMode": "askPermissions",
                    "additionalDirectories": ["user-dir"],
                },
                "userCustomization": "important-value",
            }

            settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(user_settings, f)

            manager = UVXSettingsManager()

            # Merge with UVX template
            success = manager.merge_with_existing_settings(settings_path, user_settings)
            self.assertTrue(success, "Should merge settings successfully")

            # Verify preservation of user customizations
            with open(settings_path, encoding="utf-8") as f:
                merged_settings = json.load(f)

            # Should preserve user's custom property
            self.assertEqual(merged_settings["userCustomization"], "important-value")

            # Should have bypass permissions (UVX override)
            self.assertEqual(merged_settings["permissions"]["defaultMode"], "bypassPermissions")

            # Should merge allow lists
            allow_list = merged_settings["permissions"]["allow"]
            self.assertIn("UserTool1", allow_list)  # User tool preserved
            self.assertIn("UserTool2", allow_list)  # User tool preserved
            self.assertIn("Bash", allow_list)  # UVX tool added


if __name__ == "__main__":
    unittest.main()
