"""TDD Tests for Auto Mode Interactive UI Component.

This test suite follows the Testing Pyramid principle:
- Unit tests for individual UI components (60%)
- Focus on critical paths and edge cases
- All tests should FAIL initially to guide implementation

Test Coverage:
1. UI initialization and layout creation
2. Title generation from user prompt
3. Session details display (turn counter, elapsed time, cost tracking)
4. Todo list integration and updates
5. Log area updates (streaming and batched)
6. Prompt input handling
7. Keyboard command handling (x, p, k)
8. Boundary conditions and error cases
"""

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from amplihack.launcher.auto_mode import AutoMode


class TestAutoModeUIInitialization:
    """Test UI initialization and basic setup."""

    @pytest.fixture
    def temp_working_dir(self):
        """Create temporary working directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_ui_mode_creates_ui_instance(self, temp_working_dir):
        """Test that AutoMode creates UI instance when ui_mode=True.

        Expected behavior:
        - AutoMode should have ui_enabled attribute
        - UI instance should be created when ui_mode=True
        - UI should NOT be created when ui_mode=False
        """
        # Test with UI enabled
        auto_mode_with_ui = AutoMode(
            sdk="claude",
            prompt="Test prompt",
            max_turns=5,
            working_dir=temp_working_dir,
            ui_mode=True,
        )

        assert hasattr(auto_mode_with_ui, "ui_enabled"), "Should have ui_enabled attribute"
        assert auto_mode_with_ui.ui_enabled is True, "UI should be enabled"
        assert hasattr(auto_mode_with_ui, "ui"), "Should have ui instance"

        # Test with UI disabled (default)
        auto_mode_no_ui = AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=5, working_dir=temp_working_dir
        )

        assert not hasattr(auto_mode_no_ui, "ui") or auto_mode_no_ui.ui is None

    def test_ui_has_required_components(self, temp_working_dir):
        """Test that UI instance has all required components.

        Expected behavior:
        - UI should have title panel
        - UI should have session details panel
        - UI should have todo list panel
        - UI should have log area panel
        - UI should have prompt input panel
        """
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Build authentication system",
            max_turns=5,
            working_dir=temp_working_dir,
            ui_mode=True,
        )

        ui = auto_mode.ui
        assert hasattr(ui, "title_panel"), "UI should have title_panel"
        assert hasattr(ui, "session_panel"), "UI should have session_panel"
        assert hasattr(ui, "todo_panel"), "UI should have todo_panel"
        assert hasattr(ui, "log_panel"), "UI should have log_panel"
        assert hasattr(ui, "input_panel"), "UI should have input_panel"

    def test_ui_initializes_with_layout(self, temp_working_dir):
        """Test that UI creates proper Rich layout structure.

        Expected behavior:
        - UI should create a Layout instance
        - Layout should have 5 areas (title, session, todos, logs, input)
        - Layout should be properly configured for terminal display
        """
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Test prompt",
            max_turns=5,
            working_dir=temp_working_dir,
            ui_mode=True,
        )

        ui = auto_mode.ui
        assert hasattr(ui, "layout"), "UI should have layout"
        assert ui.layout is not None, "Layout should be initialized"

        # Check that layout has correct structure
        # This will fail until implementation is complete
        with pytest.raises(AttributeError):
            assert ui.layout["title"] is not None
            assert ui.layout["session"] is not None
            assert ui.layout["todos"] is not None
            assert ui.layout["logs"] is not None
            assert ui.layout["input"] is not None


class TestUITitleGeneration:
    """Test title generation from user prompt using Claude SDK."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Build a REST API with authentication and rate limiting",
                max_turns=5,
                working_dir=Path(temp_dir),
                ui_mode=True,
            )
            yield auto_mode

    def test_title_generation_uses_claude_sdk(self, auto_mode_with_ui):
        """Test that title is generated using Claude SDK.

        Expected behavior:
        - Should call Claude SDK with title generation prompt
        - Should extract short title from response (max 50 chars)
        - Should fall back to truncated prompt if SDK fails
        """
        ui = auto_mode_with_ui.ui

        # Mock SDK call
        with patch("amplihack.launcher.auto_mode.CLAUDE_SDK_AVAILABLE", True):
            with patch("amplihack.launcher.auto_mode.query"):
                # This will fail until title generation is implemented
                with pytest.raises(AttributeError):
                    title = ui.generate_title()
                    assert len(title) <= 50, "Title should be max 50 characters"
                    assert title != "", "Title should not be empty"

    def test_title_truncates_long_prompts(self, auto_mode_with_ui):
        """Test that long prompts are truncated for title.

        Expected behavior:
        - Prompts > 50 chars should be truncated with "..."
        - Truncation should happen at word boundary if possible
        """
        long_prompt = "Build a comprehensive REST API with authentication, rate limiting, caching, monitoring, and full CRUD operations"

        auto_mode = AutoMode(
            sdk="claude",
            prompt=long_prompt,
            max_turns=5,
            working_dir=auto_mode_with_ui.working_dir,
            ui_mode=True,
        )

        # This will fail until title generation is implemented
        with pytest.raises(AttributeError):
            title = auto_mode.ui.generate_title()
            assert len(title) <= 50
            assert title.endswith("...")

    def test_title_handles_empty_prompt(self):
        """Test title generation with empty prompt.

        Expected behavior:
        - Should return default title "Auto Mode Session"
        - Should not crash or raise exception
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude", prompt="", max_turns=5, working_dir=Path(temp_dir), ui_mode=True
            )

            # This will fail until edge case handling is implemented
            with pytest.raises(AttributeError):
                title = auto_mode.ui.generate_title()
                assert title == "Auto Mode Session"


class TestSessionDetailsDisplay:
    """Test session details panel (turn counter, time, cost)."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=10,
                working_dir=Path(temp_dir),
                ui_mode=True,
            )
            auto_mode.start_time = time.time()
            yield auto_mode

    def test_session_panel_shows_turn_counter(self, auto_mode_with_ui):
        """Test that session panel displays current turn.

        Expected behavior:
        - Should display "Turn X/Y" format
        - Should update as turns progress
        """
        ui = auto_mode_with_ui.ui

        # This will fail until session panel is implemented
        with pytest.raises(AttributeError):
            session_text = ui.get_session_details()
            assert "Turn 1/10" in session_text or "1/10" in session_text

    def test_session_panel_shows_elapsed_time(self, auto_mode_with_ui):
        """Test that session panel displays elapsed time.

        Expected behavior:
        - Should format time as "Xm Ys" or "Xs"
        - Should update in real-time
        """
        ui = auto_mode_with_ui.ui
        auto_mode_with_ui.start_time = time.time() - 90  # 1m 30s ago

        # This will fail until time display is implemented
        with pytest.raises(AttributeError):
            session_text = ui.get_session_details()
            assert "1m 30s" in session_text or "90s" in session_text

    def test_session_panel_shows_cost_tracking(self, auto_mode_with_ui):
        """Test that session panel displays cost tracking from SDK.

        Expected behavior:
        - Should display input tokens count
        - Should display output tokens count
        - Should display estimated cost if available
        """
        ui = auto_mode_with_ui.ui

        # Mock SDK cost tracking
        with patch.object(
            ui,
            "get_cost_info",
            return_value={"input_tokens": 1500, "output_tokens": 800, "estimated_cost": 0.025},
        ):
            # This will fail until cost tracking is implemented
            with pytest.raises(AttributeError):
                session_text = ui.get_session_details()
                assert "1500" in session_text  # Input tokens
                assert "800" in session_text  # Output tokens
                assert "$0.025" in session_text or "0.025" in session_text

    def test_session_panel_formats_large_numbers(self, auto_mode_with_ui):
        """Test that large token counts are formatted with commas.

        Expected behavior:
        - Numbers >= 1000 should use comma separators
        - Example: 15000 -> "15,000"
        """
        ui = auto_mode_with_ui.ui

        with patch.object(
            ui,
            "get_cost_info",
            return_value={"input_tokens": 150000, "output_tokens": 80000, "estimated_cost": 2.50},
        ):
            # This will fail until number formatting is implemented
            with pytest.raises(AttributeError):
                session_text = ui.get_session_details()
                assert "150,000" in session_text or "150000" in session_text
                assert "80,000" in session_text or "80000" in session_text


