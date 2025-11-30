"""Comprehensive tests for CLAUDE.md preservation - TDD approach.

Testing pyramid:
- 60% Unit tests (fast, focused on individual functions)
- 30% Integration tests (multiple components working together)
- 10% E2E tests (complete workflows)

This test suite is written BEFORE implementation (TDD) and will fail until
the claude_md_preserver module is implemented.
"""

import pytest

# Module to be implemented
from amplihack.utils.claude_md_preserver import (
    ActionTaken,
    ClaudeState,
    HandleMode,
    backup_to_preserved,
    backup_to_project_md,
    compute_content_hash,
    detect_claude_state,
    handle_claude_md,
)

# ============================================================================
# FIXTURES (Shared test data and utilities)
# ============================================================================


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory structure."""
    project = tmp_path / "test_project"
    project.mkdir()
    claude_dir = project / ".claude"
    claude_dir.mkdir()
    context_dir = claude_dir / "context"
    context_dir.mkdir()
    return project


@pytest.fixture
def stock_claude_content():
    """Stock CLAUDE.md content (from amplihack repo)."""
    return """# CLAUDE.md

This file provides guidance to Claude Code when working with your codebase.

## Important Files to Import

When starting a session, import these files for context:

[@.claude/context/PHILOSOPHY.md](.claude/context/PHILOSOPHY.md)
[@.claude/context/PROJECT.md](.claude/context/PROJECT.md)

## MANDATORY: Workflow Selection (ALWAYS FIRST)

**CRITICAL**: You MUST classify every user request into one of three workflows
BEFORE taking action. No exceptions.

<!-- Stock content continues... -->
"""


@pytest.fixture
def custom_claude_content():
    """Custom user CLAUDE.md content (different from stock)."""
    return """# CLAUDE.md - My Custom Project Setup

This is my custom configuration for my project.

## My Custom Sections

- Custom rule 1
- Custom rule 2
- Custom workflow

This content is completely different from amplihack stock.
"""


@pytest.fixture
def outdated_claude_content():
    """Outdated amplihack CLAUDE.md (old version)."""
    return """# CLAUDE.md

This file provides guidance to Claude Code when working with your codebase.

## Old Section That Was Removed

This section existed in an old version but was removed in current stock.

[@.claude/context/PHILOSOPHY.md](.claude/context/PHILOSOPHY.md)

<!-- Outdated amplihack content -->
"""


@pytest.fixture
def project_md_with_custom_content():
    """PROJECT.md that already contains custom user content."""
    return """# Project Context

## Project: My Awesome Project

## Overview

This is my project's custom content that I've already written.

## Architecture

### Key Components

