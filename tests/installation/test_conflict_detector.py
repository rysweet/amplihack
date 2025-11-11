"""Tests for ConfigConflictDetector module."""

import os
from pathlib import Path
import pytest
import tempfile
import shutil

from amplihack.installation.conflict_detector import detect_conflicts


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


def test_detect_no_conflicts_empty_dir(temp_dir):
    """Test detection with empty .claude directory."""
    claude_dir = temp_dir / ".claude"
    claude_dir.mkdir()

    manifest = ["agents/architect.md", "agents/builder.md", "CLAUDE.md"]
    report = detect_conflicts(claude_dir, manifest)

    assert not report.has_conflicts
    assert not report.existing_claude_md
    assert len(report.existing_agents) == 0
    assert len(report.would_overwrite) == 0
    assert report.safe_to_namespace


def test_detect_no_conflicts_missing_dir(temp_dir):
    """Test detection with missing .claude directory."""
    claude_dir = temp_dir / ".claude"
    # Don't create directory

    manifest = ["agents/architect.md", "CLAUDE.md"]
    report = detect_conflicts(claude_dir, manifest)

    assert not report.has_conflicts
    assert not report.existing_claude_md
    assert report.safe_to_namespace


def test_detect_existing_claude_md(temp_dir):
    """Test detection of existing CLAUDE.md."""
    claude_dir = temp_dir / ".claude"
    claude_dir.mkdir()

    # Create existing CLAUDE.md
    claude_md = claude_dir / "CLAUDE.md"
    claude_md.write_text("# User's config")

    manifest = ["agents/architect.md", "CLAUDE.md"]
    report = detect_conflicts(claude_dir, manifest)

    assert report.has_conflicts
    assert report.existing_claude_md
    # CLAUDE.md is in manifest and would be overwritten, so not safe
    assert len(report.would_overwrite) == 1


def test_detect_conflicting_agents(temp_dir):
    """Test detection of conflicting agent files."""
    claude_dir = temp_dir / ".claude"
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir(parents=True)

    # Create conflicting agent files
    (agents_dir / "architect.md").write_text("# Custom architect")
    (agents_dir / "builder.md").write_text("# Custom builder")

    manifest = ["agents/architect.md", "agents/builder.md", "agents/tester.md"]
    report = detect_conflicts(claude_dir, manifest)

    assert report.has_conflicts
    assert "architect" in report.existing_agents
    assert "builder" in report.existing_agents
    assert "tester" not in report.existing_agents
    assert len(report.would_overwrite) == 2


def test_detect_upgrade_scenario(temp_dir):
    """Test detection of upgrade scenario (amplihack dir exists)."""
    claude_dir = temp_dir / ".claude"
    amplihack_dir = claude_dir / "amplihack"
    amplihack_dir.mkdir(parents=True)

    # Create some files in amplihack namespace
    (amplihack_dir / "CLAUDE.md").write_text("# Amplihack config")

    manifest = ["amplihack/agents/architect.md", "amplihack/CLAUDE.md"]
    report = detect_conflicts(claude_dir, manifest)

    # Upgrade scenario: namespace exists, which is safe
    assert report.safe_to_namespace


def test_handle_permission_errors(temp_dir):
    """Test graceful handling of permission errors."""
    claude_dir = temp_dir / ".claude"
    claude_dir.mkdir()

    # Make directory unreadable (Unix only)
    import sys

    if sys.platform != "win32":
        os.chmod(claude_dir, 0o000)

        try:
            manifest = ["agents/architect.md"]
            report = detect_conflicts(claude_dir, manifest)

            # Should indicate conflict but mark as unsafe
            assert report.has_conflicts
            assert not report.safe_to_namespace
        finally:
            # Restore permissions for cleanup
            os.chmod(claude_dir, 0o755)


def test_detect_namespace_files_ignored(temp_dir):
    """Test that files in amplihack namespace are ignored in conflict detection."""
    claude_dir = temp_dir / ".claude"
    agents_dir = claude_dir / "agents"
    amplihack_agents = claude_dir / "amplihack" / "agents"

    agents_dir.mkdir(parents=True)
    amplihack_agents.mkdir(parents=True)

    # Create user agent
    (agents_dir / "custom.md").write_text("# Custom agent")

    # Create amplihack agent (should not conflict)
    (amplihack_agents / "architect.md").write_text("# Amplihack architect")

    manifest = ["agents/custom.md", "amplihack/agents/architect.md"]
    report = detect_conflicts(claude_dir, manifest)

    # Should only detect conflict for custom.md, not amplihack files
    assert report.has_conflicts
    assert len(report.would_overwrite) == 1
    assert report.would_overwrite[0].name == "custom.md"


def test_empty_manifest(temp_dir):
    """Test with empty manifest."""
    claude_dir = temp_dir / ".claude"
    claude_dir.mkdir()

    manifest = []
    report = detect_conflicts(claude_dir, manifest)

    assert not report.has_conflicts
    assert report.safe_to_namespace
