"""Tests for AutoStager - TDD approach.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import os
import shutil
from pathlib import Path
from unittest.mock import patch

from amplihack.launcher.auto_stager import (
    AutoStager,
    StagingResult,
)


# UNIT TESTS (60%)
class TestStagingResult:
    """Test StagingResult dataclass creation"""

    def test_staging_result_creation(self):
        """Test creating a StagingResult with all fields"""
        result = StagingResult(
            temp_root=Path("/tmp/amplihack-stage-123"),
            staged_claude=Path("/tmp/amplihack-stage-123/.claude"),
            original_cwd=Path("/home/user/project"),
        )

        assert result.temp_root == Path("/tmp/amplihack-stage-123")
        assert result.staged_claude == Path("/tmp/amplihack-stage-123/.claude")
        assert result.original_cwd == Path("/home/user/project")


class TestAutoStagerInit:
    """Test AutoStager initialization"""

    def test_auto_stager_initializes(self):
        """Test that AutoStager can be instantiated"""
        stager = AutoStager()
        assert stager is not None


class TestTempDirectoryCreation:
    """Test temporary directory creation"""

    @patch("tempfile.mkdtemp")
    def test_creates_temp_directory(self, mock_mkdtemp, tmp_path):
        """Test that stage_for_nested_execution creates temp directory"""
        temp_dir = tmp_path / "temp-stage-123"
        mock_mkdtemp.return_value = str(temp_dir)
        temp_dir.mkdir()

        # Create a minimal .claude structure
        original_cwd = tmp_path / "original"
        original_cwd.mkdir()
        claude_dir = original_cwd / ".claude"
        claude_dir.mkdir()
        (claude_dir / "context").mkdir()

        stager = AutoStager()
        result = stager.stage_for_nested_execution(original_cwd, "session-123")

        assert mock_mkdtemp.called
        assert "amplihack-stage-session-123" in mock_mkdtemp.call_args[1]["prefix"]

    def test_temp_directory_has_claude_subdir(self, tmp_path):
        """Test that staged directory has .claude subdirectory"""
        # Create source .claude structure
        original_cwd = tmp_path / "original"
        original_cwd.mkdir()
        claude_dir = original_cwd / ".claude"
        claude_dir.mkdir()
        (claude_dir / "context").mkdir()

        stager = AutoStager()
        result = stager.stage_for_nested_execution(original_cwd, "session-123")

        assert result.staged_claude.exists()
        assert result.staged_claude.is_dir()
        assert result.staged_claude.name == ".claude"


class TestClaudeDirectoryCopying:
    """Test _copy_claude_directory method"""

    def test_copies_agents_directory(self, tmp_path):
        """Test that agents/ directory is copied"""
        source = tmp_path / "source" / ".claude"
        dest = tmp_path / "dest" / ".claude"

        source.mkdir(parents=True)
        agents_dir = source / "agents"
        agents_dir.mkdir()
        (agents_dir / "test.md").write_text("test agent")

        dest.mkdir(parents=True)

        stager = AutoStager()
        stager._copy_claude_directory(source, dest)

        assert (dest / "agents" / "test.md").exists()
        assert (dest / "agents" / "test.md").read_text() == "test agent"

    def test_copies_commands_directory(self, tmp_path):
        """Test that commands/ directory is copied"""
        source = tmp_path / "source" / ".claude"
        dest = tmp_path / "dest" / ".claude"

        source.mkdir(parents=True)
        commands_dir = source / "commands"
        commands_dir.mkdir()
        (commands_dir / "test.sh").write_text("#!/bin/bash")

        dest.mkdir(parents=True)

        stager = AutoStager()
        stager._copy_claude_directory(source, dest)

        assert (dest / "commands" / "test.sh").exists()

    def test_copies_skills_directory(self, tmp_path):
        """Test that skills/ directory is copied"""
        source = tmp_path / "source" / ".claude"
        dest = tmp_path / "dest" / ".claude"

        source.mkdir(parents=True)
        skills_dir = source / "skills"
        skills_dir.mkdir()
        (skills_dir / "skill.md").write_text("skill content")

        dest.mkdir(parents=True)

        stager = AutoStager()
        stager._copy_claude_directory(source, dest)

        assert (dest / "skills" / "skill.md").exists()

    def test_copies_tools_directory(self, tmp_path):
        """Test that tools/ directory is copied"""
        source = tmp_path / "source" / ".claude"
        dest = tmp_path / "dest" / ".claude"

        source.mkdir(parents=True)
        tools_dir = source / "tools"
        tools_dir.mkdir()
        (tools_dir / "tool.py").write_text("# tool")

        dest.mkdir(parents=True)

        stager = AutoStager()
        stager._copy_claude_directory(source, dest)

        assert (dest / "tools" / "tool.py").exists()

    def test_copies_workflow_directory(self, tmp_path):
        """Test that workflow/ directory is copied"""
        source = tmp_path / "source" / ".claude"
        dest = tmp_path / "dest" / ".claude"

        source.mkdir(parents=True)
        workflow_dir = source / "workflow"
        workflow_dir.mkdir()
        (workflow_dir / "DEFAULT_WORKFLOW.md").write_text("workflow")

        dest.mkdir(parents=True)

        stager = AutoStager()
        stager._copy_claude_directory(source, dest)

        assert (dest / "workflow" / "DEFAULT_WORKFLOW.md").exists()

    def test_copies_context_directory(self, tmp_path):
        """Test that context/ directory is copied"""
        source = tmp_path / "source" / ".claude"
        dest = tmp_path / "dest" / ".claude"

        source.mkdir(parents=True)
        context_dir = source / "context"
        context_dir.mkdir()
        (context_dir / "PHILOSOPHY.md").write_text("philosophy")

        dest.mkdir(parents=True)

        stager = AutoStager()
        stager._copy_claude_directory(source, dest)

        assert (dest / "context" / "PHILOSOPHY.md").exists()

    def test_does_not_copy_runtime_directory(self, tmp_path):
        """Test that runtime/ directory is NOT copied"""
        source = tmp_path / "source" / ".claude"
        dest = tmp_path / "dest" / ".claude"

        source.mkdir(parents=True)
        runtime_dir = source / "runtime"
        runtime_dir.mkdir()
        (runtime_dir / "sessions.jsonl").write_text("session data")

        dest.mkdir(parents=True)

        stager = AutoStager()
        stager._copy_claude_directory(source, dest)

        assert not (dest / "runtime").exists()
        assert not (dest / "runtime" / "sessions.jsonl").exists()

    def test_handles_missing_directories_gracefully(self, tmp_path):
        """Test graceful handling when source directories don't exist"""
        source = tmp_path / "source" / ".claude"
        dest = tmp_path / "dest" / ".claude"

        source.mkdir(parents=True)
        # Don't create any subdirectories

        dest.mkdir(parents=True)

        stager = AutoStager()
        # Should not crash
        stager._copy_claude_directory(source, dest)

        # Dest should exist but be mostly empty
        assert dest.exists()