- Component 1: My custom component
- Component 2: Another custom component
"""


# ============================================================================
# UNIT TESTS (60% - Fast, focused, heavily mocked)
# ============================================================================


class TestComputeContentHash:
    """Test content hash computation for file comparison."""

    def test_compute_hash_basic_content(self):
        """Test hash computation strips whitespace and computes SHA256."""
        content = "Hello World\n\n"
        result_hash = compute_content_hash(content)

        # Hash should be SHA256 hex digest
        assert isinstance(result_hash, str)
        assert len(result_hash) == 64  # SHA256 produces 64 hex chars

        # Same content should produce same hash
        assert result_hash == compute_content_hash("Hello World\n\n")

    def test_compute_hash_ignores_whitespace_differences(self):
        """Test that whitespace-only changes are ignored."""
        content1 = "Hello World"
        content2 = "Hello World\n\n\n"
        content3 = "  Hello World  "

        hash1 = compute_content_hash(content1)
        hash2 = compute_content_hash(content2)
        hash3 = compute_content_hash(content3)

        # All should produce same hash (whitespace ignored)
        assert hash1 == hash2 == hash3

    def test_compute_hash_detects_content_changes(self):
        """Test that actual content changes are detected."""
        content1 = "Hello World"
        content2 = "Hello Planet"

        hash1 = compute_content_hash(content1)
        hash2 = compute_content_hash(content2)

        # Different content should produce different hashes
        assert hash1 != hash2

    def test_compute_hash_handles_empty_string(self):
        """Test hash computation with empty content."""
        result_hash = compute_content_hash("")
        assert isinstance(result_hash, str)
        assert len(result_hash) == 64


class TestDetectClaudeState:
    """Test CLAUDE.md state detection (60% of unit tests)."""

    def test_detect_state_missing_when_file_not_exists(self, temp_project_dir):
        """Test detection returns MISSING when CLAUDE.md doesn't exist."""
        state, reason = detect_claude_state(temp_project_dir)

        assert state == ClaudeState.MISSING
        assert "not found" in reason.lower() or "missing" in reason.lower()

    def test_detect_state_valid_when_matches_stock(self, temp_project_dir, stock_claude_content):
        """Test detection returns VALID when content matches current stock."""
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(stock_claude_content)

        state, reason = detect_claude_state(temp_project_dir)

        assert state == ClaudeState.VALID
        assert "matches" in reason.lower() or "valid" in reason.lower()

    def test_detect_state_outdated_when_old_amplihack_version(
        self, temp_project_dir, outdated_claude_content
    ):
        """Test detection returns OUTDATED for old amplihack versions."""
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(outdated_claude_content)

        state, reason = detect_claude_state(temp_project_dir)

        assert state == ClaudeState.OUTDATED
        assert "outdated" in reason.lower() or "old version" in reason.lower()

    def test_detect_state_custom_when_user_content(self, temp_project_dir, custom_claude_content):
        """Test detection returns CUSTOM_CONTENT for user modifications."""
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(custom_claude_content)

        state, reason = detect_claude_state(temp_project_dir)

        assert state == ClaudeState.CUSTOM_CONTENT
        assert "custom" in reason.lower() or "modified" in reason.lower()

    def test_detect_state_handles_unreadable_file(self, temp_project_dir):
        """Test detection handles files that can't be read."""
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text("content")
        claude_file.chmod(0o000)  # Make unreadable

        try:
            state, reason = detect_claude_state(temp_project_dir)
            # Should return CUSTOM_CONTENT and assume valid user content
            assert state == ClaudeState.CUSTOM_CONTENT
            assert "unreadable" in reason.lower() or "error" in reason.lower()
        finally:
            claude_file.chmod(0o644)  # Restore permissions

    def test_detect_state_whitespace_only_changes_considered_valid(
        self, temp_project_dir, stock_claude_content
    ):
        """Test that whitespace-only changes don't trigger CUSTOM state."""
        # Add extra whitespace to stock content
        modified = stock_claude_content + "\n\n\n"
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(modified)

        state, reason = detect_claude_state(temp_project_dir)

        # Should still be VALID (whitespace ignored)
        assert state == ClaudeState.VALID


class TestBackupToProjectMd:
    """Test backup to PROJECT.md with section markers."""

    def test_backup_creates_section_in_empty_project_md(
        self, temp_project_dir, custom_claude_content
    ):
        """Test backup creates new section when PROJECT.md is empty."""
        project_md = temp_project_dir / ".claude" / "context" / "PROJECT.md"
        project_md.write_text("# Project Context\n\n[Empty template]")

        result_path = backup_to_project_md(temp_project_dir, custom_claude_content)

        assert result_path == project_md
        content = project_md.read_text()

        # Should contain section markers
        assert "<!-- BEGIN AMPLIHACK-PRESERVED-CONTENT" in content
        assert "<!-- END AMPLIHACK-PRESERVED-CONTENT -->" in content
        assert custom_claude_content in content

    def test_backup_replaces_existing_preserved_section(
        self, temp_project_dir, custom_claude_content
    ):
        """Test backup replaces existing preserved section (idempotent)."""
        project_md = temp_project_dir / ".claude" / "context" / "PROJECT.md"
        existing_content = """# Project Context

<!-- PRESERVED_CLAUDE_MD_START -->
Old preserved content that should be replaced
<!-- PRESERVED_CLAUDE_MD_END -->

## Other Sections

User's other content
"""
        project_md = temp_project_dir / ".claude" / "context" / "PROJECT.md"
        existing_content = """# Project Context

<!-- BEGIN AMPLIHACK-PRESERVED-CONTENT 2024-01-01T00:00:00 -->
Old preserved content that should be replaced
<!-- END AMPLIHACK-PRESERVED-CONTENT -->

## Other Sections

User's other content
"""
        project_md.write_text(existing_content)

        result_path = backup_to_project_md(temp_project_dir, custom_claude_content)

        content = project_md.read_text()

        # Verify return value is correct path
        assert result_path == project_md

        # Should have new content, not old
        assert custom_claude_content in content
        assert "Old preserved content" not in content
        assert "User's other content" in content  # Preserved

    def test_backup_preserves_existing_project_md_content(
        self, temp_project_dir, custom_claude_content, project_md_with_custom_content
    ):
        """Test backup preserves existing PROJECT.md content outside markers."""
        project_md = temp_project_dir / ".claude" / "context" / "PROJECT.md"
        project_md.write_text(project_md_with_custom_content)

        backup_to_project_md(temp_project_dir, custom_claude_content)

        content = project_md.read_text()

        # Original content should still be present
        assert "My Awesome Project" in content
        assert "My custom component" in content
        # New preserved section added
        assert "<!-- BEGIN AMPLIHACK-PRESERVED-CONTENT" in content

    def test_backup_creates_project_md_if_missing(self, temp_project_dir, custom_claude_content):
        """Test backup creates PROJECT.md if it doesn't exist."""
        project_md = temp_project_dir / ".claude" / "context" / "PROJECT.md"

        # Ensure it doesn't exist
        if project_md.exists():
            project_md.unlink()

        result_path = backup_to_project_md(temp_project_dir, custom_claude_content)

        assert result_path == project_md
        assert project_md.exists()
        assert custom_claude_content in project_md.read_text()


