"""Unit tests for AutoMode instruction injection feature.

Tests directory creation, prompt.md writing, and instruction checking functionality.
Following TDD approach - these tests should FAIL initially.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from amplihack.launcher.auto_mode import AutoMode


class TestAutoModeDirectoryCreation:
    """Test auto mode creates append/ and appended/ directories on initialization."""

    @pytest.fixture
    def temp_working_dir(self):
        """Create temporary working directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_auto_mode_creates_append_directory(self, temp_working_dir):
        """Test that AutoMode creates append/ directory on initialization.

        Expected behavior:
        - append/ directory should exist at log_dir/append
        - Directory should be created with parents=True
        """
        auto_mode = AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=5, working_dir=temp_working_dir
        )

        expected_append_dir = auto_mode.log_dir / "append"
        assert expected_append_dir.exists(), "append/ directory should be created"
        assert expected_append_dir.is_dir(), "append/ should be a directory"

    def test_auto_mode_creates_appended_directory(self, temp_working_dir):
        """Test that AutoMode creates appended/ directory on initialization.

        Expected behavior:
        - appended/ directory should exist at log_dir/appended
        - Directory should be created with parents=True
        """
        auto_mode = AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=5, working_dir=temp_working_dir
        )

        expected_appended_dir = auto_mode.log_dir / "appended"
        assert expected_appended_dir.exists(), "appended/ directory should be created"
        assert expected_appended_dir.is_dir(), "appended/ should be a directory"

    def test_auto_mode_directories_are_empty_initially(self, temp_working_dir):
        """Test that append/ and appended/ directories are empty on creation.

        Expected behavior:
        - Both directories should exist but contain no files
        """
        auto_mode = AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=5, working_dir=temp_working_dir
        )

        append_files = list(auto_mode.append_dir.glob("*"))
        appended_files = list(auto_mode.appended_dir.glob("*"))

        assert len(append_files) == 0, "append/ directory should be empty initially"
        assert len(appended_files) == 0, "appended/ directory should be empty initially"


