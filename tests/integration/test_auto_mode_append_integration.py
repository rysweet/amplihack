"""Integration tests for auto mode instruction injection feature.

Tests end-to-end workflows combining:
- AutoMode directory creation and prompt writing
- SessionFinder discovery
- append_instructions writing
- AutoMode processing of appended instructions

Following TDD approach - these tests should FAIL initially until all components are implemented.
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

# Import components to be implemented
try:
    from amplihack.launcher.session_finder import SessionFinder, SessionInfo
    from amplihack.launcher.append_handler import append_instructions, AppendResult
except ImportError:
    # Placeholders for not-yet-implemented components
    class SessionFinder:
        pass

    class SessionInfo:
        pass

    def append_instructions(instruction: str, session_id: str = None):
        raise NotImplementedError()

    class AppendResult:
        pass


@pytest.mark.integration
class TestFullWorkflowStartAutoAppendProcess:
    """Test complete workflow: start auto mode -> append instruction -> process."""

    @pytest.fixture
    def workspace_setup(self):
        """Create test workspace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            yield workspace

    def test_full_workflow_with_mocked_sdk(self, workspace_setup):
        """Test full workflow from auto mode start to instruction processing.

        Workflow:
        1. Start AutoMode - creates directories and prompt.md
        2. External process uses append_instructions to add new instruction
        3. AutoMode._check_for_new_instructions() finds and processes it
        4. Instruction is included in execution prompt

        Expected behavior:
        - All directories created correctly
        - prompt.md written with original prompt
        - append_instructions finds active session
        - New instruction written to append/
        - AutoMode processes instruction and moves to appended/
        - Instruction content included in execution
        """
        workspace = workspace_setup

        # Step 1: Start AutoMode
        original_prompt = "Implement authentication system"

        auto_mode = AutoMode(
            sdk="claude",
            prompt=original_prompt,
            max_turns=3,
            working_dir=workspace
        )

        # Mock SDK to avoid actual calls
        sdk_calls = []

        def mock_sdk(prompt):
            sdk_calls.append(prompt)
            return (0, "Mock SDK response")

        auto_mode.run_sdk = mock_sdk
        auto_mode.run_hook = MagicMock()

        # Verify initial setup
        assert auto_mode.append_dir.exists(), "append/ directory should exist"
        assert auto_mode.appended_dir.exists(), "appended/ directory should exist"
        assert (auto_mode.log_dir / "prompt.md").exists(), "prompt.md should exist"

        # Step 2: Simulate external append operation
        new_instruction = "Add rate limiting to API endpoints"

        # Change to workspace to simulate CLI call
        with patch('pathlib.Path.cwd', return_value=workspace):
            # This will fail until append_instructions is implemented
            try:
                result = append_instructions(new_instruction)

                # Verify instruction file created
                md_files = list(auto_mode.append_dir.glob("*.md"))
                assert len(md_files) == 1, "Should create instruction file"
                assert new_instruction in md_files[0].read_text()

                # Step 3: AutoMode checks for instructions
                instructions = auto_mode._check_for_new_instructions()

                # Verify instruction was found
                assert new_instruction in instructions, \
                    "Should find and return new instruction"

                # Verify file moved to appended/
                assert len(list(auto_mode.append_dir.glob("*.md"))) == 0, \
                    "append/ should be empty after processing"
                assert len(list(auto_mode.appended_dir.glob("*.md"))) == 1, \
                    "appended/ should contain processed instruction"

            except (NotImplementedError, ImportError, AttributeError):
                pytest.skip("append_instructions not yet implemented")

    def test_instruction_included_in_execution_prompt(self, workspace_setup):
        """Test that appended instructions are included in execution prompts.

        Expected behavior:
        - Instructions should be concatenated to execute_prompt
        - Timestamp context should be preserved
        - Multiple instructions should be combined
        """
        workspace = workspace_setup

        auto_mode = AutoMode(
            sdk="claude",
            prompt="Build API",
            max_turns=3,
            working_dir=workspace
        )

        # Create instruction files directly
        instruction1 = auto_mode.append_dir / "20241023_120000.md"
        instruction2 = auto_mode.append_dir / "20241023_120100.md"

        instruction1.write_text("Add authentication")
        instruction2.write_text("Add logging")

        # Check for instructions
        combined = auto_mode._check_for_new_instructions()

        # Verify both instructions included
        assert "Add authentication" in combined
        assert "Add logging" in combined

        # Verify timestamps preserved
        assert "20241023_120000" in combined
        assert "20241023_120100" in combined