# INTEGRATION TESTS (30%)
class TestStagingIntegration:
    """Test full staging workflow"""

    def test_complete_staging_flow(self, tmp_path):
        """Test complete staging workflow with all directories"""
        # Setup source .claude structure
        original_cwd = tmp_path / "original"
        original_cwd.mkdir()
        claude_dir = original_cwd / ".claude"
        claude_dir.mkdir()

        # Create all directories
        (claude_dir / "agents").mkdir()
        (claude_dir / "agents" / "agent.md").write_text("agent")

        (claude_dir / "commands").mkdir()
        (claude_dir / "commands" / "cmd.sh").write_text("command")

        (claude_dir / "skills").mkdir()
        (claude_dir / "skills" / "skill.md").write_text("skill")

        (claude_dir / "tools").mkdir()
        (claude_dir / "tools" / "tool.py").write_text("tool")

        (claude_dir / "workflow").mkdir()
        (claude_dir / "workflow" / "workflow.md").write_text("workflow")

        (claude_dir / "context").mkdir()
        (claude_dir / "context" / "PHILOSOPHY.md").write_text("philosophy")

        # Create runtime (should NOT be copied)
        (claude_dir / "runtime").mkdir()
        (claude_dir / "runtime" / "sessions.jsonl").write_text("sessions")

        stager = AutoStager()
        result = stager.stage_for_nested_execution(original_cwd, "test-session")

        # Verify structure
        assert result.staged_claude.exists()
        assert (result.staged_claude / "agents" / "agent.md").exists()
        assert (result.staged_claude / "commands" / "cmd.sh").exists()
        assert (result.staged_claude / "skills" / "skill.md").exists()
        assert (result.staged_claude / "tools" / "tool.py").exists()
        assert (result.staged_claude / "workflow" / "workflow.md").exists()
        assert (result.staged_claude / "context" / "PHILOSOPHY.md").exists()

        # Verify runtime NOT copied
        assert not (result.staged_claude / "runtime").exists()

    def test_staging_sets_environment_variables(self, tmp_path):
        """Test that staging sets AMPLIHACK_IS_STAGED env var"""
        original_cwd = tmp_path / "original"
        original_cwd.mkdir()
        claude_dir = original_cwd / ".claude"
        claude_dir.mkdir()
        (claude_dir / "context").mkdir()

        stager = AutoStager()

        # Clear env var before test
        if "AMPLIHACK_IS_STAGED" in os.environ:
            del os.environ["AMPLIHACK_IS_STAGED"]

        result = stager.stage_for_nested_execution(original_cwd, "test-session")

        assert "AMPLIHACK_IS_STAGED" in os.environ
        assert os.environ["AMPLIHACK_IS_STAGED"] == "1"

    def test_staging_result_preserves_original_cwd(self, tmp_path):
        """Test that StagingResult preserves original_cwd"""
        original_cwd = tmp_path / "original"
        original_cwd.mkdir()
        claude_dir = original_cwd / ".claude"
        claude_dir.mkdir()
        (claude_dir / "context").mkdir()

        stager = AutoStager()
        result = stager.stage_for_nested_execution(original_cwd, "test-session")

        assert result.original_cwd == original_cwd.resolve()