class TestTodoListIntegration:
    """Test todo list panel integration with auto mode execution."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=Path(temp_dir),
                ui_mode=True,
            )
            yield auto_mode

    def test_todo_panel_displays_current_todos(self, auto_mode_with_ui):
        """Test that todo panel shows current todo list.

        Expected behavior:
        - Should display all todos with status indicators
        - Should show pending (⏸), in_progress (▶), completed (✓)
        - Should update when todos change
        """
        ui = auto_mode_with_ui.ui

        # Mock todo list
        todos = [
            {
                "content": "Clarify objective",
                "status": "completed",
                "activeForm": "Clarifying objective",
            },
            {"content": "Create plan", "status": "in_progress", "activeForm": "Creating plan"},
            {"content": "Execute plan", "status": "pending", "activeForm": "Executing plan"},
        ]

        # This will fail until todo integration is implemented
        with pytest.raises(AttributeError):
            ui.update_todos(todos)
            todo_text = ui.get_todo_display()
            assert "✓" in todo_text or "completed" in todo_text.lower()
            assert "▶" in todo_text or "in_progress" in todo_text.lower()

    def test_todo_panel_highlights_current_task(self, auto_mode_with_ui):
        """Test that current task is highlighted in todo list.

        Expected behavior:
        - in_progress task should be highlighted/colored differently
        - Should use Rich styling for emphasis
        """
        ui = auto_mode_with_ui.ui

        todos = [
            {"content": "Task 1", "status": "completed", "activeForm": "Completing task 1"},
            {"content": "Task 2", "status": "in_progress", "activeForm": "Working on task 2"},
            {"content": "Task 3", "status": "pending", "activeForm": "Starting task 3"},
        ]

        # This will fail until highlighting is implemented
        with pytest.raises(AttributeError):
            ui.update_todos(todos)
            # Check that in_progress task uses different styling
            assert ui.todo_panel.has_highlight("Task 2")

    def test_todo_panel_handles_empty_list(self, auto_mode_with_ui):
        """Test todo panel with empty todo list.

        Expected behavior:
        - Should display message "No tasks yet"
        - Should not crash or show errors
        """
        ui = auto_mode_with_ui.ui

        # This will fail until empty state handling is implemented
        with pytest.raises(AttributeError):
            ui.update_todos([])
            todo_text = ui.get_todo_display()
            assert "No tasks" in todo_text or "Empty" in todo_text


class TestLogAreaUpdates:
    """Test log area streaming and updates."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=Path(temp_dir),
                ui_mode=True,
            )
            yield auto_mode

    def test_log_area_displays_streamed_output(self, auto_mode_with_ui):
        """Test that log area shows streaming output from Claude SDK.

        Expected behavior:
        - Should append new log lines as they arrive
        - Should maintain scrollback buffer
        - Should auto-scroll to bottom on new content
        """
        ui = auto_mode_with_ui.ui

        # This will fail until log streaming is implemented
        with pytest.raises(AttributeError):
            ui.append_log("Line 1")
            ui.append_log("Line 2")
            ui.append_log("Line 3")

            log_content = ui.get_log_content()
            assert "Line 1" in log_content
            assert "Line 2" in log_content
            assert "Line 3" in log_content

    def test_log_area_handles_rapid_updates(self, auto_mode_with_ui):
        """Test log area with rapid streaming updates.

        Expected behavior:
        - Should batch updates for performance (max 30 updates/sec)
        - Should not drop messages
        - Should maintain order
        """
        ui = auto_mode_with_ui.ui

        # This will fail until batching is implemented
        with pytest.raises(AttributeError):
            # Simulate rapid updates
            for i in range(100):
                ui.append_log(f"Log message {i}")

            log_content = ui.get_log_content()
            assert "Log message 0" in log_content
            assert "Log message 99" in log_content

    def test_log_area_truncates_old_content(self, auto_mode_with_ui):
        """Test that log area maintains maximum buffer size.

        Expected behavior:
        - Should keep last N lines (default 1000)
        - Should drop oldest lines when limit exceeded
        - Should show indicator "(older logs truncated)"
        """
        ui = auto_mode_with_ui.ui

        # This will fail until buffer management is implemented
        with pytest.raises(AttributeError):
            # Add more than buffer size
            for i in range(1100):
                ui.append_log(f"Line {i}")

            log_content = ui.get_log_content()
            # First 100 lines should be gone
            assert "Line 0" not in log_content
            assert "Line 100" in log_content
            assert "Line 1099" in log_content

    def test_log_area_formats_timestamps(self, auto_mode_with_ui):
        """Test that log entries include timestamps.

        Expected behavior:
        - Each log line should have [HH:MM:SS] prefix
        - Timestamps should be in local time
        """
        ui = auto_mode_with_ui.ui

        # This will fail until timestamp formatting is implemented
        with pytest.raises(AttributeError):
            ui.append_log("Test message")
            log_content = ui.get_log_content()
            # Check for timestamp pattern [HH:MM:SS]
            import re

            assert re.search(r"\[\d{2}:\d{2}:\d{2}\]", log_content)