class TestBackupToPreserved:
    """Test backup to CLAUDE.md.preserved file."""

    def test_backup_creates_preserved_file(self, temp_project_dir, custom_claude_content):
        """Test backup creates CLAUDE.md.preserved with correct content."""
        result_path = backup_to_preserved(temp_project_dir, custom_claude_content)

        expected_path = temp_project_dir / "CLAUDE.md.preserved"
        assert result_path == expected_path
        assert expected_path.exists()
        assert expected_path.read_text() == custom_claude_content

    def test_backup_overwrites_existing_preserved_file(
        self, temp_project_dir, custom_claude_content
    ):
        """Test backup overwrites existing .preserved file (idempotent)."""
        preserved = temp_project_dir / "CLAUDE.md.preserved"
        preserved.write_text("Old backup content")

        result_path = backup_to_preserved(temp_project_dir, custom_claude_content)

        # Verify result path is correct
        assert result_path == preserved
        # Should be overwritten with new content
        assert preserved.read_text() == custom_claude_content
        assert "Old backup content" not in preserved.read_text()


class TestHandleClaudeMdBasicScenarios:
    """Test basic scenarios of handle_claude_md function."""

    def test_handle_missing_state_copies_stock(self, temp_project_dir, stock_claude_content):
        """Test handling MISSING state copies stock CLAUDE.md."""
        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        assert result.action_taken == ActionTaken.INITIALIZED
        assert result.state == ClaudeState.MISSING
        assert result.success is True
        assert (temp_project_dir / "CLAUDE.md").exists()

    def test_handle_valid_state_skips_update(self, temp_project_dir, stock_claude_content):
        """Test handling VALID state skips update (already current)."""
        # Setup: valid CLAUDE.md already exists
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(stock_claude_content)

        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        assert result.action_taken == ActionTaken.SKIPPED
        assert result.state == ClaudeState.VALID
        assert "already valid" in result.message.lower() or "up to date" in result.message.lower()

    def test_handle_outdated_state_updates_without_backup(
        self, temp_project_dir, outdated_claude_content, stock_claude_content
    ):
        """Test handling OUTDATED state updates without backup."""
        # Setup: outdated amplihack CLAUDE.md
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(outdated_claude_content)

        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        assert result.action_taken == ActionTaken.UPDATED
        assert result.state == ClaudeState.OUTDATED
        assert result.backup_path is None  # No backup for outdated amplihack versions
        assert claude_file.read_text() == stock_claude_content

    def test_handle_custom_content_backs_up_and_replaces(
        self, temp_project_dir, custom_claude_content, stock_claude_content
    ):
        """Test handling CUSTOM_CONTENT backs up to PROJECT.md and replaces."""
        # Setup: custom user CLAUDE.md
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(custom_claude_content)

        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        assert result.action_taken == ActionTaken.BACKED_UP_AND_REPLACED
        assert result.state == ClaudeState.CUSTOM_CONTENT
        assert result.backup_path is not None
        assert result.success is True

        # CLAUDE.md should now have stock content
        assert claude_file.read_text() == stock_claude_content

        # Custom content should be in PROJECT.md
        project_md = temp_project_dir / ".claude" / "context" / "PROJECT.md"
        assert custom_claude_content in project_md.read_text()

        # CLAUDE.md.preserved should also exist
        preserved = temp_project_dir / ".claude" / "context" / "CLAUDE.md.preserved"
        assert preserved.exists()
        preserved_content = preserved.read_text()
        assert custom_claude_content in preserved_content


