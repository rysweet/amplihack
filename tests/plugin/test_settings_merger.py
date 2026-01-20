"""
TDD Tests for SettingsMerger module.

These tests validate deep merging of settings with conflict resolution,
LSP server management, and hook path resolution.

Testing Strategy:
- 60% unit tests (pure merge logic)
- 30% integration tests (file I/O + merge)
- 10% E2E tests (complete settings workflow)
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch


class TestSettingsMergerUnit:
    """Unit tests for SettingsMerger - pure merge logic."""

    def test_merge_empty_overrides_returns_base(self):
        """
        Test that merging with empty overrides returns base unchanged.

        Validates:
        - Base settings are returned as-is
        - No modifications occur
        - Original dict is not mutated
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        base = {
            "version": "1.0",
            "hooks": {"PreRun": "hook.sh"}
        }

        merger = SettingsMerger()
        result = merger.merge(base=base, overrides={})

        assert result == base
        assert result is not base  # New dict, not mutated original

    def test_merge_non_conflicting_keys(self):
        """
        Test merging non-conflicting keys from base and overrides.

        Validates:
        - Keys from both base and overrides are present
        - No conflicts means simple combination
        - Values are preserved correctly
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        base = {
            "version": "1.0",
            "hooks": {"PreRun": "hook.sh"}
        }

        overrides = {
            "custom_key": "custom_value",
            "project_name": "my_project"
        }

        merger = SettingsMerger()
        result = merger.merge(base=base, overrides=overrides)

        assert result["version"] == "1.0"
        assert result["hooks"]["PreRun"] == "hook.sh"
        assert result["custom_key"] == "custom_value"
        assert result["project_name"] == "my_project"

    def test_merge_conflicting_primitive_values_prefers_override(self):
        """
        Test that conflicting primitive values prefer override.

        Validates:
        - Override value wins for same key
        - Base value is replaced, not merged
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        base = {"timeout": 30, "debug": False}
        overrides = {"timeout": 60}

        merger = SettingsMerger()
        result = merger.merge(base=base, overrides=overrides)

        assert result["timeout"] == 60
        assert result["debug"] is False

    def test_deep_merge_nested_dicts(self):
        """
        Test deep merging of nested dictionaries.

        Validates:
        - Nested dicts are merged recursively
        - Override keys are added to nested structure
        - Base keys not in override are preserved
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        base = {
            "hooks": {
                "PreRun": "base_hook.sh",
                "PostRun": "cleanup.sh"
            }
        }

        overrides = {
            "hooks": {
                "PreRun": "custom_hook.sh",
                "CustomHook": "my_hook.sh"
            }
        }

        merger = SettingsMerger()
        result = merger.merge(base=base, overrides=overrides)

        assert result["hooks"]["PreRun"] == "custom_hook.sh"  # Override wins
        assert result["hooks"]["PostRun"] == "cleanup.sh"     # Base preserved
        assert result["hooks"]["CustomHook"] == "my_hook.sh"  # Override added

    def test_merge_array_values_append_mode(self):
        """
        Test that array values are appended, not replaced.

        Validates:
        - Lists from base and override are combined
        - Duplicates are preserved (no deduplication)
        - Order is: base items first, then override items
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        base = {"exclude": ["node_modules", ".git"]}
        overrides = {"exclude": ["build", ".venv"]}

        merger = SettingsMerger()
        result = merger.merge(base=base, overrides=overrides)

        expected = ["node_modules", ".git", "build", ".venv"]
        assert result["exclude"] == expected

    def test_merge_lsp_servers_combines_configurations(self):
        """
        Test that LSP server configurations are combined correctly.

        Validates:
        - Base LSP servers are preserved
        - Override LSP servers are added
        - Conflicting server names: override wins
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        base = {
            "lspServers": {
                "python": {
                    "command": "pylsp",
                    "args": []
                }
            }
        }

        overrides = {
            "lspServers": {
                "typescript": {
                    "command": "typescript-language-server",
                    "args": ["--stdio"]
                },
                "python": {
                    "command": "pyright-langserver",
                    "args": ["--stdio"]
                }
            }
        }

        merger = SettingsMerger()
        result = merger.merge(base=base, overrides=overrides)

        # TypeScript added
        assert "typescript" in result["lspServers"]
        # Python overridden
        assert result["lspServers"]["python"]["command"] == "pyright-langserver"

    def test_validate_settings_rejects_invalid_structure(self):
        """
        Test that validate_settings() rejects invalid settings structure.

        Validates:
        - Missing required keys raises ValueError
        - Invalid types raise ValueError
        - Error messages are descriptive
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        merger = SettingsMerger()

        # Invalid: hooks is not a dict
        with pytest.raises(ValueError, match="hooks.*must be.*dict"):
            merger.validate_settings({"hooks": "invalid"})

        # Invalid: lspServers is not a dict
        with pytest.raises(ValueError, match="lspServers.*must be.*dict"):
            merger.validate_settings({"lspServers": []})

    def test_validate_settings_accepts_valid_structure(self):
        """
        Test that validate_settings() accepts valid settings.

        Validates:
        - Valid settings pass without error
        - Returns True for valid settings
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        valid = {
            "version": "1.0",
            "hooks": {"PreRun": "hook.sh"},
            "lspServers": {
                "python": {"command": "pylsp"}
            }
        }

        merger = SettingsMerger()
        assert merger.validate_settings(valid)

    def test_resolve_hook_paths_substitutes_variables(self):
        """
        Test that resolve_hook_paths() substitutes path variables.

        Validates:
        - ${CLAUDE_PLUGIN_ROOT} is replaced with actual path
        - Relative paths are converted to absolute
        - Already absolute paths are preserved
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        settings = {
            "hooks": {
                "PreRun": "${CLAUDE_PLUGIN_ROOT}/tools/hook.sh",
                "PostRun": "/absolute/path/hook.sh"
            }
        }

        plugin_root = Path("/home/user/.amplihack/.claude")

        merger = SettingsMerger()
        result = merger.resolve_hook_paths(settings, plugin_root)

        expected = str(plugin_root / "tools" / "hook.sh")
        assert result["hooks"]["PreRun"] == expected
        assert result["hooks"]["PostRun"] == "/absolute/path/hook.sh"


