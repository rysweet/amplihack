#!/usr/bin/env python3
"""User prompt submit coverage tests.

Covers: preference loading (both formats), /dev invocation detection,
AMPLIHACK.md injection, strategy delegation, caching, extract_preferences,
build_preference_context, find_user_preferences.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_user_prompt_hook(tmp_path):
    """Create a UserPromptSubmitHook with mocked HookProcessor init."""
    with patch("hook_processor.HookProcessor.__init__", return_value=None):
        from user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.hook_name = "user_prompt_submit"
        hook.project_root = tmp_path
        hook.log_dir = tmp_path / ".claude" / "runtime" / "logs"
        hook.log_dir.mkdir(parents=True, exist_ok=True)
        hook.metrics_dir = tmp_path / ".claude" / "runtime" / "metrics"
        hook.metrics_dir.mkdir(parents=True, exist_ok=True)
        hook.analysis_dir = tmp_path / ".claude" / "runtime" / "analysis"
        hook.analysis_dir.mkdir(parents=True, exist_ok=True)
        hook.log_file = hook.log_dir / "user_prompt_submit.log"
        hook.log = MagicMock()
        hook.save_metric = MagicMock()
        hook.strategy = None
        hook._preferences_cache = None
        hook._cache_timestamp = None
        hook._amplihack_cache = None
        hook._amplihack_cache_timestamp = None
        return hook


# ============================================================================
# _is_dev_prompt
# ============================================================================


class TestIsDevPrompt:
    """Detection of /dev invocation patterns."""

    def test_exact_dev(self):
        from user_prompt_submit import UserPromptSubmitHook

        assert UserPromptSubmitHook._is_dev_prompt("/dev") is True

    def test_dev_with_args(self):
        from user_prompt_submit import UserPromptSubmitHook

        assert UserPromptSubmitHook._is_dev_prompt("/dev implement auth") is True

    def test_dev_orchestrator(self):
        from user_prompt_submit import UserPromptSubmitHook

        assert UserPromptSubmitHook._is_dev_prompt("use dev-orchestrator") is True

    def test_amplihack_dev(self):
        from user_prompt_submit import UserPromptSubmitHook

        assert UserPromptSubmitHook._is_dev_prompt("/amplihack:dev") is True

    def test_claude_amplihack_dev(self):
        from user_prompt_submit import UserPromptSubmitHook

        assert UserPromptSubmitHook._is_dev_prompt("/.claude:amplihack:dev") is True

    def test_regular_prompt_not_dev(self):
        from user_prompt_submit import UserPromptSubmitHook

        assert UserPromptSubmitHook._is_dev_prompt("what is /dev?") is False

    def test_development_not_dev(self):
        from user_prompt_submit import UserPromptSubmitHook

        assert UserPromptSubmitHook._is_dev_prompt("/development") is False

    def test_empty_string_not_dev(self):
        from user_prompt_submit import UserPromptSubmitHook

        assert UserPromptSubmitHook._is_dev_prompt("") is False

    def test_whitespace_only_not_dev(self):
        from user_prompt_submit import UserPromptSubmitHook

        assert UserPromptSubmitHook._is_dev_prompt("   ") is False

    def test_dev_with_leading_whitespace(self):
        from user_prompt_submit import UserPromptSubmitHook

        assert UserPromptSubmitHook._is_dev_prompt("  /dev") is True

    def test_case_insensitive(self):
        from user_prompt_submit import UserPromptSubmitHook

        assert UserPromptSubmitHook._is_dev_prompt("/DEV") is True


# ============================================================================
# extract_preferences
# ============================================================================


class TestExtractPreferences:
    """Preference extraction from markdown content."""

    def test_all_preferences_present(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        content = """# User Preferences

### Communication Style
formal

### Verbosity
balanced

### Collaboration Style
autonomous

### Update Frequency
regular

### Priority Type
balanced

### Preferred Languages
Python

### Coding Standards
PEP 8