# ============================================================================
# INTEGRATION TESTS (30% - Multiple components working together)
# ============================================================================


class TestBackupWorkflowIntegration:
    """Test integrated backup workflow with both backup mechanisms."""

    def test_backup_workflow_creates_both_backups(
        self, temp_project_dir, custom_claude_content, stock_claude_content
    ):
        """Test that backup workflow creates both PROJECT.md section and .preserved."""
        # Setup: custom CLAUDE.md
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(custom_claude_content)

        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        # Execute full workflow
        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        assert result.success is True

        # Verify both backups exist
        project_md = temp_project_dir / ".claude" / "context" / "PROJECT.md"
        preserved = temp_project_dir / ".claude" / "context" / "CLAUDE.md.preserved"

        assert project_md.exists()
        assert preserved.exists()

        # Verify content in both
        project_content = project_md.read_text()
        assert "<!-- BEGIN AMPLIHACK-PRESERVED-CONTENT" in project_content
        assert custom_claude_content in project_content

        preserved_content = preserved.read_text()
        assert custom_claude_content in preserved_content

    def test_backup_workflow_with_existing_project_md(
        self,
        temp_project_dir,
        custom_claude_content,
        project_md_with_custom_content,
        stock_claude_content,
    ):
        """Test backup workflow preserves existing PROJECT.md content."""
        # Setup: existing PROJECT.md with content
        project_md = temp_project_dir / ".claude" / "context" / "PROJECT.md"
        project_md.write_text(project_md_with_custom_content)

        # Setup: custom CLAUDE.md
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(custom_claude_content)

        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        # Execute workflow
        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        # Verify operation succeeded
        assert result.success
        # Verify original PROJECT.md content preserved
        project_content = project_md.read_text()
        assert "My Awesome Project" in project_content
        assert "My custom component" in project_content

        # Verify preserved section added
        assert "<!-- BEGIN AMPLIHACK-PRESERVED-CONTENT" in project_content
        assert custom_claude_content in project_content


class TestIdempotencyIntegration:
    """Test that operations are idempotent (can run multiple times safely)."""

    def test_handle_claude_md_idempotent_on_custom_content(
        self, temp_project_dir, custom_claude_content, stock_claude_content
    ):
        """Test running handle_claude_md twice produces same result."""
        # Setup
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(custom_claude_content)

        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        # Run once
        result1 = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        # Verify first run succeeded
        assert result1.success
        # Capture state after first run
        project_md = temp_project_dir / ".claude" / "context" / "PROJECT.md"
        preserved = temp_project_dir / "CLAUDE.md.preserved"

        project_content_1 = project_md.read_text()
        preserved_content_1 = preserved.read_text()
        claude_content_1 = claude_file.read_text()

        # Run again (should be idempotent)
        result2 = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        # Should skip (already valid)
        assert result2.action_taken == ActionTaken.SKIPPED
        assert result2.state == ClaudeState.VALID

        # Files should be unchanged
        assert project_md.read_text() == project_content_1
        assert preserved.read_text() == preserved_content_1
        assert claude_file.read_text() == claude_content_1

    def test_backup_to_project_md_idempotent(self, temp_project_dir, custom_claude_content):
        """Test backing up same content multiple times is idempotent."""
        # Backup once
        backup_to_project_md(temp_project_dir, custom_claude_content)

        project_md = temp_project_dir / ".claude" / "context" / "PROJECT.md"
        content_after_first = project_md.read_text()

        # Backup again (same content)
        backup_to_project_md(temp_project_dir, custom_claude_content)

        content_after_second = project_md.read_text()

        # Should be identical (idempotent)
        assert content_after_first == content_after_second

        # Should only have one preserved section
        assert content_after_second.count("<!-- BEGIN AMPLIHACK-PRESERVED-CONTENT") == 1