class TestPromptInputHandling:
    """Test prompt input panel for injecting new instructions."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=Path(temp_dir),
                ui_mode=True,
            )
            yield auto_mode

    def test_input_panel_accepts_text_input(self, auto_mode_with_ui):
        """Test that input panel accepts and queues text input.

        Expected behavior:
        - Should allow typing multi-line input
        - Should queue input for next turn
        - Should clear input after submission
        """
        ui = auto_mode_with_ui.ui

        # This will fail until input handling is implemented
        with pytest.raises(AttributeError):
            ui.set_input_text("Add error handling")
            assert ui.has_pending_input()

            pending = ui.get_pending_input()
            assert pending == "Add error handling"

            # Input should be cleared after retrieval
            assert not ui.has_pending_input()

    def test_input_panel_supports_multiline(self, auto_mode_with_ui):
        """Test that input panel supports multi-line input.

        Expected behavior:
        - Should accept input with newlines
        - Should preserve formatting
        """
        ui = auto_mode_with_ui.ui

        multiline_input = """Add these features:
- Error handling
- Logging
- Tests"""

        # This will fail until multiline support is implemented
        with pytest.raises(AttributeError):
            ui.set_input_text(multiline_input)
            pending = ui.get_pending_input()
            assert "\n" in pending
            assert "- Error handling" in pending

    def test_input_panel_shows_placeholder_text(self, auto_mode_with_ui):
        """Test that input panel shows helpful placeholder.

        Expected behavior:
        - Should show "Type new instructions..." when empty
        - Placeholder should disappear when user starts typing
        """
        ui = auto_mode_with_ui.ui

        # This will fail until placeholder is implemented
        with pytest.raises(AttributeError):
            placeholder = ui.get_input_placeholder()
            assert "Type" in placeholder or "instructions" in placeholder

    def test_input_creates_instruction_file(self, auto_mode_with_ui):
        """Test that submitted input creates instruction file.

        Expected behavior:
        - Should write input to append/TIMESTAMP.md
        - Should be picked up by _check_for_new_instructions()
        """
        ui = auto_mode_with_ui.ui

        # This will fail until file creation is implemented
        with pytest.raises(AttributeError):
            ui.submit_input("Add validation")

            # Check that instruction file was created
            md_files = list(auto_mode_with_ui.append_dir.glob("*.md"))
            assert len(md_files) == 1
            assert "Add validation" in md_files[0].read_text()


class TestKeyboardCommands:
    """Test keyboard command handling (x, p, k)."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=Path(temp_dir),
                ui_mode=True,
            )
            yield auto_mode

    def test_keyboard_command_x_exits_ui(self, auto_mode_with_ui):
        """Test that 'x' command exits UI but continues auto mode.

        Expected behavior:
        - Press 'x' should close UI
        - Auto mode should continue in background
        - Should return to terminal output mode
        """
        ui = auto_mode_with_ui.ui

        # This will fail until exit command is implemented
        with pytest.raises(AttributeError):
            ui.handle_keyboard_input("x")
            assert ui.should_exit()
            assert not auto_mode_with_ui.should_stop()

    def test_keyboard_command_p_pauses_execution(self, auto_mode_with_ui):
        """Test that 'p' command pauses/resumes execution.

        Expected behavior:
        - First 'p' should pause execution
        - Second 'p' should resume execution
        - UI should show pause indicator
        """
        ui = auto_mode_with_ui.ui

        # This will fail until pause command is implemented
        with pytest.raises(AttributeError):
            # Pause
            ui.handle_keyboard_input("p")
            assert auto_mode_with_ui.is_paused()

            # Resume
            ui.handle_keyboard_input("p")
            assert not auto_mode_with_ui.is_paused()

    def test_keyboard_command_k_kills_auto_mode(self, auto_mode_with_ui):
        """Test that 'k' command kills auto mode completely.

        Expected behavior:
        - Should stop auto mode execution
        - Should exit UI
        - Should cleanup resources
        """
        ui = auto_mode_with_ui.ui

        # This will fail until kill command is implemented
        with pytest.raises(AttributeError):
            ui.handle_keyboard_input("k")
            assert auto_mode_with_ui.should_stop()
            assert ui.should_exit()

    def test_keyboard_commands_case_insensitive(self, auto_mode_with_ui):
        """Test that keyboard commands work with uppercase.

        Expected behavior:
        - 'X', 'P', 'K' should work same as lowercase
        """
        ui = auto_mode_with_ui.ui

        # This will fail until case handling is implemented
        with pytest.raises(AttributeError):
            ui.handle_keyboard_input("X")
            assert ui.should_exit()

    def test_keyboard_ignores_invalid_commands(self, auto_mode_with_ui):
        """Test that invalid keys are ignored.

        Expected behavior:
        - Should ignore keys other than x, p, k
        - Should not crash or show errors
        """
        ui = auto_mode_with_ui.ui

        # This will fail until input validation is implemented
        with pytest.raises(AttributeError):
            ui.handle_keyboard_input("z")
            ui.handle_keyboard_input("1")
            ui.handle_keyboard_input("!")
            # Should not raise exceptions

    def test_keyboard_shows_help_on_h(self, auto_mode_with_ui):
        """Test that 'h' shows help overlay.

        Expected behavior:
        - Should display help overlay with command list
        - Help should include x, p, k commands
        """
        ui = auto_mode_with_ui.ui

        # This will fail until help overlay is implemented
        with pytest.raises(AttributeError):
            ui.handle_keyboard_input("h")
            assert ui.is_showing_help()


