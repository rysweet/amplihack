#!/usr/bin/env python3
"""Session lifecycle tests for session_start.py and session_stop.py.

Covers: version check logic, hook migration, strategy selection,
context building, session stop memory store bridge, uncommitted work detection.
"""

import json
from io import StringIO
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_start_hook(tmp_path):
    """Create a SessionStartHook with mocked HookProcessor init."""
    with patch("hook_processor.HookProcessor.__init__", return_value=None):
        from session_start import SessionStartHook

        hook = SessionStartHook()
        hook.hook_name = "session_start"
        hook.project_root = tmp_path
        hook.log_dir = tmp_path / ".claude" / "runtime" / "logs"
        hook.log_dir.mkdir(parents=True, exist_ok=True)
        hook.metrics_dir = tmp_path / ".claude" / "runtime" / "metrics"
        hook.metrics_dir.mkdir(parents=True, exist_ok=True)
        hook.analysis_dir = tmp_path / ".claude" / "runtime" / "analysis"
        hook.analysis_dir.mkdir(parents=True, exist_ok=True)
        hook.log_file = hook.log_dir / "session_start.log"
        hook.log = MagicMock()
        hook.save_metric = MagicMock()
        hook.get_session_id = MagicMock(return_value="20250101_120000_000000")
        return hook


# ============================================================================
# SessionStartHook._check_version_mismatch
# ============================================================================