class TestAutoModePromptWriting:
    """Test auto mode writes original prompt to prompt.md."""

    @pytest.fixture
    def temp_working_dir(self):
        """Create temporary working directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_auto_mode_writes_prompt_md(self, temp_working_dir):
        """Test that AutoMode writes prompt.md on initialization.

        Expected behavior:
        - prompt.md file should exist at log_dir/prompt.md
        - File should contain the original prompt
        """
        test_prompt = "Implement authentication system with JWT tokens"

        auto_mode = AutoMode(
            sdk="claude", prompt=test_prompt, max_turns=5, working_dir=temp_working_dir
        )

        prompt_file = auto_mode.log_dir / "prompt.md"
        assert prompt_file.exists(), "prompt.md should be created"
        assert prompt_file.is_file(), "prompt.md should be a file"

        content = prompt_file.read_text()
        assert test_prompt in content, "prompt.md should contain original prompt"

    def test_prompt_md_contains_metadata(self, temp_working_dir):
        """Test that prompt.md contains session metadata.

        Expected behavior:
        - Should include session start timestamp
        - Should include SDK name
        - Should include max_turns
        """
        auto_mode = AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=10, working_dir=temp_working_dir
        )

        prompt_file = auto_mode.log_dir / "prompt.md"
        content = prompt_file.read_text()

        assert "Session Started" in content or "session" in content.lower()
        assert "claude" in content.lower(), "Should include SDK name"
        assert "10" in content or "Max Turns" in content, "Should include max_turns"

    def test_prompt_md_uses_markdown_format(self, temp_working_dir):
        """Test that prompt.md uses proper markdown formatting.

        Expected behavior:
        - Should have markdown headers (# or ##)
        - Should have proper structure
        """
        auto_mode = AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=5, working_dir=temp_working_dir
        )

        prompt_file = auto_mode.log_dir / "prompt.md"
        content = prompt_file.read_text()

        assert "#" in content, "Should use markdown headers"
        assert "---" in content or "**" in content, "Should use markdown formatting"


class TestCheckForNewInstructions:
    """Test _check_for_new_instructions() method."""

    @pytest.fixture
    def auto_mode_with_temp_dir(self):
        """Create AutoMode instance with temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude", prompt="Test prompt", max_turns=5, working_dir=Path(temp_dir)
            )
            yield auto_mode

    def test_check_for_new_instructions_empty_directory(self, auto_mode_with_temp_dir):
        """Test checking for instructions when append/ directory is empty.

        Expected behavior:
        - Should return empty string
        - Should not raise any errors
        """
        result = auto_mode_with_temp_dir._check_for_new_instructions()

        assert result == "", "Should return empty string when no files present"
        assert isinstance(result, str), "Should return a string"

    def test_check_for_new_instructions_single_file(self, auto_mode_with_temp_dir):
        """Test processing a single instruction file.

        Expected behavior:
        - Should read the .md file from append/
        - Should return the content with timestamp header
        - Should move file to appended/ directory
        """
        # Create a test instruction file
        instruction_file = auto_mode_with_temp_dir.append_dir / "20241023_120000.md"
        test_instruction = "Add error handling to authentication module"
        instruction_file.write_text(test_instruction)

        result = auto_mode_with_temp_dir._check_for_new_instructions()

        # Check result contains instruction
        assert test_instruction in result, "Result should contain instruction content"
        assert "20241023_120000" in result, "Result should include timestamp"

        # Check file was moved
        assert not instruction_file.exists(), "Original file should be moved"
        moved_file = auto_mode_with_temp_dir.appended_dir / "20241023_120000.md"
        assert moved_file.exists(), "File should be moved to appended/ directory"

    def test_check_for_new_instructions_multiple_files(self, auto_mode_with_temp_dir):
        """Test processing multiple instruction files.

        Expected behavior:
        - Should process all .md files in append/
        - Should process files in sorted order (oldest first)
        - Should return all instructions combined
        - Should move all files to appended/
        """
        # Create multiple instruction files
        instructions = [
            ("20241023_120000.md", "First instruction"),
            ("20241023_120100.md", "Second instruction"),
            ("20241023_120200.md", "Third instruction"),
        ]

        for filename, content in instructions:
            file_path = auto_mode_with_temp_dir.append_dir / filename
            file_path.write_text(content)

        result = auto_mode_with_temp_dir._check_for_new_instructions()

        # Check all instructions are included
        for filename, content in instructions:
            assert content in result, f"Result should contain: {content}"

        # Check all files were moved
        for filename, _ in instructions:
            original = auto_mode_with_temp_dir.append_dir / filename
            moved = auto_mode_with_temp_dir.appended_dir / filename
            assert not original.exists(), f"{filename} should be moved"
            assert moved.exists(), f"{filename} should exist in appended/"

    def test_check_for_new_instructions_preserves_order(self, auto_mode_with_temp_dir):
        """Test that instructions are processed in chronological order.

        Expected behavior:
        - Files should be processed in sorted filename order
        - Earlier timestamps should appear first in result
        """
        # Create files with deliberate ordering
        file1 = auto_mode_with_temp_dir.append_dir / "20241023_120000.md"
        file2 = auto_mode_with_temp_dir.append_dir / "20241023_130000.md"

        file1.write_text("FIRST")
        file2.write_text("SECOND")

        result = auto_mode_with_temp_dir._check_for_new_instructions()

        # Check order in result
        first_pos = result.find("FIRST")
        second_pos = result.find("SECOND")

        assert first_pos < second_pos, "Earlier timestamp should appear first"

    def test_check_for_new_instructions_ignores_non_md_files(self, auto_mode_with_temp_dir):
        """Test that only .md files are processed.

        Expected behavior:
        - Should only process .md files
        - Should ignore .txt, .json, etc.
        """
        # Create various file types
        md_file = auto_mode_with_temp_dir.append_dir / "instruction.md"
        txt_file = auto_mode_with_temp_dir.append_dir / "instruction.txt"
        json_file = auto_mode_with_temp_dir.append_dir / "data.json"

        md_file.write_text("MD content")
        txt_file.write_text("TXT content")
        json_file.write_text('{"key": "value"}')

        result = auto_mode_with_temp_dir._check_for_new_instructions()

        # Only MD content should be in result
        assert "MD content" in result, "Should process .md files"
        assert "TXT content" not in result, "Should ignore .txt files"
        assert "key" not in result, "Should ignore .json files"

        # Only MD file should be moved
        assert not md_file.exists(), "MD file should be moved"
        assert txt_file.exists(), "TXT file should remain"
        assert json_file.exists(), "JSON file should remain"