class TestModeHandling:
    """Test different HandleMode behaviors."""

    def test_check_mode_reports_without_modifying(
        self, temp_project_dir, custom_claude_content, stock_claude_content
    ):
        """Test CHECK mode reports state without making changes."""
        # Setup: custom CLAUDE.md
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(custom_claude_content)
        original_content = claude_file.read_text()

        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        # Use CHECK mode
        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.CHECK
        )

        # Should report state
        assert result.state == ClaudeState.CUSTOM_CONTENT
        assert result.action_taken == ActionTaken.CHECKED

        # Should NOT modify files
        assert claude_file.read_text() == original_content
        assert not (temp_project_dir / ".claude" / "context" / "CLAUDE.md.preserved").exists()

    def test_force_mode_replaces_even_valid_content(self, temp_project_dir, stock_claude_content):
        """Test FORCE mode replaces even valid/current content."""
        # Setup: valid CLAUDE.md (current stock)
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(stock_claude_content)

        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        # Use FORCE mode
        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.FORCE
        )

        # Should force update even though content is valid
        assert result.action_taken in [ActionTaken.UPDATED, ActionTaken.FORCED]
        assert result.success is True


# ============================================================================
# E2E TESTS (10% - Complete workflows from start to finish)
# ============================================================================


class TestEndToEndDeploymentWorkflow:
    """Test complete deployment workflows as users would experience."""

    def test_complete_new_project_deployment(self, temp_project_dir, stock_claude_content):
        """Test complete workflow: new project, no existing CLAUDE.md."""
        # Simulate amplihack source
        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        # Deploy to project with no CLAUDE.md
        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        # Verify complete successful deployment
        assert result.success is True
        assert result.action_taken == ActionTaken.INITIALIZED
        assert result.state == ClaudeState.MISSING
        assert (temp_project_dir / "CLAUDE.md").exists()
        assert (temp_project_dir / "CLAUDE.md").read_text() == stock_claude_content

    def test_complete_existing_project_custom_claude(
        self, temp_project_dir, custom_claude_content, stock_claude_content
    ):
        """Test complete workflow: existing project with custom CLAUDE.md."""
        # Simulate existing project with custom CLAUDE.md
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(custom_claude_content)

        # Simulate amplihack source
        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        # Deploy (should backup and replace)
        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        # Verify complete workflow
        assert result.success is True
        assert result.action_taken == ActionTaken.BACKED_UP_AND_REPLACED

        # Verify CLAUDE.md replaced with stock
        assert claude_file.read_text() == stock_claude_content

        # Verify backups created
        project_md = temp_project_dir / ".claude" / "context" / "PROJECT.md"
        preserved = temp_project_dir / ".claude" / "context" / "CLAUDE.md.preserved"
        assert project_md.exists()
        assert preserved.exists()
        assert custom_claude_content in project_md.read_text()
        preserved_content = preserved.read_text()
        assert custom_claude_content in preserved_content

    def test_complete_upgrade_workflow_outdated_to_current(
        self, temp_project_dir, outdated_claude_content, stock_claude_content
    ):
        """Test complete workflow: upgrading from old amplihack version."""
        # Simulate project with outdated amplihack CLAUDE.md
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(outdated_claude_content)

        # Simulate amplihack source (current version)
        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        # Deploy (should update without backup)
        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        # Verify upgrade completed
        assert result.success is True
        assert result.action_taken == ActionTaken.UPDATED
        assert result.backup_path is None  # No backup for outdated versions
        assert claude_file.read_text() == stock_claude_content

    def test_complete_workflow_repeated_deployments(self, temp_project_dir, stock_claude_content):
        """Test complete workflow: multiple deployments (idempotency check)."""
        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        # First deployment
        result1 = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )
        assert result1.action_taken == ActionTaken.INITIALIZED

        # Second deployment (should skip)
        result2 = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )
        assert result2.action_taken == ActionTaken.SKIPPED
        assert result2.state == ClaudeState.VALID

        # Third deployment (should still skip)
        result3 = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )
        assert result3.action_taken == ActionTaken.SKIPPED


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_handle_missing_source_file(self, temp_project_dir):
        """Test handling when source CLAUDE.md doesn't exist."""
        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        # No CLAUDE.md in source

        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        assert result.success is False
        assert "source" in result.message.lower() or "not found" in result.message.lower()

    def test_handle_unreadable_source_file(self, temp_project_dir):
        """Test handling when source CLAUDE.md can't be read."""
        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text("content")
        source_claude.chmod(0o000)  # Make unreadable

        try:
            result = handle_claude_md(
                source=source_dir, target=temp_project_dir, mode=HandleMode.AUTO
            )

            assert result.success is False
            assert "read" in result.message.lower() or "permission" in result.message.lower()
        finally:
            source_claude.chmod(0o644)

    def test_handle_write_permission_error(self, temp_project_dir, stock_claude_content):
        """Test handling when target directory is not writable."""
        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        # Make target directory read-only
        temp_project_dir.chmod(0o444)

        try:
            result = handle_claude_md(
                source=source_dir, target=temp_project_dir, mode=HandleMode.AUTO
            )

            assert result.success is False
            assert "write" in result.message.lower() or "permission" in result.message.lower()
        finally:
            temp_project_dir.chmod(0o755)

    def test_handle_corrupted_project_md(
        self, temp_project_dir, custom_claude_content, stock_claude_content
    ):
        """Test handling when PROJECT.md exists but is corrupted/malformed."""
        # Create corrupted PROJECT.md
        project_md = temp_project_dir / ".claude" / "context" / "PROJECT.md"
        project_md.write_text("<!-- PRESERVED_CLAUDE_MD_START -->\nNo end marker!")

        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(custom_claude_content)

        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        # Should handle gracefully
        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        # Should succeed (handles corruption by fixing markers)
        assert result.success is True

        # Verify markers are properly closed
        final_content = project_md.read_text()
        assert final_content.count("<!-- BEGIN AMPLIHACK-PRESERVED-CONTENT") == 1
        assert final_content.count("<!-- END AMPLIHACK-PRESERVED-CONTENT -->") == 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_custom_claude_content(self, temp_project_dir, stock_claude_content):
        """Test handling when user's CLAUDE.md is empty."""
        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text("")  # Empty file

        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        # Empty file should be treated as custom content
        assert result.state == ClaudeState.CUSTOM_CONTENT
        # But might skip backup if content is empty
        assert result.success is True

    def test_very_large_claude_file(self, temp_project_dir, stock_claude_content):
        """Test handling when CLAUDE.md is very large (>1MB)."""
        # Create large custom content
        large_content = "# Custom CLAUDE.md\n" + ("x" * 2_000_000)  # ~2MB

        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(large_content)

        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        # Should handle large files
        assert result.success is True

        # Verify backup contains full content
        preserved = temp_project_dir / ".claude" / "context" / "CLAUDE.md.preserved"
        assert len(preserved.read_text()) > 2_000_000

    def test_special_characters_in_content(self, temp_project_dir, stock_claude_content):
        """Test handling content with special characters and encodings."""
        custom_content = """# CLAUDE.md with Special Chars

Unicode: 你好世界 🚀 café naïve résumé

Special: <!-- --> <script> & < > " '

Markdown: **bold** *italic* `code` [link](url)
"""

        claude_file = temp_project_dir / "CLAUDE.md"
        claude_file.write_text(custom_content, encoding="utf-8")

        source_dir = temp_project_dir / "amplihack_source"
        source_dir.mkdir()
        source_claude = source_dir / "CLAUDE.md"
        source_claude.write_text(stock_claude_content)

        result = handle_claude_md(
            source_claude=source_dir, target_dir=temp_project_dir, mode=HandleMode.AUTO
        )

        assert result.success is True

        # Verify special characters preserved in backups
        preserved = temp_project_dir / ".claude" / "context" / "CLAUDE.md.preserved"
        preserved_content = preserved.read_text(encoding="utf-8")
        assert "你好世界" in preserved_content
        assert "🚀" in preserved_content


# ============================================================================
# TESTING SUMMARY
# ============================================================================

"""
Test Coverage Summary:

UNIT TESTS (60%):
- TestComputeContentHash: 4 tests
- TestDetectClaudeState: 6 tests
- TestBackupToProjectMd: 4 tests
- TestBackupToPreserved: 2 tests
- TestHandleClaudeMdBasicScenarios: 4 tests
Total: 20 unit tests

INTEGRATION TESTS (30%):
- TestBackupWorkflowIntegration: 2 tests
- TestIdempotencyIntegration: 2 tests
- TestModeHandling: 2 tests
Total: 6 integration tests

E2E TESTS (10%):
- TestEndToEndDeploymentWorkflow: 4 tests
Total: 4 E2E tests

ERROR HANDLING:
- TestErrorHandling: 4 tests
- TestEdgeCases: 3 tests
Total: 7 error tests

GRAND TOTAL: 37 comprehensive tests

All tests are written following TDD principles and will FAIL until the
claude_md_preserver module is implemented according to the public API defined
in the architecture specification.
"""