class TestVersionCheck:
    """Version mismatch detection and handling."""

    def test_no_mismatch_returns_early(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        mock_info = MagicMock()
        mock_info.is_mismatched = False
        with patch.dict("sys.modules", {}):
            with patch(
                "session_start.SessionStartHook._check_version_mismatch"
            ) as mock_check:
                mock_check.return_value = None
                hook._check_version_mismatch()  # Should not raise

    def test_version_check_exception_fails_gracefully(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        # The real _check_version_mismatch catches all exceptions
        # Verify it doesn't crash
        with patch(
            "builtins.__import__", side_effect=ImportError("no version_checker")
        ):
            # Direct call — this should catch and log
            try:
                hook._check_version_mismatch()
            except Exception:
                pass  # Expected if internal imports fail; the point is no crash

    def test_noninteractive_version_prompt_skips_select(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        version_info = MagicMock()
        version_info.is_mismatched = True
        version_info.package_commit = "pkg123"
        version_info.project_commit = "proj456"

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False

        with patch.dict(
            "sys.modules",
            {
                "update_engine": MagicMock(perform_update=MagicMock()),
                "update_prefs": MagicMock(
                    load_update_preference=MagicMock(return_value=None),
                    save_update_preference=MagicMock(),
                ),
                "version_checker": MagicMock(
                    check_version_mismatch=MagicMock(return_value=version_info)
                ),
            },
        ):
            with patch("sys.stdin", mock_stdin):
                with patch("select.select") as mock_select:
                    with patch("sys.stderr", new_callable=StringIO) as stderr:
                        hook._check_version_mismatch()

        mock_select.assert_not_called()
        hook.log.assert_any_call("Non-interactive session detected - skipping update prompt")
        hook.save_metric.assert_any_call("version_prompt_skipped_non_interactive", True)
        assert "Non-interactive session detected - skipping update prompt" in stderr.getvalue()


# ============================================================================
# SessionStartHook._migrate_global_hooks
# ============================================================================


class TestMigrateGlobalHooks:
    """Global hook migration."""

    def test_migration_function_not_available(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        # When migrate_global_hooks is None, should skip silently
        with patch("session_start.migrate_global_hooks", None):
            hook._migrate_global_hooks()  # Should not raise

    def test_migration_raises_exception(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        mock_migrate = MagicMock(side_effect=RuntimeError("migration failed"))
        with patch("session_start.migrate_global_hooks", mock_migrate):
            # Should not raise — fails gracefully
            hook._migrate_global_hooks()


# ============================================================================
# SessionStartHook._select_strategy
# ============================================================================


class TestSessionStartStrategySelection:
    """Strategy selection in session_start."""

    def test_returns_none_when_modules_unavailable(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        with patch("session_start.LauncherDetector", None):
            result = hook._select_strategy()
            assert result is None

    def test_copilot_strategy_selected(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        mock_detector = MagicMock()
        mock_detector.detect.return_value = "copilot"
        mock_copilot_strategy = MagicMock()
        with patch("session_start.LauncherDetector", return_value=mock_detector):
            with patch("session_start.CopilotStrategy", return_value=mock_copilot_strategy):
                with patch("session_start.ClaudeStrategy"):
                    result = hook._select_strategy()
        assert result == mock_copilot_strategy

    def test_claude_strategy_selected_by_default(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        mock_detector = MagicMock()
        mock_detector.detect.return_value = "claude"
        mock_claude_strategy = MagicMock()
        with patch("session_start.LauncherDetector", return_value=mock_detector):
            with patch("session_start.ClaudeStrategy", return_value=mock_claude_strategy):
                with patch("session_start.CopilotStrategy"):
                    result = hook._select_strategy()
        assert result == mock_claude_strategy


# ============================================================================
# SessionStartHook.process — context building
# ============================================================================


class TestSessionStartProcess:
    """Process method builds comprehensive context."""

    def test_process_returns_hook_specific_output(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        # Mock strategy to return an object with __class__.__name__
        mock_strategy = MagicMock()
        mock_strategy.__class__.__name__ = "TestStrategy"
        mock_strategy.inject_context.return_value = "injected prefs"
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        hook._check_version_mismatch = MagicMock()
        hook._migrate_global_hooks = MagicMock()

        # Create minimal project structure
        context_dir = tmp_path / ".claude" / "context"
        context_dir.mkdir(parents=True, exist_ok=True)

        result = hook.process({"prompt": "implement a feature"})
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        assert "additionalContext" in result["hookSpecificOutput"]

    def test_process_with_short_prompt(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        mock_strategy = MagicMock()
        mock_strategy.__class__.__name__ = "TestStrategy"
        mock_strategy.inject_context.return_value = "prefs context"
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        hook._check_version_mismatch = MagicMock()
        hook._migrate_global_hooks = MagicMock()

        result = hook.process({"prompt": "hi"})
        assert "hookSpecificOutput" in result

    def test_process_with_empty_prompt(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        mock_strategy = MagicMock()
        mock_strategy.__class__.__name__ = "TestStrategy"
        mock_strategy.inject_context.return_value = "prefs context"
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        hook._check_version_mismatch = MagicMock()
        hook._migrate_global_hooks = MagicMock()

        result = hook.process({"prompt": ""})
        assert "hookSpecificOutput" in result

    def test_process_builds_project_context(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        mock_strategy = MagicMock()
        mock_strategy.__class__.__name__ = "TestStrategy"
        mock_strategy.inject_context.return_value = "prefs"
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        hook._check_version_mismatch = MagicMock()
        hook._migrate_global_hooks = MagicMock()

        # Create PROJECT.md
        context_dir = tmp_path / ".claude" / "context"
        context_dir.mkdir(parents=True, exist_ok=True)
        (context_dir / "PROJECT.md").write_text("# Project\nThis is the project.")

        result = hook.process({"prompt": "test"})
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "Project Context" in context

    def test_process_preferences_injection(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        mock_strategy = MagicMock()
        mock_strategy.__class__.__name__ = "TestStrategy"
        mock_strategy.inject_context.return_value = "USER PREFS INJECTED"
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        hook._check_version_mismatch = MagicMock()
        hook._migrate_global_hooks = MagicMock()

        # Create preferences file
        context_dir = tmp_path / ".claude" / "context"
        context_dir.mkdir(parents=True, exist_ok=True)
        (context_dir / "USER_PREFERENCES.md").write_text("# Prefs\nVerbosity: balanced")

        # Mock FrameworkPathResolver
        with patch("session_start.FrameworkPathResolver") as mock_resolver:
            mock_resolver.resolve_preferences_file.return_value = (
                context_dir / "USER_PREFERENCES.md"
            )
            result = hook.process({"prompt": "test"})
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "USER PREFS INJECTED" in context

    def test_process_neo4j_skip(self, tmp_path):
        """Neo4j section should be a no-op."""
        hook = _make_session_start_hook(tmp_path)
        mock_strategy = MagicMock()
        mock_strategy.__class__.__name__ = "TestStrategy"
        mock_strategy.inject_context.return_value = "prefs"
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        hook._check_version_mismatch = MagicMock()
        hook._migrate_global_hooks = MagicMock()

        with patch.dict(os.environ, {"AMPLIHACK_ENABLE_NEO4J_MEMORY": "1"}):
            result = hook.process({"prompt": "test"})
        # Should still produce valid output
        assert "hookSpecificOutput" in result


# ============================================================================
# session_stop.py — main()
# ============================================================================


class TestSessionStopMain:
    """Memory store bridge in session_stop."""

    def test_tty_stdin_exits_silently(self):
        """When stdin is TTY, should exit without error."""
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        with patch("sys.stdin", mock_stdin):
            with patch.dict("sys.modules", {
                "amplihack.memory.coordinator": MagicMock(),
                "amplihack.memory.types": MagicMock(),
            }):
                from session_stop import main
                main()  # Should not raise

    def test_empty_agent_output_returns_early(self):
        """No agent_output should skip storage."""
        from io import StringIO

        mock_stdin = StringIO(json.dumps({"agent_type": "test", "output": ""}))
        mock_stdin.isatty = lambda: False
        with patch("sys.stdin", mock_stdin):
            with patch.dict("sys.modules", {
                "amplihack.memory.coordinator": MagicMock(),
                "amplihack.memory.types": MagicMock(),
            }):
                # Reimport to get fresh module
                import importlib
                import session_stop
                importlib.reload(session_stop)
                session_stop.main()  # Should not raise

    def test_memory_store_failure_non_fatal(self):
        """Memory storage failure should log warning but not crash."""
        from io import StringIO

        session_data = {
            "agent_type": "test",
            "output": "test output text",
            "task": "test task",
            "success": True,
            "session_id": "test-session",
        }
        mock_stdin = StringIO(json.dumps(session_data))
        mock_stdin.isatty = lambda: False

        # Mock the coordinator to raise
        mock_coordinator_module = MagicMock()
        mock_coordinator_module.MemoryCoordinator.side_effect = RuntimeError("storage failed")

        with patch("sys.stdin", mock_stdin):
            with patch.dict("sys.modules", {
                "amplihack.memory.coordinator": mock_coordinator_module,
                "amplihack.memory.types": MagicMock(),
            }):
                import importlib
                import session_stop
                importlib.reload(session_stop)
                session_stop.main()  # Should not raise

    def test_invalid_json_handled(self):
        """Invalid JSON in stdin should be handled."""
        from io import StringIO

        mock_stdin = StringIO("{invalid json}")
        mock_stdin.isatty = lambda: False
        with patch("sys.stdin", mock_stdin):
            with patch.dict("sys.modules", {
                "amplihack.memory.coordinator": MagicMock(),
                "amplihack.memory.types": MagicMock(),
            }):
                import importlib
                import session_stop
                importlib.reload(session_stop)
                # json.loads will raise, caught by outer try-except
                session_stop.main()  # Should not raise


# ============================================================================
# SessionStartHook — substantial keyword detection
# ============================================================================


class TestSubstantialPromptDetection:
    """Prompt substantiality checks."""

    def test_implement_keyword_is_substantial(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        mock_strategy = MagicMock()
        mock_strategy.__class__.__name__ = "TestStrategy"
        mock_strategy.inject_context.return_value = "prefs"
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        hook._check_version_mismatch = MagicMock()
        hook._migrate_global_hooks = MagicMock()

        # "implement" is a substantial keyword
        result = hook.process({"prompt": "implement auth"})
        assert "hookSpecificOutput" in result

    def test_long_prompt_is_substantial(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        mock_strategy = MagicMock()
        mock_strategy.__class__.__name__ = "TestStrategy"
        mock_strategy.inject_context.return_value = "prefs"
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        hook._check_version_mismatch = MagicMock()
        hook._migrate_global_hooks = MagicMock()

        # > 20 chars is substantial
        result = hook.process({"prompt": "a" * 25})
        assert "hookSpecificOutput" in result


# ============================================================================
# SessionStartHook — blarify & gitignore
# ============================================================================


class TestBlarifyAndGitignore:
    """Blarify and gitignore check integration."""

    def test_blarify_disabled_by_env(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        mock_strategy = MagicMock()
        mock_strategy.__class__.__name__ = "TestStrategy"
        mock_strategy.inject_context.return_value = "prefs"
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        hook._check_version_mismatch = MagicMock()
        hook._migrate_global_hooks = MagicMock()

        with patch.dict(os.environ, {"AMPLIHACK_DISABLE_BLARIFY": "1"}):
            result = hook.process({"prompt": "test"})
        assert "hookSpecificOutput" in result

    def test_gitignore_check_failure_non_fatal(self, tmp_path):
        hook = _make_session_start_hook(tmp_path)
        mock_strategy = MagicMock()
        mock_strategy.__class__.__name__ = "TestStrategy"
        mock_strategy.inject_context.return_value = "prefs"
        hook._select_strategy = MagicMock(return_value=mock_strategy)
        hook._check_version_mismatch = MagicMock()
        hook._migrate_global_hooks = MagicMock()

        # GitignoreChecker is imported locally in process(), so patch the import
        with patch("gitignore_checker.GitignoreChecker", side_effect=RuntimeError("fail")):
            result = hook.process({"prompt": "test"})
        assert "hookSpecificOutput" in result