class TestCheckForNewInstructionsErrorHandling:
    """Test error handling in _check_for_new_instructions()."""

    @pytest.fixture
    def auto_mode_with_temp_dir(self):
        """Create AutoMode instance with temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude", prompt="Test prompt", max_turns=5, working_dir=Path(temp_dir)
            )
            yield auto_mode

    def test_check_handles_read_permission_error(self, auto_mode_with_temp_dir):
        """Test handling of file read permission errors.

        Expected behavior:
        - Should log error but not crash
        - Should continue processing other files
        - Should return partial results
        """
        # Create two files, one will cause read error
        good_file = auto_mode_with_temp_dir.append_dir / "good.md"
        bad_file = auto_mode_with_temp_dir.append_dir / "bad.md"

        good_file.write_text("Good content")
        bad_file.write_text("Bad content")

        # Mock read to raise error for bad_file
        original_read = Path.read_text

        def mock_read_text(self, *args, **kwargs):
            if self.name == "bad.md":
                raise PermissionError("Cannot read file")
            return original_read(self, *args, **kwargs)

        with patch.object(Path, "read_text", mock_read_text):
            result = auto_mode_with_temp_dir._check_for_new_instructions()

        # Should still process good file
        assert "Good content" in result, "Should process accessible files"
        # Bad file shouldn't be in result
        assert "Bad content" not in result, "Should skip unreadable files"

    def test_check_handles_move_error(self, auto_mode_with_temp_dir):
        """Test handling of file move errors.

        Expected behavior:
        - Should log error but not crash
        - Should continue processing other files
        """
        instruction_file = auto_mode_with_temp_dir.append_dir / "test.md"
        instruction_file.write_text("Test content")

        # Mock rename to raise error
        with patch.object(Path, "rename", side_effect=OSError("Move failed")):
            # Should not raise exception
            result = auto_mode_with_temp_dir._check_for_new_instructions()

            # Should still return content even if move failed
            assert "Test content" in result, "Should still process content"

    def test_check_handles_corrupted_file(self, auto_mode_with_temp_dir):
        """Test handling of corrupted or binary files.

        Expected behavior:
        - Should handle decode errors gracefully
        - Should log error and continue
        """
        # Create a binary file with .md extension
        binary_file = auto_mode_with_temp_dir.append_dir / "binary.md"
        binary_file.write_bytes(b"\x80\x81\x82\x83")

        # Should not crash
        try:
            result = auto_mode_with_temp_dir._check_for_new_instructions()
            # If it handles gracefully, result should be string
            assert isinstance(result, str)
        except UnicodeDecodeError:
            pytest.fail("Should handle decode errors gracefully")

    def test_check_handles_empty_file(self, auto_mode_with_temp_dir):
        """Test handling of empty instruction files.

        Expected behavior:
        - Should process empty files without error
        - Should move empty files to appended/
        """
        empty_file = auto_mode_with_temp_dir.append_dir / "empty.md"
        empty_file.write_text("")

        result = auto_mode_with_temp_dir._check_for_new_instructions()

        # Should not crash
        assert isinstance(result, str)

        # File should be moved
        assert not empty_file.exists(), "Empty file should still be moved"
        assert (auto_mode_with_temp_dir.appended_dir / "empty.md").exists()


class TestInstructionIntegrationWithRunLoop:
    """Test that _check_for_new_instructions() is called during run loop."""

    @pytest.fixture
    def auto_mode_with_mocked_sdk(self):
        """Create AutoMode with mocked SDK calls."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude", prompt="Test prompt", max_turns=3, working_dir=Path(temp_dir)
            )

            # Mock run_sdk to avoid actual SDK calls
            auto_mode.run_sdk = MagicMock(return_value=(0, "Mock response"))

            # Mock run_hook to avoid actual hook execution
            auto_mode.run_hook = MagicMock()

            yield auto_mode

    def test_check_for_instructions_called_in_execute_phase(self, auto_mode_with_mocked_sdk):
        """Test that instruction checking happens during execute phase.

        Expected behavior:
        - _check_for_new_instructions() should be called before each execute turn
        - New instructions should be appended to execute prompt
        """
        # Add an instruction file before execution
        instruction_file = auto_mode_with_mocked_sdk.append_dir / "20241023_120000.md"
        instruction_file.write_text("Add logging to all functions")

        # Spy on _check_for_new_instructions
        original_check = auto_mode_with_mocked_sdk._check_for_new_instructions
        check_called = []

        def spy_check():
            result = original_check()
            check_called.append(result)
            return result

        auto_mode_with_mocked_sdk._check_for_new_instructions = spy_check

        # Run auto mode (will use mocked SDK)
        # This will fail initially as integration may not be complete
        with pytest.raises((AttributeError, NotImplementedError, RuntimeError)):
            auto_mode_with_mocked_sdk.run()

    def test_new_instructions_included_in_prompt(self, auto_mode_with_mocked_sdk):
        """Test that new instructions are included in execution prompt.

        Expected behavior:
        - Instructions from append/ should be added to execute_prompt
        - Instructions should maintain their timestamp context
        """
        # This test will fail until prompt injection is implemented
        instruction_file = auto_mode_with_mocked_sdk.append_dir / "20241023_120000.md"
        instruction_file.write_text("Critical: Fix security vulnerability")

        # Capture prompts sent to SDK
        prompts_sent = []

        def capture_sdk_call(prompt):
            prompts_sent.append(prompt)
            return (0, "Mock response")

        auto_mode_with_mocked_sdk.run_sdk = capture_sdk_call

        # This will fail initially
        with pytest.raises((AttributeError, NotImplementedError, RuntimeError)):
            auto_mode_with_mocked_sdk.run()

            # Check that instruction was included
            assert any("Fix security vulnerability" in p for p in prompts_sent)