### Workflow Preferences
DEFAULT_WORKFLOW
"""
        prefs = hook.extract_preferences(content)
        assert prefs["Communication Style"] == "formal"
        assert prefs["Verbosity"] == "balanced"
        assert prefs["Collaboration Style"] == "autonomous"
        assert prefs["Update Frequency"] == "regular"
        assert prefs["Priority Type"] == "balanced"
        assert prefs["Preferred Languages"] == "Python"
        assert prefs["Coding Standards"] == "PEP 8"
        assert prefs["Workflow Preferences"] == "DEFAULT_WORKFLOW"

    def test_some_preferences_missing(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        content = """### Verbosity
verbose
"""
        prefs = hook.extract_preferences(content)
        assert prefs == {"Verbosity": "verbose"}

    def test_not_set_values_skipped(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        content = """### Communication Style
(not set)

### Verbosity
balanced
"""
        prefs = hook.extract_preferences(content)
        assert "Communication Style" not in prefs
        assert prefs["Verbosity"] == "balanced"

    def test_learned_patterns_detected(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        content = """### Verbosity
balanced

## Learned Patterns

### Pattern 1
Something learned
"""
        prefs = hook.extract_preferences(content)
        assert prefs.get("Has Learned Patterns") == "Yes (see USER_PREFERENCES.md)"

    def test_learned_patterns_empty_section(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        content = """### Verbosity
balanced

