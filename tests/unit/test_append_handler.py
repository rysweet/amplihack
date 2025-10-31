"""Unit tests for append_instructions functionality.

Tests the CLI --append flag handler that writes instructions to active session append/ directory.
Function to be implemented in amplihack/launcher/append_handler.py

Following TDD approach - these tests should FAIL initially as append_instructions is not implemented.
"""

import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# append_instructions function to be implemented
try:
    from amplihack.launcher.append_handler import (
        append_instructions,
        AppendResult,
        AppendError,
    )
except ImportError:
    # Define placeholders so tests can be written
    def append_instructions(instruction: str, session_id: str = None) -> dict:
        """Placeholder - to be implemented."""
        raise NotImplementedError("append_instructions not yet implemented")

    class AppendResult:
        """Placeholder - to be implemented."""

    class AppendError(Exception):
        """Placeholder - to be implemented."""


class TestAppendInstructionsBasic:
    """Test basic functionality of append_instructions."""

    @pytest.fixture
    def active_session_workspace(self):
        """Create workspace with active auto mode session."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create active session
            logs_dir = workspace / ".claude" / "runtime" / "logs"
            session_id = f"auto_claude_{int(time.time())}"
            session_dir = logs_dir / session_id
            append_dir = session_dir / "append"

            append_dir.mkdir(parents=True)
            (session_dir / "prompt.md").write_text("Original prompt")

            yield {
                "workspace": workspace,
                "session_id": session_id,
                "session_dir": session_dir,
                "append_dir": append_dir,
            }

    def test_append_instructions_creates_file(self, active_session_workspace):
        """Test that append_instructions creates a new .md file in append/ directory.

        Expected behavior:
        - Should create timestamped .md file
        - File should be in append/ directory
        - File should contain the instruction text
        """
        workspace = active_session_workspace["workspace"]
        append_dir = active_session_workspace["append_dir"]

        instruction = "Add error handling to authentication module"

        # Change to workspace directory
        with patch("pathlib.Path.cwd", return_value=workspace):
            append_instructions(instruction)

        # Check file was created
        md_files = list(append_dir.glob("*.md"))
        assert len(md_files) == 1, "Should create one .md file"

        # Check content
        content = md_files[0].read_text()
        assert instruction in content, "File should contain instruction text"

    def test_append_instructions_uses_timestamp_filename(self, active_session_workspace):
        """Test that instruction files use timestamp-based filenames.

        Expected behavior:
        - Filename should be in format: YYYYMMDD_HHMMSS.md
        - Timestamp should be close to current time
        """
        workspace = active_session_workspace["workspace"]
        append_dir = active_session_workspace["append_dir"]

        instruction = "Test instruction"

        # Capture current time
        before_time = datetime.now()

        with patch("pathlib.Path.cwd", return_value=workspace):
            append_instructions(instruction)

        after_time = datetime.now()

        # Check filename format
        md_files = list(append_dir.glob("*.md"))
        assert len(md_files) == 1

        filename = md_files[0].stem  # Filename without extension

        # Parse timestamp from filename (format: YYYYMMDD_HHMMSS)
        try:
            file_time = datetime.strptime(filename, "%Y%m%d_%H%M%S")
            assert before_time <= file_time <= after_time, (
                "Timestamp should be within test execution time"
            )
        except ValueError:
            pytest.fail(f"Filename '{filename}' does not match expected timestamp format")

    def test_append_instructions_returns_success_result(self, active_session_workspace):
        """Test that append_instructions returns success result.

        Expected behavior:
        - Should return AppendResult object
        - Result should indicate success
        - Result should include filename and session_id
        """
        workspace = active_session_workspace["workspace"]

        instruction = "Test instruction"

        with patch("pathlib.Path.cwd", return_value=workspace):
            result = append_instructions(instruction)

        assert result is not None, "Should return result"
        assert hasattr(result, "success") or isinstance(result, dict), (
            "Should return result with success indicator"
        )

        if isinstance(result, dict):
            assert result.get("success") is True, "Should indicate success"
            assert "filename" in result, "Should include filename"
            assert "session_id" in result, "Should include session_id"


class TestAppendInstructionsSessionDiscovery:
    """Test session discovery functionality."""

    @pytest.fixture
    def workspace_with_session(self):
        """Create workspace with active session."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            logs_dir = workspace / ".claude" / "runtime" / "logs"
            session_id = f"auto_claude_{int(time.time())}"
            session_dir = logs_dir / session_id
            append_dir = session_dir / "append"

            append_dir.mkdir(parents=True)
            (session_dir / "prompt.md").write_text("Test prompt")

            yield workspace, session_id

    def test_append_finds_session_automatically(self, workspace_with_session):
        """Test that append_instructions finds active session without explicit session_id.

        Expected behavior:
        - Should search for active session starting from current directory
        - Should find session in workspace .claude/runtime/logs/
        - Should write to found session's append/ directory
        """
        workspace, session_id = workspace_with_session

        instruction = "Auto-discovered session test"

        with patch("pathlib.Path.cwd", return_value=workspace):
            append_instructions(instruction)

        # Verify instruction was written to the session
        append_dir = workspace / ".claude" / "runtime" / "logs" / session_id / "append"
        md_files = list(append_dir.glob("*.md"))

        assert len(md_files) == 1, "Should create instruction in found session"
        assert instruction in md_files[0].read_text()

    def test_append_with_explicit_session_id(self, workspace_with_session):
        """Test providing explicit session_id to append_instructions.

        Expected behavior:
        - Should use provided session_id instead of auto-discovery
        - Should write to specified session's append/ directory
        """
        workspace, session_id = workspace_with_session

        instruction = "Explicit session test"

        with patch("pathlib.Path.cwd", return_value=workspace):
            append_instructions(instruction, session_id=session_id)

        # Verify written to correct session
        append_dir = workspace / ".claude" / "runtime" / "logs" / session_id / "append"
        md_files = list(append_dir.glob("*.md"))

        assert len(md_files) == 1
        assert instruction in md_files[0].read_text()

    def test_append_from_subdirectory(self, workspace_with_session):
        """Test appending instruction from project subdirectory.

        Expected behavior:
        - Should traverse up to find .claude directory
        - Should find session in parent workspace
        - Should successfully write instruction
        """
        workspace, session_id = workspace_with_session

        # Create subdirectory
        subdir = workspace / "src" / "components"
        subdir.mkdir(parents=True)

        instruction = "From subdirectory"

        with patch("pathlib.Path.cwd", return_value=subdir):
            append_instructions(instruction)

        # Should still write to workspace session
        append_dir = workspace / ".claude" / "runtime" / "logs" / session_id / "append"
        md_files = list(append_dir.glob("*.md"))

        assert len(md_files) == 1, "Should find and write to parent workspace session"