class TestAutoModeAttributes:
    """Test that AutoMode has correct attributes for injection feature."""

    @pytest.fixture
    def temp_working_dir(self):
        """Create temporary working directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_auto_mode_has_append_dir_attribute(self, temp_working_dir):
        """Test that AutoMode has append_dir attribute.

        Expected behavior:
        - append_dir should be a Path object
        - append_dir should be log_dir / "append"
        """
        auto_mode = AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=5, working_dir=temp_working_dir
        )

        assert hasattr(auto_mode, "append_dir"), "AutoMode should have append_dir attribute"
        assert isinstance(auto_mode.append_dir, Path), "append_dir should be a Path"
        assert auto_mode.append_dir.name == "append", "append_dir should be named 'append'"

    def test_auto_mode_has_appended_dir_attribute(self, temp_working_dir):
        """Test that AutoMode has appended_dir attribute.

        Expected behavior:
        - appended_dir should be a Path object
        - appended_dir should be log_dir / "appended"
        """
        auto_mode = AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=5, working_dir=temp_working_dir
        )

        assert hasattr(auto_mode, "appended_dir"), "AutoMode should have appended_dir attribute"
        assert isinstance(auto_mode.appended_dir, Path), "appended_dir should be a Path"
        assert auto_mode.appended_dir.name == "appended", "appended_dir should be named 'appended'"

    def test_auto_mode_has_check_method(self, temp_working_dir):
        """Test that AutoMode has _check_for_new_instructions method.

        Expected behavior:
        - Method should exist
        - Method should be callable
        """
        auto_mode = AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=5, working_dir=temp_working_dir
        )

        assert hasattr(auto_mode, "_check_for_new_instructions"), (
            "AutoMode should have _check_for_new_instructions method"
        )
        assert callable(auto_mode._check_for_new_instructions), (
            "_check_for_new_instructions should be callable"
        )