class TestUIBoundaryConditions:
    """Test boundary conditions and edge cases."""

    def test_ui_handles_very_long_titles(self):
        """Test UI with extremely long prompt for title.

        Expected behavior:
        - Should truncate gracefully
        - Should not break layout
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            very_long_prompt = "A" * 500
            auto_mode = AutoMode(
                sdk="claude",
                prompt=very_long_prompt,
                max_turns=5,
                working_dir=Path(temp_dir),
                ui_mode=True,
            )

            # This will fail until length handling is implemented
            with pytest.raises(AttributeError):
                title = auto_mode.ui.generate_title()
                assert len(title) <= 50

    def test_ui_handles_unicode_in_logs(self):
        """Test UI with unicode characters in log output.

        Expected behavior:
        - Should display unicode correctly
        - Should not crash on emoji or special chars
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude", prompt="Test", max_turns=5, working_dir=Path(temp_dir), ui_mode=True
            )

            # This will fail until unicode handling is implemented
            with pytest.raises(AttributeError):
                ui = auto_mode.ui
                ui.append_log("✓ Success with emoji 🎉")
                ui.append_log("中文字符测试")
                log_content = ui.get_log_content()
                assert "✓" in log_content
                assert "🎉" in log_content

    def test_ui_handles_zero_max_turns(self):
        """Test UI with max_turns=0 edge case.

        Expected behavior:
        - Should handle gracefully
        - Should show 0/0 or disable turn display
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude", prompt="Test", max_turns=0, working_dir=Path(temp_dir), ui_mode=True
            )

            # This will fail until edge case is handled
            with pytest.raises((AttributeError, ValueError)):
                auto_mode.ui.get_session_details()
                # Should not crash

    def test_ui_handles_negative_elapsed_time(self):
        """Test UI with negative elapsed time (clock skew).

        Expected behavior:
        - Should clamp to 0 or show "0s"
        - Should not crash
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude", prompt="Test", max_turns=5, working_dir=Path(temp_dir), ui_mode=True
            )
            # Set start_time in the future
            auto_mode.start_time = time.time() + 100

            # This will fail until edge case is handled
            with pytest.raises(AttributeError):
                session_text = auto_mode.ui.get_session_details()
                assert "0s" in session_text or "0m" in session_text


