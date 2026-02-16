"""Tests for legacy hook path migration in settings.py.

This test suite follows TDD methodology - all tests are written BEFORE implementation
and should FAIL initially. Tests validate the migrate_legacy_hook_paths() function
that migrates old hook paths from $HOME/.claude/tools/amplihack/hooks/ to the new
$HOME/.amplihack/.claude/tools/amplihack/hooks/ pattern.

Coverage Strategy (Testing Pyramid - 60% unit):
- Core migration logic (success cases)
- Edge cases (empty, missing, malformed)
- Idempotency (no double migration)
- Integration with ensure_settings_json()
"""

import json

import pytest

from amplihack.settings import migrate_legacy_hook_paths


# Test fixtures
@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Create a temporary home directory for testing."""
    fake_home = tmp_path / "home" / "testuser"
    fake_home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))
    return fake_home


@pytest.fixture
def legacy_settings():
    """Create settings dict with legacy hook paths."""
    return {
        "permissions": {
            "allow": ["Bash", "TodoWrite"],
            "deny": [],
            "defaultMode": "bypassPermissions",
        },
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$HOME/.claude/tools/amplihack/hooks/session_start.py",
                            "timeout": 10,
                        }
                    ]
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$HOME/.claude/tools/amplihack/hooks/stop.py",
                            "timeout": 120,
                        }
                    ]
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$HOME/.claude/tools/amplihack/hooks/post_tool_use.py",
                        }
                    ],
                }
            ],
            "PreCompact": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$HOME/.claude/tools/amplihack/hooks/pre_compact.py",
                            "timeout": 30,
                        }
                    ]
                }
            ],
        },
    }


@pytest.fixture
def modern_settings():
    """Create settings dict with modern hook paths (already migrated)."""
    return {
        "permissions": {
            "allow": ["Bash", "TodoWrite"],
            "deny": [],
            "defaultMode": "bypassPermissions",
        },
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$HOME/.amplihack/.claude/tools/amplihack/hooks/session_start.py",
                            "timeout": 10,
                        }
                    ]
                }
            ],
        },
    }


@pytest.fixture
def mixed_settings():
    """Create settings dict with both legacy and modern paths."""
    return {
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$HOME/.claude/tools/amplihack/hooks/session_start.py",
                            "timeout": 10,
                        }
                    ]
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$HOME/.amplihack/.claude/tools/amplihack/hooks/stop.py",
                            "timeout": 120,
                        }
                    ]
                }
            ],
        },
    }


# Core migration tests
class TestBasicMigration:
    """Test core migration functionality."""

    def test_migrate_single_hook(self, legacy_settings):
        """Test migrating a single legacy hook path."""
        # Arrange
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "$HOME/.claude/tools/amplihack/hooks/session_start.py",
                                "timeout": 10,
                            }
                        ]
                    }
                ]
            }
        }

        # Act
        count = migrate_legacy_hook_paths(settings)

        # Assert
        assert count == 1
        hook_cmd = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        assert hook_cmd == "$HOME/.amplihack/.claude/tools/amplihack/hooks/session_start.py"
        assert ".claude/tools/amplihack" not in hook_cmd or ".amplihack/.claude" in hook_cmd

    def test_migrate_all_hook_types(self, legacy_settings):
        """Test migrating all hook types (SessionStart, Stop, PostToolUse, PreCompact)."""
        # Act
        count = migrate_legacy_hook_paths(legacy_settings)

        # Assert
        assert count == 4  # All 4 legacy hooks should be migrated

        # Verify SessionStart
        session_start_cmd = legacy_settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        assert (
            session_start_cmd == "$HOME/.amplihack/.claude/tools/amplihack/hooks/session_start.py"
        )

        # Verify Stop
        stop_cmd = legacy_settings["hooks"]["Stop"][0]["hooks"][0]["command"]
        assert stop_cmd == "$HOME/.amplihack/.claude/tools/amplihack/hooks/stop.py"

        # Verify PostToolUse
        post_tool_use_cmd = legacy_settings["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
        assert (
            post_tool_use_cmd == "$HOME/.amplihack/.claude/tools/amplihack/hooks/post_tool_use.py"
        )

        # Verify PreCompact
        pre_compact_cmd = legacy_settings["hooks"]["PreCompact"][0]["hooks"][0]["command"]
        assert pre_compact_cmd == "$HOME/.amplihack/.claude/tools/amplihack/hooks/pre_compact.py"

    def test_migrate_preserves_other_properties(self, legacy_settings):
        """Test that migration preserves timeout and other hook properties."""
        # Act
        migrate_legacy_hook_paths(legacy_settings)

        # Assert - check timeouts are preserved
        session_start_hook = legacy_settings["hooks"]["SessionStart"][0]["hooks"][0]
        assert session_start_hook["timeout"] == 10
        assert session_start_hook["type"] == "command"

        stop_hook = legacy_settings["hooks"]["Stop"][0]["hooks"][0]
        assert stop_hook["timeout"] == 120
        assert stop_hook["type"] == "command"


# Idempotency tests
class TestIdempotency:
    """Test that migration is idempotent (safe to run multiple times)."""

    def test_already_migrated_paths_unchanged(self, modern_settings):
        """Test that already-migrated paths are not modified."""
        # Arrange
        original_cmd = modern_settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]

        # Act
        count = migrate_legacy_hook_paths(modern_settings)

        # Assert
        assert count == 0  # No migrations should occur
        new_cmd = modern_settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        assert new_cmd == original_cmd

    def test_migrate_twice_same_result(self, legacy_settings):
        """Test that migrating twice produces the same result as migrating once."""
        # Arrange
        import copy

        # Act - First migration
        first_count = migrate_legacy_hook_paths(legacy_settings)
        state_after_first_run = copy.deepcopy(legacy_settings)

        # Act - Second migration
        second_count = migrate_legacy_hook_paths(legacy_settings)

        # Assert
        assert first_count > 0  # First run should migrate
        assert second_count == 0  # Second run should be no-op
        # Settings should be identical after both runs
        assert legacy_settings == state_after_first_run  # Second run didn't change anything

    def test_mixed_paths_only_migrates_legacy(self, mixed_settings):
        """Test that mixed settings only migrate legacy paths, leaving modern paths unchanged."""
        # Arrange
        original_stop_cmd = mixed_settings["hooks"]["Stop"][0]["hooks"][0]["command"]

        # Act
        count = migrate_legacy_hook_paths(mixed_settings)

        # Assert
        assert count == 1  # Only SessionStart should be migrated

        # Modern path unchanged
        stop_cmd = mixed_settings["hooks"]["Stop"][0]["hooks"][0]["command"]
        assert stop_cmd == original_stop_cmd
        assert ".amplihack/.claude" in stop_cmd

        # Legacy path migrated
        session_start_cmd = mixed_settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        assert ".amplihack/.claude" in session_start_cmd


# Edge case tests
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_settings(self):
        """Test migration with empty settings dict."""
        # Arrange
        settings = {}

        # Act
        count = migrate_legacy_hook_paths(settings)

        # Assert
        assert count == 0

    def test_missing_hooks_section(self):
        """Test migration when hooks section is missing."""
        # Arrange
        settings = {
            "permissions": {
                "allow": ["Bash"],
            }
        }

        # Act
        count = migrate_legacy_hook_paths(settings)

        # Assert
        assert count == 0

    def test_empty_hooks_section(self):
        """Test migration when hooks section is empty."""
        # Arrange
        settings = {"hooks": {}}

        # Act
        count = migrate_legacy_hook_paths(settings)

        # Assert
        assert count == 0

    def test_hook_without_command_field(self):
        """Test migration handles hooks missing command field gracefully."""
        # Arrange
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                # Missing command field
                                "timeout": 10,
                            }
                        ]
                    }
                ]
            }
        }

        # Act
        count = migrate_legacy_hook_paths(settings)

        # Assert
        assert count == 0  # Should handle gracefully

    def test_malformed_hook_structure(self):
        """Test migration handles malformed hook structures gracefully."""
        # Arrange
        settings = {
            "hooks": {
                "SessionStart": "not a list",  # Malformed
            }
        }

        # Act
        count = migrate_legacy_hook_paths(settings)

        # Assert
        assert count == 0  # Should handle gracefully without crashing

    def test_non_amplihack_hooks_unchanged(self):
        """Test that non-amplihack hook paths are not modified."""
        # Arrange
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/usr/local/bin/custom_hook.sh",
                                "timeout": 10,
                            }
                        ]
                    }
                ]
            }
        }
        original_cmd = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]

        # Act
        count = migrate_legacy_hook_paths(settings)

        # Assert
        assert count == 0
        new_cmd = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        assert new_cmd == original_cmd


# Integration tests
class TestIntegration:
    """Test integration with ensure_settings_json()."""

    def test_ensure_settings_json_migrates_legacy_paths(self, temp_home, monkeypatch):
        """Test that ensure_settings_json() automatically migrates legacy paths."""
        # Arrange
        claude_dir = temp_home / ".claude"
        claude_dir.mkdir(parents=True)
        settings_path = claude_dir / "settings.json"

        # Create settings with legacy paths
        legacy_settings_dict = {
            "permissions": {
                "allow": ["Bash"],
                "defaultMode": "bypassPermissions",
            },
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "$HOME/.claude/tools/amplihack/hooks/session_start.py",
                                "timeout": 10,
                            }
                        ]
                    }
                ]
            },
        }
        settings_path.write_text(json.dumps(legacy_settings_dict, indent=2))

        # Mock to avoid interactive prompts and actual hook installation
        monkeypatch.setenv("AMPLIHACK_YES", "1")

        # Mock the module-level constants that ensure_settings_json uses
        import amplihack.settings

        monkeypatch.setattr(amplihack.settings, "CLAUDE_DIR", str(claude_dir))
        monkeypatch.setattr(amplihack.settings, "HOME", str(temp_home))

        # Act
        from amplihack.settings import ensure_settings_json

        result = ensure_settings_json()

        # Assert
        assert result is True

        # Read settings and verify migration occurred
        updated_settings = json.loads(settings_path.read_text())
        session_start_cmd = updated_settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]

        # Verify migration succeeded - should contain .amplihack/.claude pattern
        assert "/.amplihack/.claude/tools/amplihack" in session_start_cmd
        # Original legacy path used $HOME/.claude/tools/ which should be gone
        assert not session_start_cmd.startswith("$HOME/.claude/tools/")


# Path pattern tests
class TestPathPatterns:
    """Test detection and transformation of various path patterns."""

    def test_detects_legacy_pattern(self):
        """Test that legacy pattern $HOME/.claude/tools/amplihack/hooks/ is detected."""
        # Arrange
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "$HOME/.claude/tools/amplihack/hooks/session_start.py",
                            }
                        ]
                    }
                ]
            }
        }

        # Act
        count = migrate_legacy_hook_paths(settings)

        # Assert
        assert count == 1

    def test_transforms_to_modern_pattern(self):
        """Test that transformation to $HOME/.amplihack/.claude/tools/amplihack/hooks/ is correct."""
        # Arrange
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "$HOME/.claude/tools/amplihack/hooks/session_start.py",
                            }
                        ]
                    }
                ]
            }
        }

        # Act
        migrate_legacy_hook_paths(settings)

        # Assert
        new_cmd = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        expected = "$HOME/.amplihack/.claude/tools/amplihack/hooks/session_start.py"
        assert new_cmd == expected

    def test_handles_absolute_paths(self, temp_home):
        """Test migration with absolute paths instead of $HOME variable."""
        # Arrange
        legacy_path = str(
            temp_home / ".claude" / "tools" / "amplihack" / "hooks" / "session_start.py"
        )
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": legacy_path,
                            }
                        ]
                    }
                ]
            }
        }

        # Act
        count = migrate_legacy_hook_paths(settings)

        # Assert
        assert count == 1
        new_cmd = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        expected_path = str(
            temp_home
            / ".amplihack"
            / ".claude"
            / "tools"
            / "amplihack"
            / "hooks"
            / "session_start.py"
        )
        assert new_cmd == expected_path