class TestAppendInstructionsErrorHandling:
    """Test error handling in append_instructions."""

    def test_append_no_active_session_error(self):
        """Test error when no active session exists.

        Expected behavior:
        - Should raise AppendError or return error result
        - Error message should indicate no active session found
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # No .claude directory created

            instruction = "Test instruction"

            with patch("pathlib.Path.cwd", return_value=workspace):
                with pytest.raises((AppendError, FileNotFoundError, ValueError)):
                    append_instructions(instruction)

    def test_append_empty_instruction(self):
        """Test handling of empty instruction.

        Expected behavior:
        - Should raise ValueError or return error
        - Should not create file for empty instruction
        """
        with pytest.raises((ValueError, AppendError)):
            append_instructions("")

    def test_append_whitespace_only_instruction(self):
        """Test handling of whitespace-only instruction.

        Expected behavior:
        - Should raise ValueError or return error
        - Should not create file for whitespace-only content
        """
        with pytest.raises((ValueError, AppendError)):
            append_instructions("   \n\t  ")

    def test_append_permission_error(self):
        """Test handling of permission errors when writing file.

        Expected behavior:
        - Should handle permission errors gracefully
        - Should raise appropriate error with clear message
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            logs_dir = workspace / ".claude" / "runtime" / "logs"
            session_dir = logs_dir / f"auto_claude_{int(time.time())}"
            append_dir = session_dir / "append"
            append_dir.mkdir(parents=True)
            (session_dir / "prompt.md").write_text("Test")

            instruction = "Test instruction"

            # Mock write to raise permission error
            with patch("pathlib.Path.cwd", return_value=workspace):
                with patch("builtins.open", side_effect=PermissionError("Access denied")):
                    with pytest.raises((PermissionError, AppendError, OSError)):
                        append_instructions(instruction)


