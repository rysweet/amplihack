"""Tests for InstallationOrchestrator module."""

from pathlib import Path
import pytest
import shutil
import tempfile

from amplihack.installation.orchestrator import (
    orchestrate_installation,
    InstallMode,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def source_files(temp_dir):
    """Create source files for installation."""
    source_dir = temp_dir / "source"
    source_dir.mkdir()

    # Create minimal valid installation files
    (source_dir / "CLAUDE.md").write_text("# Amplihack Config")

    agents_dir = source_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "architect.md").write_text("# Architect")
    (agents_dir / "builder.md").write_text("# Builder")

    commands_dir = source_dir / "commands"
    commands_dir.mkdir()
    (commands_dir / "ultrathink.md").write_text("# UltraThink")

    return source_dir


def test_fresh_install_flow(temp_dir, source_files):
    """Test installation to fresh project."""
    target_dir = temp_dir / "project"
    target_dir.mkdir()

    result = orchestrate_installation(
        mode=InstallMode.INSTALL,
        target_dir=target_dir,
        source_dir=source_files,
        force=True,  # Skip prompts
        auto_integrate=True,
        non_interactive=True,
    )

    assert result.success
    assert result.mode == InstallMode.INSTALL
    assert result.installation_result.success
    assert result.integration_result is not None
    assert result.integration_result.success

    # Verify installation
    amplihack_dir = target_dir / ".claude" / "amplihack"
    assert amplihack_dir.exists()
    assert (amplihack_dir / "CLAUDE.md").exists()

    # Verify integration
    claude_md = target_dir / ".claude" / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text()
        assert "@.claude/amplihack/CLAUDE.md" in content


def test_upgrade_flow(temp_dir, source_files):
    """Test upgrading existing installation."""
    target_dir = temp_dir / "project"
    claude_dir = target_dir / ".claude"
    amplihack_dir = claude_dir / "amplihack"
    amplihack_dir.mkdir(parents=True)

    # Create old installation
    (amplihack_dir / "old_file.txt").write_text("old")

    result = orchestrate_installation(
        mode=InstallMode.INSTALL,
        target_dir=target_dir,
        source_dir=source_files,
        force=True,  # Skip prompts
        non_interactive=True,
    )

    assert result.success

    # Verify old file is gone, new files present
    assert not (amplihack_dir / "old_file.txt").exists()
    assert (amplihack_dir / "CLAUDE.md").exists()


def test_conflict_resolution_flow(temp_dir, source_files):
    """Test handling conflicts with existing files."""
    target_dir = temp_dir / "project"
    claude_dir = target_dir / ".claude"
    claude_dir.mkdir(parents=True)

    # Create conflicting files
    (claude_dir / "CLAUDE.md").write_text("# User Config")

    agents_dir = claude_dir / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "custom.md").write_text("# Custom Agent")

    result = orchestrate_installation(
        mode=InstallMode.INSTALL,
        target_dir=target_dir,
        source_dir=source_files,
        force=True,
        non_interactive=True,
    )

    assert result.success
    assert result.conflicts_detected

    # User files should be preserved
    assert (claude_dir / "CLAUDE.md").exists()
    assert (agents_dir / "custom.md").exists()

    # Amplihack files should be in namespace
    amplihack_dir = claude_dir / "amplihack"
    assert (amplihack_dir / "CLAUDE.md").exists()
    assert (amplihack_dir / "agents" / "architect.md").exists()


def test_uvx_mode_flow(temp_dir, source_files):
    """Test UVX mode (ephemeral) installation."""
    target_dir = temp_dir / "project"
    target_dir.mkdir()

    result = orchestrate_installation(
        mode=InstallMode.UVX,
        target_dir=target_dir,
        source_dir=source_files,
        non_interactive=True,
    )

    assert result.success
    assert result.mode == InstallMode.UVX

    # Should install files but not integrate
    amplihack_dir = target_dir / ".claude" / "amplihack"
    assert amplihack_dir.exists()

    # Should have user action about UVX being temporary
    assert any("UVX mode" in action for action in result.user_actions_required)


