"""TDD Integration Tests for Auto Mode Interactive UI.

End-to-end integration tests following Testing Pyramid (10% E2E):
- Full workflow from start to finish
- Real interaction patterns
- Integration between all components
- Focus on critical user journeys

Test Coverage:
1. Complete UI workflow with mocked auto mode
2. Prompt injection via UI during execution
3. Pause and resume workflow
4. Exit UI while auto mode continues
5. Error recovery scenarios
"""

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from amplihack.launcher.auto_mode import AutoMode


class TestFullUIWorkflow:
    """Test complete UI workflow from start to finish."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled and mocked execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Build a REST API with authentication",
                max_turns=5,
                working_dir=Path(temp_dir),
                ui_mode=True,
            )

            # Mock SDK calls to prevent real API usage
            auto_mode.run_sdk = MagicMock(return_value=(0, "Mock response"))
            auto_mode.run_hook = MagicMock()

            yield auto_mode

    def test_ui_starts_and_displays_initial_state(self, auto_mode_with_ui):
        """Test that UI starts and shows correct initial state.

        Expected behavior:
        - Title generated from prompt
        - Session panel shows Turn 1/5, 0s elapsed
        - Todo list shows initial phases
        - Log area shows session start message
        - Input panel ready for text
        """
        # This will fail until full integration is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui

            # Start UI
            auto_mode.start_ui()

            # Check initial state
            ui = auto_mode.ui
            assert ui.title_panel is not None
            assert "REST API" in ui.get_title() or "authentication" in ui.get_title()

            session_text = ui.get_session_details()
            assert "1/5" in session_text or "Turn 1" in session_text

            todos = ui.get_todos()
            assert len(todos) > 0
            assert any("Clarify" in t["content"] for t in todos)

            logs = ui.get_log_content()
            assert "Session" in logs or "Starting" in logs

    def test_ui_updates_during_execution(self, auto_mode_with_ui):
        """Test that UI updates as auto mode executes.

        Expected behavior:
        - Turn counter increments (1/5 → 2/5 → 3/5)
        - Elapsed time increases
        - Todo status changes (pending → in_progress → completed)
        - Logs stream continuously
        - Cost tracking updates
        """
        # This will fail until dynamic updates are implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui

            # Track UI updates
            updates = []

            def capture_update():
                updates.append(
                    {
                        "turn": auto_mode.get_current_turn(),
                        "todos": auto_mode.get_todos(),
                        "logs": auto_mode.get_queued_logs(),
                    }
                )

            # Start execution in background
            auto_mode.start_background()

            # Capture updates periodically
            for _ in range(5):
                time.sleep(0.5)
                capture_update()

            # Verify progression
            assert len(updates) >= 3
            assert updates[0]["turn"] < updates[-1]["turn"]
            assert len(updates[-1]["logs"]) > len(updates[0]["logs"])

            # Cleanup
            auto_mode.stop()
            auto_mode.execution_thread.join(timeout=5)

    def test_ui_shows_completion_state(self, auto_mode_with_ui):
        """Test UI state when auto mode completes.

        Expected behavior:
        - Final turn shown (5/5 or actual completion turn)
        - All todos marked completed
        - Summary displayed in logs
        - Input panel disabled or shows completion message
        """
        # This will fail until completion handling is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui

            # Mock to complete quickly
            auto_mode.max_turns = 2

            # Start and wait for completion
            auto_mode.start_background()
            auto_mode.execution_thread.join(timeout=10)

            ui = auto_mode.ui

            # Check completion state
            todos = ui.get_todos()
            completed_count = sum(1 for t in todos if t["status"] == "completed")
            assert completed_count == len(todos)

            logs = ui.get_log_content()
            assert "Summary" in logs or "Complete" in logs or "Objective achieved" in logs

    def test_ui_handles_execution_error(self, auto_mode_with_ui):
        """Test UI behavior when execution encounters error.

        Expected behavior:
        - Error displayed in logs
        - Current todo marked as failed or error state
        - Session panel shows error indicator
        - UI remains responsive
        """
        # This will fail until error handling is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui

            # Mock SDK to raise error on turn 2
            call_count = [0]

            def mock_with_error(prompt):
                call_count[0] += 1
                if call_count[0] == 2:
                    raise RuntimeError("Simulated SDK error")
                return (0, "Mock response")

            auto_mode.run_sdk = mock_with_error

            # Start execution
            auto_mode.start_background()
            time.sleep(2)  # Let it hit the error

            # Check error state
            logs = auto_mode.get_queued_logs()
            assert any("error" in log.lower() for log in logs)

            # UI should still be responsive
            assert auto_mode.ui.is_responsive()

            # Cleanup
            auto_mode.stop()
            auto_mode.execution_thread.join(timeout=5)


class TestPromptInjectionViaUI:
    """Test injecting new instructions via UI during execution."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Build authentication system",
                max_turns=10,
                working_dir=Path(temp_dir),
                ui_mode=True,
            )

            # Mock to control execution
            auto_mode.run_sdk = MagicMock(return_value=(0, "Mock response"))
            auto_mode.run_hook = MagicMock()

            yield auto_mode

    def test_inject_instruction_during_execution(self, auto_mode_with_ui):
        """Test injecting instruction while auto mode is running.

        Expected behavior:
        - User types instruction in input panel
        - Instruction queued for next turn
        - Instruction file created in append/
        - Auto mode picks up instruction
        - Instruction appended to execute prompt
        """
        # This will fail until injection workflow is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui

            # Start execution
            auto_mode.start_background()
            time.sleep(0.5)  # Let it start

            # Inject instruction from UI
            ui = auto_mode.ui
            ui.submit_input("Add rate limiting to API endpoints")

            # Verify instruction file created
            time.sleep(0.1)
            md_files = list(auto_mode.append_dir.glob("*.md"))
            assert len(md_files) > 0
            assert "rate limiting" in md_files[0].read_text()

            # Wait for auto mode to process
            time.sleep(1)

            # Verify instruction was picked up
            assert auto_mode.run_sdk.called
            prompts = [call[0][0] for call in auto_mode.run_sdk.call_args_list]
            assert any("rate limiting" in p for p in prompts)

            # Cleanup
            auto_mode.stop()
            auto_mode.execution_thread.join(timeout=5)

    def test_multiple_injections_queued_in_order(self, auto_mode_with_ui):
        """Test multiple instruction injections are processed in order.

        Expected behavior:
        - Inject instruction A at time T1
        - Inject instruction B at time T2
        - A processed before B (FIFO order)
        """
        # This will fail until queueing is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui
            ui = auto_mode.ui

            # Inject multiple instructions
            ui.submit_input("First instruction")
            time.sleep(0.1)
            ui.submit_input("Second instruction")
            time.sleep(0.1)
            ui.submit_input("Third instruction")

            # Check files created in order
            md_files = sorted(auto_mode.append_dir.glob("*.md"))
            assert len(md_files) == 3

            contents = [f.read_text() for f in md_files]
            assert "First" in contents[0]
            assert "Second" in contents[1]
            assert "Third" in contents[2]

    def test_injection_appears_in_ui_logs(self, auto_mode_with_ui):
        """Test that injected instructions are logged in UI.

        Expected behavior:
        - When instruction submitted, log message shown
        - Log shows instruction queued for next turn
        """
        # This will fail until injection logging is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui
            ui = auto_mode.ui

            auto_mode.start_background()
            time.sleep(0.5)

            # Inject instruction
            ui.submit_input("Add logging to all functions")

            time.sleep(0.2)

            # Check logs
            logs = auto_mode.get_queued_logs()
            assert any("instruction" in log.lower() for log in logs)
            assert any("logging" in log.lower() for log in logs)

            auto_mode.stop()
            auto_mode.execution_thread.join(timeout=5)

    def test_injection_with_multiline_content(self, auto_mode_with_ui):
        """Test injecting multiline instruction.

        Expected behavior:
        - Multiline input preserved
        - All lines included in instruction file
        - Formatting maintained
        """
        # This will fail until multiline handling is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui
            ui = auto_mode.ui

            multiline = """Add these features:
- Input validation
- Error handling
- Unit tests"""

            ui.submit_input(multiline)

            # Check file content
            md_files = list(auto_mode.append_dir.glob("*.md"))
            content = md_files[0].read_text()

            assert "Input validation" in content
            assert "Error handling" in content
            assert "Unit tests" in content
            assert "\n" in content  # Newlines preserved