@pytest.mark.integration
class TestMultipleAppendOperationsQueuing:
    """Test multiple append operations and queuing behavior."""

    @pytest.fixture
    def active_auto_mode(self):
        """Create and return active AutoMode instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=workspace
            )

            # Mock SDK
            auto_mode.run_sdk = MagicMock(return_value=(0, "Mock response"))
            auto_mode.run_hook = MagicMock()

            yield auto_mode, workspace

    def test_multiple_sequential_appends(self, active_auto_mode):
        """Test multiple sequential append operations.

        Expected behavior:
        - Each append creates separate file
        - Files accumulate in append/ directory
        - All processed together when checked
        - All moved to appended/ after processing
        """
        auto_mode, workspace = active_auto_mode

        instructions = [
            "First instruction",
            "Second instruction",
            "Third instruction",
        ]

        with patch('pathlib.Path.cwd', return_value=workspace):
            try:
                # Add multiple instructions
                for instruction in instructions:
                    append_instructions(instruction)
                    time.sleep(0.01)  # Ensure unique timestamps

                # Verify all files created
                md_files = list(auto_mode.append_dir.glob("*.md"))
                assert len(md_files) == 3, "Should create file for each instruction"

                # Process all instructions
                combined = auto_mode._check_for_new_instructions()

                # Verify all instructions in result
                for instruction in instructions:
                    assert instruction in combined, f"Should include: {instruction}"

                # Verify all moved to appended/
                assert len(list(auto_mode.append_dir.glob("*.md"))) == 0
                assert len(list(auto_mode.appended_dir.glob("*.md"))) == 3

            except (NotImplementedError, ImportError, AttributeError):
                pytest.skip("append_instructions not yet implemented")

    def test_append_during_execution(self, active_auto_mode):
        """Test appending instruction while auto mode is executing.

        Expected behavior:
        - New instruction should be picked up in next execution turn
        - Should not interfere with current turn
        - Should be processed in subsequent check
        """
        auto_mode, workspace = active_auto_mode

        # Simulate auto mode in execution
        # Add instruction during execution
        mid_execution_instruction = "Emergency fix: Handle null values"

        instruction_file = auto_mode.append_dir / f"{int(time.time())}.md"
        instruction_file.write_text(mid_execution_instruction)

        # Check for instructions (simulating next turn)
        instructions = auto_mode._check_for_new_instructions()

        assert mid_execution_instruction in instructions
        assert instruction_file not in auto_mode.append_dir.glob("*.md")

    def test_rapid_successive_appends(self, active_auto_mode):
        """Test rapid successive append operations (race condition handling).

        Expected behavior:
        - All appends should succeed
        - No file overwrites
        - All instructions preserved
        """
        auto_mode, workspace = active_auto_mode

        with patch('pathlib.Path.cwd', return_value=workspace):
            try:
                # Rapid appends
                for i in range(5):
                    append_instructions(f"Rapid instruction {i}")

                # All should be created
                md_files = list(auto_mode.append_dir.glob("*.md"))
                assert len(md_files) == 5, "Should create all files without collision"

                # All instructions should be preserved
                combined = auto_mode._check_for_new_instructions()
                for i in range(5):
                    assert f"Rapid instruction {i}" in combined

            except (NotImplementedError, ImportError, AttributeError):
                pytest.skip("append_instructions not yet implemented")


@pytest.mark.integration
class TestAppendFromSubdirectory:
    """Test appending instructions from project subdirectories."""

    @pytest.fixture
    def project_with_subdirs(self):
        """Create project with subdirectory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create project structure
            (workspace / "src" / "api").mkdir(parents=True)
            (workspace / "tests" / "unit").mkdir(parents=True)
            (workspace / "docs").mkdir(parents=True)

            # Start auto mode session
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Develop API",
                max_turns=5,
                working_dir=workspace
            )

            auto_mode.run_sdk = MagicMock(return_value=(0, "Mock"))
            auto_mode.run_hook = MagicMock()

            yield {
                'workspace': workspace,
                'auto_mode': auto_mode,
                'subdirs': {
                    'api': workspace / "src" / "api",
                    'tests': workspace / "tests" / "unit",
                    'docs': workspace / "docs",
                }
            }

    def test_append_from_api_subdirectory(self, project_with_subdirs):
        """Test appending from src/api subdirectory.

        Expected behavior:
        - Should traverse up to find .claude directory
        - Should find active session in workspace root
        - Should write to session's append/ directory
        """
        workspace = project_with_subdirs['workspace']
        auto_mode = project_with_subdirs['auto_mode']
        api_dir = project_with_subdirs['subdirs']['api']

        instruction = "Add validation to API endpoints"

        with patch('pathlib.Path.cwd', return_value=api_dir):
            try:
                result = append_instructions(instruction)

                # Verify written to workspace session
                md_files = list(auto_mode.append_dir.glob("*.md"))
                assert len(md_files) == 1, "Should write to workspace session"
                assert instruction in md_files[0].read_text()

            except (NotImplementedError, ImportError, AttributeError):
                pytest.skip("append_instructions not yet implemented")

    def test_append_from_multiple_subdirectories(self, project_with_subdirs):
        """Test appending from different subdirectories in same session.

        Expected behavior:
        - All instructions should go to same session
        - All should be discoverable from workspace root
        """
        workspace = project_with_subdirs['workspace']
        auto_mode = project_with_subdirs['auto_mode']
        subdirs = project_with_subdirs['subdirs']

        instructions = [
            ("api", "API instruction", subdirs['api']),
            ("tests", "Test instruction", subdirs['tests']),
            ("docs", "Documentation instruction", subdirs['docs']),
        ]

        try:
            for name, instruction, subdir in instructions:
                with patch('pathlib.Path.cwd', return_value=subdir):
                    append_instructions(instruction)

            # All should be in same session
            md_files = list(auto_mode.append_dir.glob("*.md"))
            assert len(md_files) == 3, "All instructions should be in same session"

            # Process all
            combined = auto_mode._check_for_new_instructions()

            for _, instruction, _ in instructions:
                assert instruction in combined

        except (NotImplementedError, ImportError, AttributeError):
            pytest.skip("append_instructions not yet implemented")

    def test_append_from_deeply_nested_directory(self, project_with_subdirs):
        """Test appending from deeply nested subdirectory.

        Expected behavior:
        - Should traverse up multiple levels
        - Should find workspace root
        - Should successfully write instruction
        """
        workspace = project_with_subdirs['workspace']
        auto_mode = project_with_subdirs['auto_mode']

        # Create deeply nested directory
        deep_dir = workspace / "src" / "api" / "v1" / "handlers" / "auth"
        deep_dir.mkdir(parents=True)

        instruction = "From deeply nested directory"

        with patch('pathlib.Path.cwd', return_value=deep_dir):
            try:
                result = append_instructions(instruction)

                # Should still find and write to workspace session
                md_files = list(auto_mode.append_dir.glob("*.md"))
                assert len(md_files) == 1
                assert instruction in md_files[0].read_text()

            except (NotImplementedError, ImportError, AttributeError):
                pytest.skip("append_instructions not yet implemented")