# E2E TESTS (10%)
class TestAutoStagerE2E:
    """Test end-to-end staging scenarios"""

    def test_real_world_nested_session_staging(self, tmp_path):
        """Test realistic nested session staging scenario"""
        # Setup: amplihack source repo with full .claude structure
        original_cwd = tmp_path / "amplihack"
        original_cwd.mkdir()

        # Create realistic .claude structure
        claude_dir = original_cwd / ".claude"
        claude_dir.mkdir()

        (claude_dir / "agents").mkdir()
        (claude_dir / "agents" / "amplihack").mkdir()
        (claude_dir / "agents" / "amplihack" / "builder.md").write_text("builder agent")

        (claude_dir / "commands").mkdir()
        (claude_dir / "commands" / "ultrathink.sh").write_text("#!/bin/bash")

        (claude_dir / "context").mkdir()
        (claude_dir / "context" / "PHILOSOPHY.md").write_text("# Philosophy")
        (claude_dir / "context" / "PROJECT.md").write_text("# Project")

        (claude_dir / "workflow").mkdir()
        (claude_dir / "workflow" / "DEFAULT_WORKFLOW.md").write_text("# Workflow")

        # Add runtime (should NOT be staged)
        (claude_dir / "runtime").mkdir()
        (claude_dir / "runtime" / "sessions.jsonl").write_text("session data")

        # Stage for nested execution
        stager = AutoStager()
        result = stager.stage_for_nested_execution(original_cwd, "nested-session-001")

        # Verify complete staging
        assert result.temp_root.exists()
        assert result.staged_claude.exists()

        # Verify essential directories copied
        assert (result.staged_claude / "agents" / "amplihack" / "builder.md").exists()
        assert (result.staged_claude / "commands" / "ultrathink.sh").exists()
        assert (result.staged_claude / "context" / "PHILOSOPHY.md").exists()
        assert (result.staged_claude / "workflow" / "DEFAULT_WORKFLOW.md").exists()

        # Verify runtime NOT copied
        assert not (result.staged_claude / "runtime").exists()

        # Verify environment variable set
        assert os.environ.get("AMPLIHACK_IS_STAGED") == "1"

        # Verify original directory untouched
        assert (original_cwd / ".claude" / "runtime" / "sessions.jsonl").exists()

    def test_minimal_claude_structure_staging(self, tmp_path):
        """Test staging with minimal .claude structure"""
        # Minimal setup - just context directory
        original_cwd = tmp_path / "minimal"
        original_cwd.mkdir()
        claude_dir = original_cwd / ".claude"
        claude_dir.mkdir()
        (claude_dir / "context").mkdir()
        (claude_dir / "context" / "PROJECT.md").write_text("# Minimal Project")

        stager = AutoStager()
        result = stager.stage_for_nested_execution(original_cwd, "minimal-session")

        # Should still create staged directory
        assert result.staged_claude.exists()
        assert (result.staged_claude / "context" / "PROJECT.md").exists()