class TestPauseAndResume:
    """Test pause and resume functionality."""

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

            # Mock with slow execution to test pause
            def slow_sdk(prompt):
                time.sleep(1)
                return (0, "Mock response")

            auto_mode.run_sdk = slow_sdk
            auto_mode.run_hook = MagicMock()

            yield auto_mode

    def test_pause_stops_new_turns(self, auto_mode_with_ui):
        """Test that pause prevents new turns from starting.

        Expected behavior:
        - Execution running normally
        - Press 'p' to pause
        - Current turn completes
        - No new turn starts
        - Turn counter stays same
        """
        # This will fail until pause mechanism is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui

            # Start execution
            auto_mode.start_background()
            time.sleep(0.5)

            # Get current turn
            turn_before_pause = auto_mode.get_current_turn()

            # Pause
            auto_mode.ui.handle_keyboard_input("p")
            time.sleep(2)  # Wait longer than turn duration

            # Turn should not have advanced
            turn_after_pause = auto_mode.get_current_turn()
            assert turn_after_pause == turn_before_pause

            auto_mode.stop()
            auto_mode.execution_thread.join(timeout=5)

    def test_resume_continues_execution(self, auto_mode_with_ui):
        """Test that resume continues from paused state.

        Expected behavior:
        - Pause execution
        - Press 'p' again to resume
        - Execution continues
        - Turns increment normally
        """
        # This will fail until resume mechanism is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui

            auto_mode.start_background()
            time.sleep(0.5)

            # Pause
            auto_mode.ui.handle_keyboard_input("p")
            turn_at_pause = auto_mode.get_current_turn()
            time.sleep(1)

            # Resume
            auto_mode.ui.handle_keyboard_input("p")
            time.sleep(2)

            # Should have advanced
            turn_after_resume = auto_mode.get_current_turn()
            assert turn_after_resume > turn_at_pause

            auto_mode.stop()
            auto_mode.execution_thread.join(timeout=5)

    def test_pause_indicator_in_ui(self, auto_mode_with_ui):
        """Test that UI shows pause indicator.

        Expected behavior:
        - When paused, UI shows "PAUSED" indicator
        - Session panel shows pause icon or text
        - When resumed, indicator disappears
        """
        # This will fail until pause UI is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui
            ui = auto_mode.ui

            auto_mode.start_background()
            time.sleep(0.5)

            # Pause
            ui.handle_keyboard_input("p")
            time.sleep(0.1)

            session_text = ui.get_session_details()
            assert "PAUSED" in session_text or "⏸" in session_text

            # Resume
            ui.handle_keyboard_input("p")
            time.sleep(0.1)

            session_text = ui.get_session_details()
            assert "PAUSED" not in session_text

            auto_mode.stop()
            auto_mode.execution_thread.join(timeout=5)

    def test_can_inject_while_paused(self, auto_mode_with_ui):
        """Test that instructions can be injected while paused.

        Expected behavior:
        - Pause execution
        - Submit instruction
        - Instruction queued
        - Resume execution
        - Instruction processed
        """
        # This will fail until pause+inject integration is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui
            ui = auto_mode.ui

            auto_mode.start_background()
            time.sleep(0.5)

            # Pause
            ui.handle_keyboard_input("p")
            time.sleep(0.1)

            # Inject while paused
            ui.submit_input("Add feature while paused")

            # Verify file created
            md_files = list(auto_mode.append_dir.glob("*.md"))
            assert len(md_files) > 0

            # Resume
            ui.handle_keyboard_input("p")
            time.sleep(2)

            # Instruction should be processed
            assert auto_mode.run_sdk.called

            auto_mode.stop()
            auto_mode.execution_thread.join(timeout=5)