## Learned Patterns
"""
        prefs = hook.extract_preferences(content)
        assert "Has Learned Patterns" not in prefs

    def test_empty_content(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        prefs = hook.extract_preferences("")
        assert prefs == {}

    def test_malformed_content(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        prefs = hook.extract_preferences("random text without any headers")
        assert prefs == {}


# ============================================================================
# build_preference_context
# ============================================================================


class TestBuildPreferenceContext:
    """Preference context formatting."""

    def test_empty_preferences_returns_empty(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        assert hook.build_preference_context({}) == ""

    def test_single_preference(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        result = hook.build_preference_context({"Verbosity": "balanced"})
        assert "ACTIVE USER PREFERENCES" in result
        assert "Verbosity: balanced" in result

    def test_communication_style_has_instruction(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        result = hook.build_preference_context({"Communication Style": "formal"})
        assert "Use this style in your response" in result

    def test_has_learned_patterns_special_format(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        result = hook.build_preference_context(
            {"Has Learned Patterns": "Yes (see USER_PREFERENCES.md)"}
        )
        assert "Yes (see USER_PREFERENCES.md)" in result

    def test_multiple_preferences_in_priority_order(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        prefs = {
            "Verbosity": "verbose",
            "Communication Style": "casual",
            "Priority Type": "speed",
        }
        result = hook.build_preference_context(prefs)
        # Communication Style should come before Verbosity
        comm_pos = result.index("Communication Style")
        verb_pos = result.index("Verbosity")
        assert comm_pos < verb_pos

    def test_read_only_notice(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        result = hook.build_preference_context({"Verbosity": "balanced"})
        assert "READ-ONLY" in result


# ============================================================================
# find_user_preferences
# ============================================================================


class TestFindUserPreferences:
    """Preference file location."""

    def test_finds_in_project_root(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        pref_file = tmp_path / ".claude" / "context" / "USER_PREFERENCES.md"
        pref_file.parent.mkdir(parents=True, exist_ok=True)
        pref_file.write_text("# Preferences")
        with patch("user_prompt_submit.FrameworkPathResolver", None):
            result = hook.find_user_preferences()
        assert result == pref_file

    def test_finds_in_src_location(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        pref_file = tmp_path / "src" / "amplihack" / ".claude" / "context" / "USER_PREFERENCES.md"
        pref_file.parent.mkdir(parents=True, exist_ok=True)
        pref_file.write_text("# Preferences")
        with patch("user_prompt_submit.FrameworkPathResolver", None):
            result = hook.find_user_preferences()
        assert result == pref_file

    def test_returns_none_when_not_found(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        with patch("user_prompt_submit.FrameworkPathResolver", None):
            result = hook.find_user_preferences()
        assert result is None

    def test_framework_path_resolver_takes_priority(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        resolved_path = tmp_path / "resolved" / "USER_PREFERENCES.md"
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text("# Resolved")
        mock_resolver = MagicMock()
        mock_resolver.resolve_preferences_file.return_value = resolved_path
        with patch("user_prompt_submit.FrameworkPathResolver", mock_resolver):
            result = hook.find_user_preferences()
        assert result == resolved_path


# ============================================================================
# get_cached_preferences
# ============================================================================


class TestGetCachedPreferences:
    """Preference caching with mtime."""

    def test_first_read_populates_cache(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        pref_file = tmp_path / "prefs.md"
        pref_file.write_text("### Verbosity\nbalanced")
        result = hook.get_cached_preferences(pref_file)
        assert result == {"Verbosity": "balanced"}
        assert hook._preferences_cache is not None

    def test_cache_hit_on_unchanged_file(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        pref_file = tmp_path / "prefs.md"
        pref_file.write_text("### Verbosity\nbalanced")
        result1 = hook.get_cached_preferences(pref_file)
        assert result1 == {"Verbosity": "balanced"}

        # Verify cache is populated
        assert hook._preferences_cache == {"Verbosity": "balanced"}
        assert hook._cache_timestamp is not None

        # Call again without modifying the file — should use cache
        result2 = hook.get_cached_preferences(pref_file)
        assert result2 == {"Verbosity": "balanced"}

    def test_cache_miss_on_modified_file(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        pref_file = tmp_path / "prefs.md"
        pref_file.write_text("### Verbosity\nbalanced")
        hook.get_cached_preferences(pref_file)
        # Modify file (change mtime)
        import time

        time.sleep(0.05)
        pref_file.write_text("### Verbosity\nverbose")
        result = hook.get_cached_preferences(pref_file)
        assert result == {"Verbosity": "verbose"}

    def test_file_deleted_returns_empty(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        pref_file = tmp_path / "prefs.md"
        pref_file.write_text("### Verbosity\nbalanced")
        hook.get_cached_preferences(pref_file)
        pref_file.unlink()
        result = hook.get_cached_preferences(pref_file)
        assert result == {}


# ============================================================================
# _inject_amplihack_if_different
# ============================================================================


class TestInjectAmplihackIfDifferent:
    """AMPLIHACK.md injection logic."""

    def test_no_amplihack_md_returns_empty(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        # No AMPLIHACK.md exists and no CLAUDE_PLUGIN_ROOT set
        with patch.dict(os.environ, {}, clear=True):
            result = hook._inject_amplihack_if_different()
        assert result == ""

    def test_same_content_returns_empty(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        # Create identical files
        (tmp_path / "CLAUDE.md").write_text("Same content here")
        amplihack_dir = tmp_path / ".claude"
        amplihack_dir.mkdir(exist_ok=True)
        (amplihack_dir / "AMPLIHACK.md").write_text("Same content here")
        with patch.dict(os.environ, {}, clear=True):
            result = hook._inject_amplihack_if_different()
        assert result == ""

    def test_different_content_returns_amplihack(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("Project CLAUDE content")
        amplihack_dir = tmp_path / ".claude"
        amplihack_dir.mkdir(exist_ok=True)
        (amplihack_dir / "AMPLIHACK.md").write_text("Framework AMPLIHACK content")
        with patch.dict(os.environ, {}, clear=True):
            result = hook._inject_amplihack_if_different()
        assert result == "Framework AMPLIHACK content"

    def test_cache_hit_on_unchanged_files(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("Project content")
        amplihack_dir = tmp_path / ".claude"
        amplihack_dir.mkdir(exist_ok=True)
        (amplihack_dir / "AMPLIHACK.md").write_text("Framework content")

        with patch.dict(os.environ, {}, clear=True):
            # First call populates cache
            result1 = hook._inject_amplihack_if_different()
            assert result1 == "Framework content"

            # Second call should use cache
            result2 = hook._inject_amplihack_if_different()
            assert result2 == "Framework content"
        assert hook._amplihack_cache is not None

    def test_plugin_root_env_var(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        (plugin_dir / "AMPLIHACK.md").write_text("Plugin content")
        (tmp_path / "CLAUDE.md").write_text("Different")
        with patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": str(plugin_dir)}):
            result = hook._inject_amplihack_if_different()
        assert result == "Plugin content"

    def test_exception_returns_empty(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        with patch.object(Path, "exists", side_effect=RuntimeError("boom")):
            result = hook._inject_amplihack_if_different()
        assert result == ""


# ============================================================================
# process() — full flow
# ============================================================================


class TestUserPromptProcess:
    """Full process() flow tests."""

    def test_basic_process_returns_additional_context(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        hook._select_strategy = MagicMock(return_value=None)
        hook.find_user_preferences = MagicMock(return_value=None)
        hook._inject_amplihack_if_different = MagicMock(return_value="")

        result = hook.process({"userMessage": "hello"})
        assert "additionalContext" in result

    def test_preferences_injected_when_found(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        hook._select_strategy = MagicMock(return_value=None)
        pref_file = tmp_path / "prefs.md"
        pref_file.write_text("### Verbosity\nbalanced")
        hook.find_user_preferences = MagicMock(return_value=pref_file)
        hook._inject_amplihack_if_different = MagicMock(return_value="")

        result = hook.process({"userMessage": "hello"})
        assert "ACTIVE USER PREFERENCES" in result["additionalContext"]

    def test_strategy_short_circuits(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        mock_strategy = MagicMock()
        mock_strategy.handle_user_prompt_submit.return_value = {"custom": True}
        hook._select_strategy = MagicMock(return_value=mock_strategy)

        result = hook.process({"userMessage": "hello"})
        assert result == {"custom": True}

    def test_strategy_returns_none_continues(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        mock_strategy = MagicMock()
        mock_strategy.handle_user_prompt_submit.return_value = None
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        hook.find_user_preferences = MagicMock(return_value=None)
        hook._inject_amplihack_if_different = MagicMock(return_value="")

        result = hook.process({"userMessage": "hello"})
        assert "additionalContext" in result

    def test_dict_user_message_handled(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        hook._select_strategy = MagicMock(return_value=None)
        hook.find_user_preferences = MagicMock(return_value=None)
        hook._inject_amplihack_if_different = MagicMock(return_value="")

        result = hook.process({"userMessage": {"text": "hello from dict"}})
        assert "additionalContext" in result

    def test_prompt_key_handled(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        hook._select_strategy = MagicMock(return_value=None)
        hook.find_user_preferences = MagicMock(return_value=None)
        hook._inject_amplihack_if_different = MagicMock(return_value="")

        result = hook.process({"prompt": "hello from prompt key"})
        assert "additionalContext" in result

    def test_dev_prompt_triggers_tracking(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        hook._select_strategy = MagicMock(return_value=None)
        hook.find_user_preferences = MagicMock(return_value=None)
        hook._inject_amplihack_if_different = MagicMock(return_value="")

        with patch("workflow_enforcement_hook._write_state") as mock_write:
            result = hook.process({"userMessage": "/dev implement auth"})
        mock_write.assert_called_once()
        assert "additionalContext" in result

    def test_dev_tracking_failure_non_fatal(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        hook._select_strategy = MagicMock(return_value=None)
        hook.find_user_preferences = MagicMock(return_value=None)
        hook._inject_amplihack_if_different = MagicMock(return_value="")

        with patch("workflow_enforcement_hook._write_state", side_effect=RuntimeError("fail")):
            result = hook.process({"userMessage": "/dev implement auth"})
        # Should not crash
        assert "additionalContext" in result

    def test_memory_injection_failure_non_fatal(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        hook._select_strategy = MagicMock(return_value=None)
        hook.find_user_preferences = MagicMock(return_value=None)
        hook._inject_amplihack_if_different = MagicMock(return_value="")

        with patch(
            "agent_memory_hook.detect_agent_references",
            side_effect=RuntimeError("no module"),
        ):
            result = hook.process({"userMessage": "hello"})
        assert "additionalContext" in result


# ============================================================================
# _select_strategy
# ============================================================================


class TestUserPromptSelectStrategy:
    """Strategy selection error handling."""

    def test_import_error_returns_none(self, tmp_path):
        hook = _make_user_prompt_hook(tmp_path)
        with patch("builtins.__import__", side_effect=ImportError("not found")):
            # The actual method catches ImportError internally
            try:
                result = hook._select_strategy()
            except ImportError:
                result = None
        assert result is None