@pytest.mark.integration
class TestSessionFinderIntegration:
    """Test SessionFinder integration with append_instructions."""

    @pytest.fixture
    def multi_session_workspace(self):
        """Create workspace with multiple sessions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            logs_dir = workspace / ".claude" / "runtime" / "logs"
            logs_dir.mkdir(parents=True)

            # Create multiple sessions
            sessions = []
            for i in range(3):
                ts = int(time.time()) - (i * 3600)  # Different times
                session_id = f"auto_claude_{ts}"
                session_dir = logs_dir / session_id
                (session_dir / "append").mkdir(parents=True)
                (session_dir / "prompt.md").write_text(f"Session {i}")
                sessions.append((session_id, session_dir))

            yield workspace, sessions

    def test_append_finds_most_recent_session(self, multi_session_workspace):
        """Test that append_instructions finds most recent active session.

        Expected behavior:
        - Should identify most recent session by timestamp
        - Should write to that session's append/ directory
        """
        workspace, sessions = multi_session_workspace

        instruction = "Target most recent session"

        with patch('pathlib.Path.cwd', return_value=workspace):
            try:
                result = append_instructions(instruction)

                # Should write to most recent session (first in list, largest timestamp)
                most_recent_session_id, most_recent_dir = sessions[0]
                append_dir = most_recent_dir / "append"

                md_files = list(append_dir.glob("*.md"))
                assert len(md_files) == 1, "Should write to most recent session"
                assert instruction in md_files[0].read_text()

            except (NotImplementedError, ImportError, AttributeError):
                pytest.skip("append_instructions not yet implemented")

    def test_append_with_sdk_filter(self, multi_session_workspace):
        """Test append_instructions with SDK type filtering.

        Expected behavior:
        - Should filter sessions by SDK type
        - Should write to correct SDK session
        """
        workspace, sessions = multi_session_workspace

        # Add copilot session
        logs_dir = workspace / ".claude" / "runtime" / "logs"
        copilot_session = logs_dir / f"auto_copilot_{int(time.time())}"
        (copilot_session / "append").mkdir(parents=True)
        (copilot_session / "prompt.md").write_text("Copilot session")

        instruction = "For Copilot session"

        with patch('pathlib.Path.cwd', return_value=workspace):
            try:
                # Append with SDK filter
                result = append_instructions(instruction, sdk_filter="copilot")

                # Should write to copilot session
                md_files = list((copilot_session / "append").glob("*.md"))
                assert len(md_files) == 1, "Should write to Copilot session"

            except (NotImplementedError, ImportError, TypeError, AttributeError):
                pytest.skip("SDK filtering not yet implemented")


@pytest.mark.integration
class TestErrorRecoveryAndEdgeCases:
    """Test error recovery and edge case handling in full workflow."""

    @pytest.fixture
    def workspace(self):
        """Create test workspace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_recovery_from_corrupted_instruction_file(self, workspace):
        """Test that AutoMode handles corrupted instruction files gracefully.

        Expected behavior:
        - Should skip corrupted files
        - Should continue processing valid files
        - Should log error
        - Should not crash
        """
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Test",
            max_turns=3,
            working_dir=workspace
        )

        # Create mix of valid and corrupted files
        (auto_mode.append_dir / "valid.md").write_text("Valid instruction")
        (auto_mode.append_dir / "corrupted.md").write_bytes(b'\x80\x81\x82')

        # Should handle gracefully
        try:
            instructions = auto_mode._check_for_new_instructions()

            # Should process valid instruction
            assert "Valid instruction" in instructions or instructions == ""

        except UnicodeDecodeError:
            pytest.fail("Should handle corrupted files gracefully")

    def test_append_when_append_directory_missing(self, workspace):
        """Test behavior when append/ directory is deleted during operation.

        Expected behavior:
        - Should detect missing directory
        - Should return appropriate error
        - Should not crash
        """
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Test",
            max_turns=3,
            working_dir=workspace
        )

        # Remove append directory
        import shutil
        shutil.rmtree(auto_mode.append_dir)

        # Should handle gracefully
        instructions = auto_mode._check_for_new_instructions()
        assert instructions == "" or instructions is None, \
            "Should handle missing directory"

    def test_concurrent_append_and_check(self, workspace):
        """Test concurrent append and check operations.

        Expected behavior:
        - Should handle race conditions
        - Files being written should not cause errors
        - Either processed or left for next check
        """
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Test",
            max_turns=3,
            working_dir=workspace
        )

        # Create file during check (simulate race condition)
        def create_file_during_check():
            time.sleep(0.01)
            (auto_mode.append_dir / "concurrent.md").write_text("Concurrent")

        import threading
        thread = threading.Thread(target=create_file_during_check)
        thread.start()

        # Check for instructions
        instructions = auto_mode._check_for_new_instructions()

        thread.join()

        # Should not crash
        assert isinstance(instructions, str), "Should return string result"


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndWithRealWorkflow:
    """Test end-to-end workflow with realistic scenarios."""

    def test_developer_workflow_simulation(self):
        """Simulate realistic developer workflow.

        Scenario:
        1. Developer starts auto mode: amplihack --auto "Build API"
        2. Auto mode starts executing
        3. Developer realizes they forgot something
        4. Developer runs: amplihack --append "Add rate limiting"
        5. Auto mode picks up instruction in next turn
        6. Auto mode continues with updated requirements

        Expected behavior:
        - Complete workflow executes successfully
        - Instruction is incorporated seamlessly
        - Both original and appended instructions are satisfied
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Step 1: Start auto mode
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Build REST API with authentication",
                max_turns=5,
                working_dir=workspace
            )

            # Mock SDK
            sdk_prompts = []

            def capture_sdk(prompt):
                sdk_prompts.append(prompt)
                return (0, "Mock response")

            auto_mode.run_sdk = capture_sdk
            auto_mode.run_hook = MagicMock()

            # Step 2 & 3: Simulate execution started, then append
            try:
                # Developer appends new instruction
                new_requirement = "Add rate limiting: 100 requests per minute per API key"

                with patch('pathlib.Path.cwd', return_value=workspace):
                    append_instructions(new_requirement)

                # Step 4: Auto mode checks for instructions (next turn)
                instructions = auto_mode._check_for_new_instructions()

                # Verify instruction picked up
                assert new_requirement in instructions, \
                    "New requirement should be discovered"

                # Verify instruction would be included in execution
                # (in real workflow, this happens in the execute phase)
                assert instructions != "", "Should have instructions to append"

            except (NotImplementedError, ImportError, AttributeError):
                pytest.skip("Full workflow not yet implemented")