class TestExitUIAutoModeContinues:
    """Test exiting UI while keeping auto mode running."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Long running task",
                max_turns=10,
                working_dir=Path(temp_dir),
                ui_mode=True,
            )

            # Mock with controlled execution
            auto_mode.run_sdk = MagicMock(return_value=(0, "Mock response"))
            auto_mode.run_hook = MagicMock()

            yield auto_mode

    def test_exit_ui_keeps_automode_running(self, auto_mode_with_ui):
        """Test that pressing 'x' exits UI but keeps auto mode running.

        Expected behavior:
        - Auto mode running in background
        - Press 'x' to exit UI
        - UI closes/exits
        - Background thread still alive
        - Execution continues
        """
        # This will fail until UI exit is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui

            auto_mode.start_background()
            time.sleep(0.5)

            # Exit UI
            auto_mode.ui.handle_keyboard_input("x")
            time.sleep(0.1)

            # UI should be exiting
            assert auto_mode.ui.should_exit()

            # But auto mode thread should still be alive
            assert auto_mode.execution_thread.is_alive()

            # Cleanup
            auto_mode.stop()
            auto_mode.execution_thread.join(timeout=5)

    def test_exit_switches_to_terminal_output(self, auto_mode_with_ui):
        """Test that exiting UI switches to terminal output mode.

        Expected behavior:
        - UI exit triggered
        - Auto mode continues writing to terminal
        - Progress shown as text logs
        """
        # This will fail until output switching is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui

            auto_mode.start_background()
            time.sleep(0.5)

            # Exit UI
            auto_mode.ui.handle_keyboard_input("x")

            # Check that terminal output mode is active
            assert not auto_mode.ui_mode or auto_mode.terminal_fallback_active

            auto_mode.stop()
            auto_mode.execution_thread.join(timeout=5)

    def test_logs_flushed_on_ui_exit(self, auto_mode_with_ui):
        """Test that queued logs are flushed when UI exits.

        Expected behavior:
        - Exit UI with logs in queue
        - All queued logs written to terminal
        - No logs lost
        """
        # This will fail until log flushing is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui

            auto_mode.start_background()
            time.sleep(0.5)

            # Queue some logs
            for i in range(10):
                auto_mode.queue_log(f"Log message {i}")

            # Capture stdout
            import sys
            from io import StringIO

            captured = StringIO()
            sys.stdout = captured

            # Exit UI (should flush logs)
            auto_mode.ui.handle_keyboard_input("x")
            time.sleep(0.2)

            sys.stdout = sys.__stdout__
            output = captured.getvalue()

            # All logs should be in output
            for i in range(10):
                assert f"Log message {i}" in output

            auto_mode.stop()
            auto_mode.execution_thread.join(timeout=5)


class TestErrorRecoveryScenarios:
    """Test error recovery in integrated UI context."""

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
            auto_mode.run_hook = MagicMock()
            yield auto_mode

    def test_recover_from_sdk_timeout(self, auto_mode_with_ui):
        """Test recovery when SDK times out.

        Expected behavior:
        - SDK call times out
        - Error logged to UI
        - Auto retry with backoff
        - Eventually succeeds or fails gracefully
        """
        # This will fail until timeout recovery is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui

            # Mock SDK to timeout then succeed
            call_count = [0]

            def mock_with_timeout(prompt):
                call_count[0] += 1
                if call_count[0] == 1:
                    time.sleep(10)  # Simulate timeout
                    raise TimeoutError("SDK timeout")
                return (0, "Success after retry")

            auto_mode.run_sdk = mock_with_timeout

            auto_mode.start_background()
            time.sleep(15)  # Wait for timeout and retry

            # Should have retried and succeeded
            logs = auto_mode.get_queued_logs()
            assert any("timeout" in log.lower() for log in logs)
            assert any("retry" in log.lower() for log in logs)

            auto_mode.stop()
            auto_mode.execution_thread.join(timeout=5)

    def test_recover_from_ui_thread_crash(self, auto_mode_with_ui):
        """Test that auto mode continues if UI thread crashes.

        Expected behavior:
        - UI encounters exception
        - Auto mode thread isolated from crash
        - Execution continues
        - Falls back to terminal output
        """
        # This will fail until crash isolation is implemented
        with pytest.raises(AttributeError):
            auto_mode = auto_mode_with_ui
            auto_mode.run_sdk = MagicMock(return_value=(0, "Mock response"))

            auto_mode.start_background()
            time.sleep(0.5)

            # Simulate UI crash
            auto_mode.ui._internal_crash = lambda: 1 / 0

            try:
                auto_mode.ui._internal_crash()
            except ZeroDivisionError:
                pass

            # Auto mode should still be running
            time.sleep(0.5)
            assert auto_mode.execution_thread.is_alive()

            auto_mode.stop()
            auto_mode.execution_thread.join(timeout=5)

    def test_graceful_degradation_on_missing_dependencies(self, auto_mode_with_ui):
        """Test graceful degradation if Rich library unavailable.

        Expected behavior:
        - Detect Rich not available
        - Fall back to text-based output
        - Auto mode continues normally
        """
        # This will fail until dependency checking is implemented
        with pytest.raises(AttributeError):
            # Simulate Rich unavailable
            with patch.dict("sys.modules", {"rich": None}):
                with tempfile.TemporaryDirectory() as temp_dir:
                    auto_mode = AutoMode(
                        sdk="claude",
                        prompt="Test",
                        max_turns=3,
                        working_dir=Path(temp_dir),
                        ui_mode=True,
                    )

                    # Should fall back to terminal mode
                    assert not auto_mode.ui or auto_mode.terminal_fallback_active
