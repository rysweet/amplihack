"""Tests for ConfigCLI module."""

import os
from pathlib import Path
import pytest
import shutil
import tempfile
from click.testing import CliRunner

from amplihack.installation.config_cli import config, IMPORT_STATEMENT


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def project_with_amplihack(temp_dir):
    """Create project with Amplihack installed."""
    project_dir = temp_dir / "project"
    claude_dir = project_dir / ".claude"
    amplihack_dir = claude_dir / "amplihack"
    amplihack_dir.mkdir(parents=True)

    # Create minimal Amplihack installation
    (amplihack_dir / "CLAUDE.md").write_text("# Amplihack Config")

    agents_dir = amplihack_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "architect.md").write_text("# Architect")

    return project_dir


@pytest.fixture
def runner():
    """Create Click test runner."""
    return CliRunner()


def test_show_command_not_in_project(runner, temp_dir):
    """Test show command outside Claude project."""
    original_cwd = os.getcwd()
    try:
        os.chdir(temp_dir)
        result = runner.invoke(config, ["show"])

        assert result.exit_code != 0
        assert "not in a claude project" in result.output.lower()
    finally:
        os.chdir(original_cwd)


def test_show_command_displays_status(runner, project_with_amplihack):
    """Test show command displays correct status."""
    original_cwd = os.getcwd()
    try:
        os.chdir(project_with_amplihack)
        result = runner.invoke(config, ["show"])

        assert result.exit_code == 0
        assert "amplihack" in result.output.lower()
    finally:
        os.chdir(original_cwd)


def test_integrate_not_installed(runner, temp_dir):
    """Test integrate fails when Amplihack not installed."""
    project_dir = temp_dir / "project"
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)

    original_cwd = os.getcwd()
    try:
        os.chdir(project_dir)
        result = runner.invoke(config, ["integrate", "--force"])

        assert result.exit_code != 0
        assert "not installed" in result.output.lower()
    finally:
        os.chdir(original_cwd)


def test_integrate_with_force(runner, project_with_amplihack):
    """Test integrate with --force flag (no prompts)."""
    original_cwd = os.getcwd()
    try:
        os.chdir(project_with_amplihack)
        result = runner.invoke(config, ["integrate", "--force"])

        assert result.exit_code == 0

        # Verify import was added
        claude_md = project_with_amplihack / ".claude" / "CLAUDE.md"
        if claude_md.exists():
            content = claude_md.read_text()
            assert IMPORT_STATEMENT in content
    finally:
        os.chdir(original_cwd)


def test_integrate_with_dry_run(runner, project_with_amplihack):
    """Test integrate --dry-run shows preview without changes."""
    claude_md = project_with_amplihack / ".claude" / "CLAUDE.md"
    claude_md.write_text("# My Config\n")

    original_content = claude_md.read_text()

    original_cwd = os.getcwd()
    try:
        os.chdir(project_with_amplihack)
        result = runner.invoke(config, ["integrate", "--dry-run"])

        assert result.exit_code == 0
        assert "preview" in result.output.lower() or "dry run" in result.output.lower()

        # File should be unchanged
        assert claude_md.read_text() == original_content
    finally:
        os.chdir(original_cwd)


def test_integrate_prompts_user(runner, project_with_amplihack):
    """Test integrate prompts for confirmation."""
    original_cwd = os.getcwd()
    try:
        os.chdir(project_with_amplihack)
        # Answer 'no' to confirmation
        result = runner.invoke(config, ["integrate"], input="n\n")

        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()
    finally:
        os.chdir(original_cwd)


def test_integrate_already_present(runner, project_with_amplihack):
    """Test integrate when import already present."""
    claude_md = project_with_amplihack / ".claude" / "CLAUDE.md"
    claude_md.write_text(f"# Config\n\n{IMPORT_STATEMENT}\n")

    original_cwd = os.getcwd()
    try:
        os.chdir(project_with_amplihack)
        result = runner.invoke(config, ["integrate", "--force"])

        assert result.exit_code == 0
        assert "already" in result.output.lower() or "present" in result.output.lower()
    finally:
        os.chdir(original_cwd)


def test_remove_prompts_user(runner, project_with_amplihack):
    """Test remove prompts for confirmation."""
    claude_md = project_with_amplihack / ".claude" / "CLAUDE.md"
    claude_md.write_text(f"# Config\n\n{IMPORT_STATEMENT}\n")

    original_cwd = os.getcwd()
    try:
        os.chdir(project_with_amplihack)
        # Answer 'no' to confirmation
        result = runner.invoke(config, ["remove"], input="n\n")

        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()
    finally:
        os.chdir(original_cwd)