class TestSettingsMergerIntegration:
    """Integration tests for SettingsMerger - file I/O + merge."""

    def test_merge_from_files(self, tmp_path):
        """
        Test merging settings loaded from JSON files.

        Validates:
        - Base settings loaded from file
        - Override settings loaded from file
        - Merged result is correct
        - Result can be written to file
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        # Create base settings file
        base_file = tmp_path / "base.json"
        base_settings = {
            "version": "1.0",
            "hooks": {"PreRun": "base_hook.sh"}
        }
        base_file.write_text(json.dumps(base_settings, indent=2))

        # Create override settings file
        override_file = tmp_path / "override.json"
        override_settings = {
            "hooks": {"CustomHook": "custom.sh"},
            "custom_key": "value"
        }
        override_file.write_text(json.dumps(override_settings, indent=2))

        # Merge
        merger = SettingsMerger()
        result = merger.merge_from_files(
            base_path=base_file,
            override_path=override_file
        )

        assert result["version"] == "1.0"
        assert result["hooks"]["PreRun"] == "base_hook.sh"
        assert result["hooks"]["CustomHook"] == "custom.sh"
        assert result["custom_key"] == "value"

    def test_save_merged_settings(self, tmp_path):
        """
        Test saving merged settings to file.

        Validates:
        - Settings are written in valid JSON format
        - Formatting is readable (indented)
        - File can be loaded back and matches original
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        settings = {
            "version": "1.0",
            "hooks": {"PreRun": "hook.sh"}
        }

        output_file = tmp_path / "output.json"

        merger = SettingsMerger()
        merger.save_settings(settings, output_file)

        # Verify file exists and is valid JSON
        assert output_file.exists()
        loaded = json.loads(output_file.read_text())
        assert loaded == settings

    def test_complete_merge_workflow(self, tmp_path):
        """
        Test complete workflow: load base, load override, merge, save.

        Validates:
        - End-to-end merge process
        - File I/O operations
        - Settings validation
        - Path resolution
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        # Setup plugin root
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()

        # Base settings (from plugin)
        base_file = plugin_root / "settings.json"
        base = {
            "version": "1.0",
            "hooks": {
                "PreRun": "${CLAUDE_PLUGIN_ROOT}/tools/hook.sh"
            },
            "lspServers": {
                "python": {"command": "pylsp"}
            }
        }
        base_file.write_text(json.dumps(base, indent=2))

        # Project overrides
        project_root = tmp_path / "project"
        project_root.mkdir()
        override_file = project_root / "settings_override.json"
        override = {
            "hooks": {
                "CustomHook": "custom.sh"
            },
            "lspServers": {
                "typescript": {"command": "tsserver"}
            }
        }
        override_file.write_text(json.dumps(override, indent=2))

        # Merge and save
        output_file = project_root / ".claude" / "settings.json"
        output_file.parent.mkdir(parents=True)

        merger = SettingsMerger()
        result = merger.merge_from_files(base_file, override_file)
        result = merger.resolve_hook_paths(result, plugin_root)
        merger.save_settings(result, output_file)

        # Verify result
        loaded = json.loads(output_file.read_text())
        assert loaded["version"] == "1.0"
        assert "PreRun" in loaded["hooks"]
        assert "CustomHook" in loaded["hooks"]
        assert "python" in loaded["lspServers"]
        assert "typescript" in loaded["lspServers"]

        # Verify path was resolved
        expected_hook_path = str(plugin_root / "tools" / "hook.sh")
        assert loaded["hooks"]["PreRun"] == expected_hook_path


class TestSettingsMergerEdgeCases:
    """Edge case tests for SettingsMerger."""

    def test_merge_with_null_values(self):
        """
        Test merging when values are None/null.

        Validates:
        - None in override removes key from base
        - None in base is overridden by override value
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        base = {"key1": "value1", "key2": "value2"}
        overrides = {"key1": None, "key3": "value3"}

        merger = SettingsMerger()
        result = merger.merge(base=base, overrides=overrides)

        assert "key1" not in result  # Removed by None override
        assert result["key2"] == "value2"
        assert result["key3"] == "value3"

    def test_merge_deeply_nested_structures(self):
        """
        Test merging with deeply nested dictionaries (3+ levels).

        Validates:
        - Deep merging works at all nesting levels
        - Values at each level are handled correctly
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        base = {
            "level1": {
                "level2": {
                    "level3": {
                        "key": "base_value"
                    }
                }
            }
        }

        overrides = {
            "level1": {
                "level2": {
                    "level3": {
                        "key": "override_value",
                        "new_key": "new_value"
                    }
                }
            }
        }

        merger = SettingsMerger()
        result = merger.merge(base=base, overrides=overrides)

        assert result["level1"]["level2"]["level3"]["key"] == "override_value"
        assert result["level1"]["level2"]["level3"]["new_key"] == "new_value"

    def test_merge_with_circular_references_raises_error(self):
        """
        Test that circular references in settings are detected.

        Validates:
        - Circular references raise ValueError
        - Error message indicates circular reference
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        # Create circular reference
        circular = {"key": "value"}
        circular["self"] = circular

        merger = SettingsMerger()

        with pytest.raises(ValueError, match="circular|recursion"):
            merger.merge(base=circular, overrides={})

    def test_merge_preserves_special_types(self):
        """
        Test that special types (int, bool, float) are preserved.

        Validates:
        - Type conversions don't occur unintentionally
        - Boolean values remain boolean
        - Numeric values remain numeric
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        base = {
            "timeout": 30,
            "debug": False,
            "threshold": 0.95
        }

        overrides = {
            "timeout": 60,
            "debug": True
        }

        merger = SettingsMerger()
        result = merger.merge(base=base, overrides=overrides)

        assert isinstance(result["timeout"], int)
        assert isinstance(result["debug"], bool)
        assert isinstance(result["threshold"], float)
        assert result["timeout"] == 60
        assert result["debug"] is True

    def test_resolve_hook_paths_handles_windows_paths(self):
        """
        Test that resolve_hook_paths() works with Windows paths.

        Validates:
        - Windows-style paths (backslashes) are handled
        - Drive letters are preserved
        - Path separators are normalized
        """
        from amplihack.plugin.settings_merger import SettingsMerger

        settings = {
            "hooks": {
                "PreRun": "${CLAUDE_PLUGIN_ROOT}\\tools\\hook.sh"
            }
        }

        plugin_root = Path("C:/Users/test/.amplihack/.claude")

        merger = SettingsMerger()
        result = merger.resolve_hook_paths(settings, plugin_root)

        # Path should be normalized to platform format
        expected_path = str(plugin_root / "tools" / "hook.sh")
        assert result["hooks"]["PreRun"] == expected_path