def test_user_declines_integration(temp_dir, source_files):
    """Test when user declines CLAUDE.md integration."""
    target_dir = temp_dir / "project"
    target_dir.mkdir()

    # Simulate user declining integration
    result = orchestrate_installation(
        mode=InstallMode.INSTALL,
        target_dir=target_dir,
        source_dir=source_files,
        auto_integrate=False,  # Don't integrate
        non_interactive=True,
    )

    assert result.success
    assert result.installation_result.success

    # Should not have integration result
    assert result.integration_result is None

    # Should have manual action suggestion
    # (only in non-auto-integrate, non-force mode with prompts)


def test_force_flag_skips_prompts(temp_dir, source_files):
    """Test that force flag bypasses user prompts."""
    target_dir = temp_dir / "project"
    claude_dir = target_dir / ".claude"
    claude_dir.mkdir(parents=True)

    # Create existing CLAUDE.md
    (claude_dir / "CLAUDE.md").write_text("# User Config")

    # Force should skip all prompts and proceed
    result = orchestrate_installation(
        mode=InstallMode.INSTALL,
        target_dir=target_dir,
        source_dir=source_files,
        force=True,
        auto_integrate=True,
        non_interactive=True,
    )

    assert result.success


def test_installation_failure_handling(temp_dir):
    """Test handling of installation failures."""
    target_dir = temp_dir / "project"
    target_dir.mkdir()

    # Use non-existent source
    bad_source = temp_dir / "nonexistent"

    result = orchestrate_installation(
        mode=InstallMode.INSTALL,
        target_dir=target_dir,
        source_dir=bad_source,
        non_interactive=True,
    )

    assert not result.success
    assert len(result.errors) > 0 or len(result.installation_result.errors) > 0


def test_no_conflicts_smooth_install(temp_dir, source_files):
    """Test installation with no conflicts."""
    target_dir = temp_dir / "project"
    target_dir.mkdir()

    result = orchestrate_installation(
        mode=InstallMode.INSTALL,
        target_dir=target_dir,
        source_dir=source_files,
        non_interactive=True,
        force=True,
    )

    assert result.success
    assert not result.conflicts_detected
    assert result.installation_result.success


def test_integration_already_present(temp_dir, source_files):
    """Test when import already exists in CLAUDE.md."""
    target_dir = temp_dir / "project"
    claude_dir = target_dir / ".claude"
    claude_dir.mkdir(parents=True)

    # Create CLAUDE.md with import already present
    claude_md = claude_dir / "CLAUDE.md"
    claude_md.write_text("# Config\n\n@.claude/amplihack/CLAUDE.md\n")

    result = orchestrate_installation(
        mode=InstallMode.INSTALL,
        target_dir=target_dir,
        source_dir=source_files,
        force=True,
        auto_integrate=True,
        non_interactive=True,
    )

    assert result.success
    assert result.integration_result is not None
    assert result.integration_result.action_taken == "already_present"


def test_non_interactive_mode(temp_dir, source_files):
    """Test non-interactive mode for CI/automation."""
    target_dir = temp_dir / "project"
    target_dir.mkdir()

    result = orchestrate_installation(
        mode=InstallMode.INSTALL,
        target_dir=target_dir,
        source_dir=source_files,
        non_interactive=True,
        auto_integrate=True,
    )

    assert result.success
    # Should complete without any user prompts


def test_preserve_user_files(temp_dir, source_files):
    """Test that user files are never modified."""
    target_dir = temp_dir / "project"
    claude_dir = target_dir / ".claude"
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir(parents=True)

    # Create user files
    user_agent = agents_dir / "my_custom_agent.md"
    user_agent.write_text("# My Custom Agent\n\nContent here")

    user_claude_md = claude_dir / "CLAUDE.md"
    user_claude_md.write_text("# My Project\n\nUser content")

    original_agent_content = user_agent.read_text()
    original_claude_content = user_claude_md.read_text()

    result = orchestrate_installation(
        mode=InstallMode.INSTALL,
        target_dir=target_dir,
        source_dir=source_files,
        force=True,
        auto_integrate=False,  # Don't modify CLAUDE.md
        non_interactive=True,
    )

    assert result.success

    # User files should be unchanged (when auto_integrate=False)
    assert user_agent.read_text() == original_agent_content
    assert user_claude_md.read_text() == original_claude_content