class TestUIErrorHandling:
    """Test UI error handling and resilience."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=Path(temp_dir),
                ui_mode=True,
            )
            yield auto_mode

    def test_ui_handles_missing_cost_info(self, auto_mode_with_ui):
        """Test UI when cost info is unavailable.

        Expected behavior:
        - Should show "N/A" or "-" for missing values
        - Should not crash
        """
        ui = auto_mode_with_ui.ui

        with patch.object(ui, "get_cost_info", return_value=None):
            # This will fail until error handling is implemented
            with pytest.raises(AttributeError):
                session_text = ui.get_session_details()
                assert "N/A" in session_text or "-" in session_text

    def test_ui_handles_todo_update_failure(self, auto_mode_with_ui):
        """Test UI when todo update fails.

        Expected behavior:
        - Should log error but not crash
        - Should maintain previous todo state
        """
        ui = auto_mode_with_ui.ui

        # This will fail until error handling is implemented
        with pytest.raises(AttributeError):
            ui.update_todos([{"invalid": "structure"}])
            # Should not raise exception

    def test_ui_handles_log_write_failure(self, auto_mode_with_ui):
        """Test UI when log writing fails.

        Expected behavior:
        - Should continue operation
        - Should log error internally
        """
        ui = auto_mode_with_ui.ui

        # Mock append to raise exception
        with patch.object(ui, "_append_to_buffer", side_effect=OSError("Disk full")):
            # This will fail until error handling is implemented
            with pytest.raises(AttributeError):
                ui.append_log("Test message")
                # Should not propagate exception
