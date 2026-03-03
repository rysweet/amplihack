"""Tests for settings_migrator deduplication and pattern coverage.

Tests the hook deduplication logic and expanded AMPLIHACK_HOOK_PATTERNS
added to fix issue #2834 (duplicate hook execution).

Testing pyramid: 100% unit tests (mocked I/O, fast execution).
"""

import json
import sys
from pathlib import Path

# Add hooks directory to path for import
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks"
    ),
)

from settings_migrator import SettingsMigrator


class TestDeduplicateHooks:
    """Unit tests for SettingsMigrator.deduplicate_hooks() static method."""

    def test_removes_exact_duplicate_entries(self):
        settings = {
            "hooks": {
                "UserPromptSubmit": [
                    {"hooks": [{"command": "foo.py", "type": "command"}]},
                    {"hooks": [{"command": "foo.py", "type": "command"}]},
                ]
            }
        }
        removed = SettingsMigrator.deduplicate_hooks(settings)
        assert removed == 1
        assert len(settings["hooks"]["UserPromptSubmit"]) == 1

    def test_preserves_distinct_entries(self):
        settings = {
            "hooks": {
                "UserPromptSubmit": [
                    {"hooks": [{"command": "foo.py", "type": "command"}]},
                    {"hooks": [{"command": "bar.py", "type": "command"}]},
                ]
            }
        }
        removed = SettingsMigrator.deduplicate_hooks(settings)
        assert removed == 0
        assert len(settings["hooks"]["UserPromptSubmit"]) == 2

    def test_handles_multiple_hook_types(self):
        settings = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"command": "start.py"}]},
                    {"hooks": [{"command": "start.py"}]},
                ],
                "Stop": [
                    {"hooks": [{"command": "stop.py"}]},
                ],
            }
        }
        removed = SettingsMigrator.deduplicate_hooks(settings)
        assert removed == 1
        assert len(settings["hooks"]["SessionStart"]) == 1
        assert len(settings["hooks"]["Stop"]) == 1

    def test_handles_empty_hooks(self):
        settings = {"hooks": {}}
        removed = SettingsMigrator.deduplicate_hooks(settings)
        assert removed == 0

    def test_handles_no_hooks_key(self):
        settings = {"permissions": {}}
        removed = SettingsMigrator.deduplicate_hooks(settings)
        assert removed == 0

    def test_triple_duplicate(self):
        settings = {
            "hooks": {
                "PreToolUse": [
                    {"hooks": [{"command": "check.py"}]},
                    {"hooks": [{"command": "check.py"}]},
                    {"hooks": [{"command": "check.py"}]},
                ]
            }
        }
        removed = SettingsMigrator.deduplicate_hooks(settings)
        assert removed == 2
        assert len(settings["hooks"]["PreToolUse"]) == 1

    def test_multi_command_config_dedup(self):
        """Two configs with same set of commands are duplicates."""
        settings = {
            "hooks": {
                "UserPromptSubmit": [
                    {"hooks": [{"command": "a.py"}, {"command": "b.py"}]},
                    {"hooks": [{"command": "a.py"}, {"command": "b.py"}]},
                ]
            }
        }
        removed = SettingsMigrator.deduplicate_hooks(settings)
        assert removed == 1


class TestAmplihackHookPatterns:
    """Tests that AMPLIHACK_HOOK_PATTERNS covers all known hook scripts."""

    EXPECTED_HOOKS = [
        "amplihack/hooks/stop.py",
        "amplihack/hooks/session_start.py",
        "amplihack/hooks/pre_tool_use.py",
        "amplihack/hooks/post_tool_use.py",
        "amplihack/hooks/pre_compact.py",
        "amplihack/hooks/session_end.py",
        "amplihack/hooks/user_prompt_submit.py",
        "amplihack/hooks/workflow_classification_reminder.py",
    ]

    def test_all_expected_patterns_present(self):
        for hook in self.EXPECTED_HOOKS:
            assert hook in SettingsMigrator.AMPLIHACK_HOOK_PATTERNS, f"Missing pattern: {hook}"

    def test_xpia_hooks_not_matched(self):
        """XPIA hooks must NOT be matched — they're security hooks."""
        xpia_commands = [
            "/home/user/.amplihack/.claude/tools/xpia/hooks/session_start.py",
            "/home/user/.amplihack/.claude/tools/xpia/hooks/pre_tool_use.py",
            "/home/user/.amplihack/.claude/tools/xpia/hooks/post_tool_use.py",
        ]
        for cmd in xpia_commands:
            matched = any(p in cmd for p in SettingsMigrator.AMPLIHACK_HOOK_PATTERNS)
            assert not matched, f"XPIA hook should NOT match: {cmd}"

    def test_amplihack_hooks_matched_with_full_paths(self):
        """Full absolute paths should match patterns."""
        full_path_commands = [
            "/home/user/.amplihack/.claude/tools/amplihack/hooks/stop.py",
            "$HOME/.amplihack/.claude/tools/amplihack/hooks/session_start.py",
            "/home/user/.amplihack/.claude/tools/amplihack/hooks/workflow_classification_reminder.py",
            "/home/user/.amplihack/.claude/tools/amplihack/hooks/user_prompt_submit.py",
        ]
        for cmd in full_path_commands:
            matched = any(p in cmd for p in SettingsMigrator.AMPLIHACK_HOOK_PATTERNS)
            assert matched, f"Amplihack hook should match: {cmd}"


class TestAllHookTypes:
    """Tests that ALL_HOOK_TYPES covers all Claude Code hook events."""

    def test_includes_user_prompt_submit(self):
        assert "UserPromptSubmit" in SettingsMigrator.ALL_HOOK_TYPES

    def test_includes_session_end(self):
        assert "SessionEnd" in SettingsMigrator.ALL_HOOK_TYPES

    def test_includes_original_types(self):
        for t in ["SessionStart", "Stop", "PreToolUse", "PostToolUse", "PreCompact"]:
            assert t in SettingsMigrator.ALL_HOOK_TYPES


class TestDetectGlobalAmplihackHooks:
    """Tests for detecting amplihack hooks in global settings."""

    def test_detects_user_prompt_submit_hooks(self, tmp_path):
        """Previously missed: UserPromptSubmit hooks should be detected."""
        global_settings = tmp_path / ".claude" / "settings.json"
        global_settings.parent.mkdir(parents=True)
        global_settings.write_text(
            json.dumps(
                {
                    "hooks": {
                        "UserPromptSubmit": [
                            {
                                "hooks": [
                                    {
                                        "command": "/home/user/.amplihack/.claude/tools/amplihack/hooks/workflow_classification_reminder.py",
                                        "type": "command",
                                    }
                                ]
                            }
                        ]
                    }
                }
            )
        )

        migrator = SettingsMigrator(project_root=tmp_path)
        migrator.global_settings_path = global_settings
        assert migrator.detect_global_amplihack_hooks() is True

    def test_does_not_detect_xpia_only(self, tmp_path):
        """Global settings with only XPIA hooks should return False."""
        global_settings = tmp_path / ".claude" / "settings.json"
        global_settings.parent.mkdir(parents=True)
        global_settings.write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [
                            {
                                "hooks": [
                                    {
                                        "command": "/home/user/.amplihack/.claude/tools/xpia/hooks/session_start.py",
                                        "type": "command",
                                    }
                                ]
                            }
                        ]
                    }
                }
            )
        )

        migrator = SettingsMigrator(project_root=tmp_path)
        migrator.global_settings_path = global_settings
        assert migrator.detect_global_amplihack_hooks() is False