# SECURITY TESTS
class TestSymlinkProtection:
    """Test security protections against symlink attacks"""

    def test_skips_symlinked_directories(self, tmp_path, capsys):
        """Test that symlinked directories are skipped with warning"""
        source = tmp_path / "source" / ".claude"
        dest = tmp_path / "dest" / ".claude"

        source.mkdir(parents=True)
        dest.mkdir(parents=True)

        # Create a normal directory
        normal_dir = source / "context"
        normal_dir.mkdir()
        (normal_dir / "test.txt").write_text("normal content")

        # Create a symlink that points to sensitive system location
        sensitive_target = tmp_path / "sensitive"
        sensitive_target.mkdir()
        (sensitive_target / "secrets.txt").write_text("sensitive data")

        symlink_dir = source / "agents"
        symlink_dir.symlink_to(sensitive_target)

        stager = AutoStager()
        stager._copy_claude_directory(source, dest)

        # Verify normal directory was copied
        assert (dest / "context" / "test.txt").exists()
        assert (dest / "context" / "test.txt").read_text() == "normal content"

        # Verify symlinked directory was NOT copied
        assert not (dest / "agents").exists()

        # Verify warning message was printed
        captured = capsys.readouterr()
        assert "Skipping symlinked directory agents" in captured.out
        assert "security protection" in captured.out

    def test_copytree_with_security_parameters(self, tmp_path):
        """Test that copytree uses symlinks=False and copy_function=shutil.copy"""
        source = tmp_path / "source" / ".claude"
        dest = tmp_path / "dest" / ".claude"

        source.mkdir(parents=True)
        dest.mkdir(parents=True)

        # Create a directory with a file containing a symlink internally
        context_dir = source / "context"
        context_dir.mkdir()
        (context_dir / "real_file.txt").write_text("real content")

        # Create internal symlink
        internal_target = tmp_path / "internal_target.txt"
        internal_target.write_text("internal target")
        (context_dir / "internal_link.txt").symlink_to(internal_target)

        stager = AutoStager()
        stager._copy_claude_directory(source, dest)

        # Verify real file was copied
        assert (dest / "context" / "real_file.txt").exists()

        # Verify internal symlink was NOT followed (should be copied as symlink or skipped)
        # With symlinks=False, the symlink should be converted to a regular file
        if (dest / "context" / "internal_link.txt").exists():
            # If it exists, it should be a regular file (not a symlink)
            assert not (dest / "context" / "internal_link.txt").is_symlink()


class TestSessionIdSanitization:
    """Test security protections for session_id sanitization"""

    def test_sanitizes_path_traversal_attempts(self, tmp_path):
        """Test that session_id with path traversal is sanitized"""
        original_cwd = tmp_path / "original"
        original_cwd.mkdir()
        claude_dir = original_cwd / ".claude"
        claude_dir.mkdir()
        (claude_dir / "context").mkdir()

        stager = AutoStager()

        # Try path traversal attack
        malicious_session_id = "../../../etc/passwd"
        result = stager.stage_for_nested_execution(original_cwd, malicious_session_id)

        # Verify that session_id was sanitized (no path separators)
        temp_name = str(result.temp_root)
        assert "../" not in temp_name
        assert (
            ".." not in temp_name.split("amplihack-stage-")[1].split("-")[0]
        )  # Check sanitized part only

        # Verify the slashes were replaced with underscores
        assert "_________etc_passwd" in temp_name or "___etc_passwd" in temp_name

        # Verify temp directory was created with sanitized name
        assert result.temp_root.exists()

    def test_sanitizes_special_characters(self, tmp_path):
        """Test that session_id with special characters is sanitized"""
        original_cwd = tmp_path / "original"
        original_cwd.mkdir()
        claude_dir = original_cwd / ".claude"
        claude_dir.mkdir()
        (claude_dir / "context").mkdir()

        stager = AutoStager()

        # Try various special characters
        malicious_session_id = "session!@#$%^&*()=+[]{}|;:'\",<>?/\\"
        result = stager.stage_for_nested_execution(original_cwd, malicious_session_id)

        # Verify special characters were replaced with underscores
        temp_name = result.temp_root.name
        assert "!" not in temp_name
        assert "@" not in temp_name
        assert "#" not in temp_name
        assert "/" not in temp_name
        assert "\\" not in temp_name

        # Verify only safe characters remain (alphanumeric, underscore, hyphen)
        import re

        # Extract the session part from the temp directory name
        # Format: amplihack-stage-{session_id}-{random}
        assert re.match(r"^amplihack-stage-[a-zA-Z0-9_-]+", temp_name)

        # Verify temp directory was created successfully
        assert result.temp_root.exists()

    def test_preserves_valid_session_ids(self, tmp_path):
        """Test that valid session_ids are not modified"""
        original_cwd = tmp_path / "original"
        original_cwd.mkdir()
        claude_dir = original_cwd / ".claude"
        claude_dir.mkdir()
        (claude_dir / "context").mkdir()

        stager = AutoStager()

        # Valid session IDs should pass through unchanged
        valid_ids = [
            "session-123",
            "nested-session-001",
            "test_session_2024",
            "my-test-session",
        ]

        for session_id in valid_ids:
            result = stager.stage_for_nested_execution(original_cwd, session_id)

            # Verify session_id appears in temp directory name
            assert session_id in str(result.temp_root)

            # Clean up for next iteration
            shutil.rmtree(result.temp_root)