def test_remove_with_keep_files(runner, project_with_amplihack):
    """Test remove --keep-files preserves installation."""
    claude_md = project_with_amplihack / ".claude" / "CLAUDE.md"
    claude_md.write_text(f"# Config\n\n{IMPORT_STATEMENT}\n")

    amplihack_dir = project_with_amplihack / ".claude" / "amplihack"

    original_cwd = os.getcwd()
    try:
        os.chdir(project_with_amplihack)
        # Answer 'yes' to confirmation
        result = runner.invoke(config, ["remove", "--keep-files"], input="y\n")

        assert result.exit_code == 0

        # Directory should still exist
        assert amplihack_dir.exists()

        # Import should be removed
        if claude_md.exists():
            content = claude_md.read_text()
            assert IMPORT_STATEMENT not in content
    finally:
        os.chdir(original_cwd)


def test_remove_without_keep_files(runner, project_with_amplihack):
    """Test remove deletes installation directory."""
    claude_md = project_with_amplihack / ".claude" / "CLAUDE.md"
    claude_md.write_text(f"# Config\n\n{IMPORT_STATEMENT}\n")

    amplihack_dir = project_with_amplihack / ".claude" / "amplihack"

    original_cwd = os.getcwd()
    try:
        os.chdir(project_with_amplihack)
        # Answer 'yes' to confirmation
        result = runner.invoke(config, ["remove"], input="y\n")

        assert result.exit_code == 0

        # Directory should be removed
        assert not amplihack_dir.exists()
    finally:
        os.chdir(original_cwd)


def test_reset_requires_force(runner, project_with_amplihack):
    """Test reset command requires --force flag."""
    original_cwd = os.getcwd()
    try:
        os.chdir(project_with_amplihack)
        result = runner.invoke(config, ["reset"])

        assert result.exit_code != 0
    finally:
        os.chdir(original_cwd)


def test_reset_without_installation(runner, temp_dir):
    """Test reset when Amplihack not installed."""
    project_dir = temp_dir / "project"
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)

    original_cwd = os.getcwd()
    try:
        os.chdir(project_dir)
        result = runner.invoke(config, ["reset", "--force"])

        assert result.exit_code != 0
        assert "not installed" in result.output.lower()
    finally:
        os.chdir(original_cwd)


def test_reset_with_force(runner, project_with_amplihack):
    """Test reset with --force flag."""
    amplihack_dir = project_with_amplihack / ".claude" / "amplihack"

    original_cwd = os.getcwd()
    try:
        os.chdir(project_with_amplihack)
        # Answer 'yes' to confirmation
        result = runner.invoke(config, ["reset", "--force"], input="y\n")

        assert result.exit_code == 0

        # Directory should be removed
        assert not amplihack_dir.exists()
    finally:
        os.chdir(original_cwd)


def test_show_without_claude_md(runner, project_with_amplihack):
    """Test show command when CLAUDE.md doesn't exist."""
    original_cwd = os.getcwd()
    try:
        os.chdir(project_with_amplihack)
        result = runner.invoke(config, ["show"])

        assert result.exit_code == 0
        # Should handle missing CLAUDE.md gracefully
    finally:
        os.chdir(original_cwd)


def test_integrate_creates_backup(runner, project_with_amplihack):
    """Test that integrate creates backup before modifying."""
    claude_md = project_with_amplihack / ".claude" / "CLAUDE.md"
    claude_md.write_text("# My Config\n")

    original_cwd = os.getcwd()
    try:
        os.chdir(project_with_amplihack)
        result = runner.invoke(config, ["integrate", "--force"])

        assert result.exit_code == 0

        # Backup should be created
        backups = list(claude_md.parent.glob("CLAUDE.md.backup.*"))
        assert len(backups) >= 1
    finally:
        os.chdir(original_cwd)


def test_commands_work_in_subdirectory(runner, project_with_amplihack):
    """Test that commands work from project subdirectory."""
    subdir = project_with_amplihack / "subdir"
    subdir.mkdir()

    original_cwd = os.getcwd()
    try:
        os.chdir(subdir)

        result = runner.invoke(config, ["show"])

        # Should find .claude directory in parent
        assert result.exit_code == 0

    finally:
        os.chdir(original_cwd)


def test_remove_import_not_present(runner, project_with_amplihack):
    """Test remove when import not present."""
    claude_md = project_with_amplihack / ".claude" / "CLAUDE.md"
    claude_md.write_text("# Config\n\nNo import here\n")

    original_cwd = os.getcwd()
    try:
        os.chdir(project_with_amplihack)
        result = runner.invoke(config, ["remove"], input="y\n")

        assert result.exit_code == 0
        assert "not present" in result.output.lower()
    finally:
        os.chdir(original_cwd)