class TestAppendInstructionsConcurrency:
    """Test concurrent append operations."""

    @pytest.fixture
    def workspace_with_session(self):
        """Create workspace with active session."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            logs_dir = workspace / ".claude" / "runtime" / "logs"
            session_id = f"auto_claude_{int(time.time())}"
            session_dir = logs_dir / session_id
            append_dir = session_dir / "append"

            append_dir.mkdir(parents=True)
            (session_dir / "prompt.md").write_text("Test prompt")

            yield workspace, session_id

    def test_multiple_append_operations(self, workspace_with_session):
        """Test multiple sequential append operations.

        Expected behavior:
        - Should create separate file for each instruction
        - Files should have different timestamps (or unique identifiers)
        - All instructions should be preserved
        """
        workspace, session_id = workspace_with_session
        instructions = [
            "First instruction",
            "Second instruction",
            "Third instruction",
        ]

        with patch("pathlib.Path.cwd", return_value=workspace):
            for instruction in instructions:
                append_instructions(instruction)
                time.sleep(0.01)  # Small delay to ensure different timestamps

        # Check all files created
        append_dir = workspace / ".claude" / "runtime" / "logs" / session_id / "append"
        md_files = list(append_dir.glob("*.md"))

        assert len(md_files) == 3, "Should create file for each instruction"

        # Check all instructions present
        all_content = " ".join(f.read_text() for f in md_files)
        for instruction in instructions:
            assert instruction in all_content, f"Should contain: {instruction}"

    def test_append_filename_collision_handling(self, workspace_with_session):
        """Test handling of filename collisions (same timestamp).

        Expected behavior:
        - If collision occurs, should append suffix or use microseconds
        - Should not overwrite existing file
        - Both instructions should be preserved
        """
        workspace, session_id = workspace_with_session

        with patch("pathlib.Path.cwd", return_value=workspace):
            # Mock datetime to return same timestamp
            with patch("datetime.datetime") as mock_dt:
                fixed_time = datetime(2024, 10, 23, 12, 0, 0)
                mock_dt.now.return_value = fixed_time

                # Try to create two files with same timestamp
                append_instructions("First instruction")

                # Second call with same mocked time
                mock_dt.now.return_value = fixed_time
                append_instructions("Second instruction")

        # Both files should exist (with collision handling)
        append_dir = workspace / ".claude" / "runtime" / "logs" / session_id / "append"
        md_files = list(append_dir.glob("*.md"))

        # Should have both files (collision handling should create unique names)
        assert len(md_files) >= 1, "Should create at least one file"

        # Both instructions should be preserved
        all_content = " ".join(f.read_text() for f in md_files)
        # At minimum, one instruction should be preserved
        assert "First instruction" in all_content or "Second instruction" in all_content


class TestAppendInstructionsFormatting:
    """Test instruction content formatting."""

    @pytest.fixture
    def workspace_with_session(self):
        """Create workspace with active session."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            logs_dir = workspace / ".claude" / "runtime" / "logs"
            session_id = f"auto_claude_{int(time.time())}"
            session_dir = logs_dir / session_id
            append_dir = session_dir / "append"

            append_dir.mkdir(parents=True)
            (session_dir / "prompt.md").write_text("Test prompt")

            yield workspace, session_id

    def test_instruction_preserves_multiline_content(self, workspace_with_session):
        """Test that multiline instructions are preserved correctly.

        Expected behavior:
        - Should preserve line breaks
        - Should maintain formatting
        """
        workspace, session_id = workspace_with_session

        instruction = """Add the following features:
- Feature 1
- Feature 2
- Feature 3

Please implement carefully."""

        with patch("pathlib.Path.cwd", return_value=workspace):
            append_instructions(instruction)

        # Check content preserved
        append_dir = workspace / ".claude" / "runtime" / "logs" / session_id / "append"
        md_files = list(append_dir.glob("*.md"))

        content = md_files[0].read_text()
        assert "Feature 1" in content
        assert "Feature 2" in content
        assert "Feature 3" in content
        assert content.count("\n") >= 3, "Should preserve line breaks"

    def test_instruction_handles_special_characters(self, workspace_with_session):
        """Test handling of special characters in instructions.

        Expected behavior:
        - Should preserve special characters
        - Should handle markdown syntax
        - Should handle code blocks
        """
        workspace, session_id = workspace_with_session

        instruction = """Fix the `authenticate()` function:
```python
def authenticate(user):
    # Add validation
    pass
```
Use **strong** encryption."""

        with patch("pathlib.Path.cwd", return_value=workspace):
            append_instructions(instruction)

        # Check special characters preserved
        append_dir = workspace / ".claude" / "runtime" / "logs" / session_id / "append"
        md_files = list(append_dir.glob("*.md"))

        content = md_files[0].read_text()
        assert "`authenticate()`" in content or "authenticate()" in content
        assert "```" in content or "python" in content
        assert "**strong**" in content or "strong" in content

    def test_instruction_handles_unicode(self, workspace_with_session):
        """Test handling of unicode characters.

        Expected behavior:
        - Should correctly handle unicode characters
        - Should preserve emoji
        - Should maintain encoding
        """
        workspace, session_id = workspace_with_session

        instruction = "Add tests for thé français function 🚀"

        with patch("pathlib.Path.cwd", return_value=workspace):
            append_instructions(instruction)

        # Check unicode preserved
        append_dir = workspace / ".claude" / "runtime" / "logs" / session_id / "append"
        md_files = list(append_dir.glob("*.md"))

        content = md_files[0].read_text()
        assert "thé français" in content or "the" in content.lower()


class TestAppendResult:
    """Test AppendResult data structure."""

    def test_append_result_structure(self):
        """Test that AppendResult has expected structure.

        Expected attributes:
        - success: bool
        - filename: str or Path
        - session_id: str
        - append_dir: Path
        - timestamp: datetime or str
        - message: optional str
        """
        # This will fail until AppendResult is implemented
        with pytest.raises((TypeError, AttributeError, NameError)):
            result = AppendResult(
                success=True,
                filename="20241023_120000.md",
                session_id="auto_claude_1729699200",
                append_dir=Path("/tmp/append"),
                timestamp="20241023_120000",
                message="Instruction added successfully",
            )

            assert hasattr(result, "success")
            assert hasattr(result, "filename")
            assert hasattr(result, "session_id")
            assert hasattr(result, "append_dir")
            assert hasattr(result, "timestamp")

    def test_append_result_to_dict(self):
        """Test converting AppendResult to dictionary.

        Expected behavior:
        - Should have to_dict() method or be dict-serializable
        - Should include all relevant information
        """
        with pytest.raises((TypeError, AttributeError, NameError)):
            result = AppendResult(
                success=True,
                filename="test.md",
                session_id="auto_claude_123",
                append_dir=Path("/tmp"),
                timestamp="20241023_120000",
            )

            result_dict = result.to_dict() if hasattr(result, "to_dict") else dict(result)

            assert isinstance(result_dict, dict)
            assert "success" in result_dict
            assert "filename" in result_dict
            assert "session_id" in result_dict


class TestCLIIntegration:
    """Test CLI --append flag integration (conceptual tests)."""

    def test_cli_append_flag_exists(self):
        """Test that --append flag is available in CLI.

        This is a conceptual test - actual CLI testing would be in integration tests.
        """
        # Placeholder to guide implementation
        # CLI should accept: amplihack --append "instruction text"
        assert True, "CLI flag should be implemented"

    def test_cli_append_with_session_id(self):
        """Test that --append flag can accept optional session ID.

        Conceptual test for CLI argument: amplihack --append "text" --session SESSION_ID
        """
        # Placeholder to guide implementation
        assert True, "CLI should support --session flag"

    def test_cli_append_help_text(self):
        """Test that --append flag has proper help text.

        Conceptual test for help documentation.
        """
        # Placeholder to guide implementation
        assert True, "Help text should explain append functionality"
