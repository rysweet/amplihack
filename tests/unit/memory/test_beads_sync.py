"""
Unit tests for BeadsSync.

Tests git coordination for beads state synchronization, including:
- JSONL export detection
- Git sync coordination
- Merge conflict detection
- Debounce logic (5-second delay)

Following TDD approach - all tests should FAIL initially until implementation exists.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
from datetime import datetime, timedelta


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_git_repo(tmp_path):
    """Create mock git repository structure."""
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    (repo_path / ".beads").mkdir()
    return repo_path


@pytest.fixture
def beads_sync(mock_git_repo):
    """Create BeadsSync instance for testing."""
    # This import will fail initially (TDD)
    from amplihack.memory.beads_sync import BeadsSync
    return BeadsSync(repo_path=str(mock_git_repo))


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for git command execution."""
    with patch('subprocess.run') as mock:
        mock.return_value = MagicMock(
            returncode=0,
            stdout='success',
            stderr=''
        )
        yield mock


# =============================================================================
# JSONL Export Detection Tests
# =============================================================================

def test_detect_jsonl_export_exists(beads_sync, mock_git_repo):
    """Test detecting existing JSONL export file."""
    # Create JSONL export file
    jsonl_file = mock_git_repo / ".beads" / "export.jsonl"
    jsonl_file.write_text('{"id": "ISSUE-001"}\n')

    has_export = beads_sync.has_jsonl_export()

    assert has_export is True


def test_detect_jsonl_export_missing(beads_sync, mock_git_repo):
    """Test detecting missing JSONL export file."""
    has_export = beads_sync.has_jsonl_export()

    assert has_export is False


def test_get_jsonl_export_path(beads_sync, mock_git_repo):
    """Test getting JSONL export file path."""
    export_path = beads_sync.get_jsonl_export_path()

    assert export_path == mock_git_repo / ".beads" / "export.jsonl"
    assert export_path.parent.name == ".beads"


def test_create_jsonl_export(beads_sync, mock_git_repo):
    """Test creating JSONL export from beads data."""
    sample_issues = [
        {"id": "ISSUE-001", "title": "Issue 1"},
        {"id": "ISSUE-002", "title": "Issue 2"}
    ]

    beads_sync.create_jsonl_export(sample_issues)

    export_path = mock_git_repo / ".beads" / "export.jsonl"
    assert export_path.exists()

    lines = export_path.read_text().strip().split('\n')
    assert len(lines) == 2


def test_read_jsonl_export(beads_sync, mock_git_repo):
    """Test reading JSONL export file."""
    jsonl_file = mock_git_repo / ".beads" / "export.jsonl"
    jsonl_file.write_text('{"id": "ISSUE-001"}\n{"id": "ISSUE-002"}\n')

    issues = beads_sync.read_jsonl_export()

    assert len(issues) == 2
    assert issues[0]["id"] == "ISSUE-001"
    assert issues[1]["id"] == "ISSUE-002"


def test_jsonl_export_empty_file(beads_sync, mock_git_repo):
    """Test reading empty JSONL export file."""
    jsonl_file = mock_git_repo / ".beads" / "export.jsonl"
    jsonl_file.write_text('')

    issues = beads_sync.read_jsonl_export()

    assert issues == []


def test_jsonl_export_malformed_line(beads_sync, mock_git_repo):
    """Test handling malformed JSONL line."""
    jsonl_file = mock_git_repo / ".beads" / "export.jsonl"
    jsonl_file.write_text('{"id": "ISSUE-001"}\nInvalid JSON\n{"id": "ISSUE-002"}\n')

    with pytest.raises(ValueError, match="malformed JSONL"):
        beads_sync.read_jsonl_export()


# =============================================================================
# Git Sync Coordination Tests
# =============================================================================

def test_check_git_status_clean(beads_sync, mock_subprocess):
    """Test checking git status when working tree is clean."""
    mock_subprocess.return_value = MagicMock(
        returncode=0,
        stdout='',
        stderr=''
    )

    is_clean = beads_sync.is_git_clean()

    assert is_clean is True
    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args[0][0]
    assert 'git' in call_args
    assert 'status' in call_args


def test_check_git_status_dirty(beads_sync, mock_subprocess):
    """Test checking git status when working tree has changes."""
    mock_subprocess.return_value = MagicMock(
        returncode=0,
        stdout=' M .beads/export.jsonl\n',
        stderr=''
    )

    is_clean = beads_sync.is_git_clean()

    assert is_clean is False


def test_stage_beads_export(beads_sync, mock_subprocess):
    """Test staging JSONL export for commit."""
    result = beads_sync.stage_export()

    assert result is True
    call_args = mock_subprocess.call_args[0][0]
    assert 'git' in call_args
    assert 'add' in call_args
    assert '.beads/export.jsonl' in call_args


def test_stage_beads_export_file_not_found(beads_sync, mock_subprocess):
    """Test staging when export file doesn't exist."""
    mock_subprocess.return_value = MagicMock(
        returncode=128,  # Git error code
        stdout='',
        stderr='fatal: pathspec .beads/export.jsonl did not match any files'
    )

    with pytest.raises(RuntimeError, match="export file not found"):
        beads_sync.stage_export()


def test_commit_beads_export(beads_sync, mock_subprocess):
    """Test committing JSONL export."""
    result = beads_sync.commit_export(message="Update beads state")

    assert result is True
    call_args = mock_subprocess.call_args[0][0]
    assert 'git' in call_args
    assert 'commit' in call_args
    assert 'Update beads state' in str(call_args)


def test_commit_beads_export_nothing_to_commit(beads_sync, mock_subprocess):
    """Test committing when there are no changes."""
    mock_subprocess.return_value = MagicMock(
        returncode=1,
        stdout='',
        stderr='nothing to commit'
    )

    result = beads_sync.commit_export(message="Update beads state")

    # Should succeed (idempotent)
    assert result is True


def test_push_beads_export(beads_sync, mock_subprocess):
    """Test pushing JSONL export to remote."""
    result = beads_sync.push_export()

    assert result is True
    call_args = mock_subprocess.call_args[0][0]
    assert 'git' in call_args
    assert 'push' in call_args


def test_push_beads_export_no_remote(beads_sync, mock_subprocess):
    """Test pushing when no remote is configured."""
    mock_subprocess.return_value = MagicMock(
        returncode=128,
        stdout='',
        stderr='fatal: No configured push destination'
    )

    with pytest.raises(RuntimeError, match="no remote configured"):
        beads_sync.push_export()


def test_pull_beads_export(beads_sync, mock_subprocess):
    """Test pulling JSONL export from remote."""
    result = beads_sync.pull_export()

    assert result is True
    call_args = mock_subprocess.call_args[0][0]
    assert 'git' in call_args
    assert 'pull' in call_args


# =============================================================================
# Merge Conflict Detection Tests
# =============================================================================

def test_detect_merge_conflict_exists(beads_sync, mock_git_repo):
    """Test detecting merge conflict in JSONL export."""
    jsonl_file = mock_git_repo / ".beads" / "export.jsonl"
    jsonl_file.write_text('''<<<<<<< HEAD
{"id": "ISSUE-001", "status": "open"}
=======
{"id": "ISSUE-001", "status": "closed"}
>>>>>>> main
''')

    has_conflict = beads_sync.has_merge_conflict()

    assert has_conflict is True


def test_detect_merge_conflict_none(beads_sync, mock_git_repo):
    """Test detecting no merge conflict."""
    jsonl_file = mock_git_repo / ".beads" / "export.jsonl"
    jsonl_file.write_text('{"id": "ISSUE-001", "status": "open"}\n')

    has_conflict = beads_sync.has_merge_conflict()

    assert has_conflict is False


def test_get_conflict_markers(beads_sync, mock_git_repo):
    """Test extracting conflict markers from file."""
    jsonl_file = mock_git_repo / ".beads" / "export.jsonl"
    jsonl_file.write_text('''<<<<<<< HEAD
{"id": "ISSUE-001", "status": "open"}
=======
{"id": "ISSUE-001", "status": "closed"}
>>>>>>> main
''')

    conflict_info = beads_sync.get_conflict_info()

    assert conflict_info is not None
    assert "HEAD" in conflict_info["ours"]
    assert "main" in conflict_info["theirs"]


def test_resolve_conflict_use_ours(beads_sync, mock_git_repo):
    """Test resolving conflict by keeping our version."""
    jsonl_file = mock_git_repo / ".beads" / "export.jsonl"
    jsonl_file.write_text('''<<<<<<< HEAD
{"id": "ISSUE-001", "status": "open"}
=======
{"id": "ISSUE-001", "status": "closed"}
>>>>>>> main
''')

    result = beads_sync.resolve_conflict(strategy="ours")

    assert result is True
    content = jsonl_file.read_text()
    assert "<<<<<<< HEAD" not in content
    assert '"status": "open"' in content


def test_resolve_conflict_use_theirs(beads_sync, mock_git_repo):
    """Test resolving conflict by keeping their version."""
    jsonl_file = mock_git_repo / ".beads" / "export.jsonl"
    jsonl_file.write_text('''<<<<<<< HEAD
{"id": "ISSUE-001", "status": "open"}
=======
{"id": "ISSUE-001", "status": "closed"}
>>>>>>> main
''')

    result = beads_sync.resolve_conflict(strategy="theirs")

    assert result is True
    content = jsonl_file.read_text()
    assert "<<<<<<< HEAD" not in content
    assert '"status": "closed"' in content


def test_resolve_conflict_merge_strategy(beads_sync, mock_git_repo):
    """Test resolving conflict with smart merge strategy."""
    jsonl_file = mock_git_repo / ".beads" / "export.jsonl"
    jsonl_file.write_text('''<<<<<<< HEAD
{"id": "ISSUE-001", "status": "open", "updated_at": "2025-10-18T11:00:00Z"}
=======
{"id": "ISSUE-001", "status": "closed", "updated_at": "2025-10-18T10:00:00Z"}
>>>>>>> main
''')

    result = beads_sync.resolve_conflict(strategy="merge")

    assert result is True
    content = jsonl_file.read_text()
    assert "<<<<<<< HEAD" not in content
    # Should keep newer version based on timestamp
    assert '"status": "open"' in content


# =============================================================================
# Debounce Logic Tests
# =============================================================================

def test_debounce_sync_immediate_first_call(beads_sync):
    """Test that first sync happens immediately."""
    start_time = time.time()

    beads_sync.sync_with_debounce()

    elapsed = time.time() - start_time
    assert elapsed < 0.5  # Should be immediate


def test_debounce_sync_delayed_second_call(beads_sync):
    """Test that second sync within 5 seconds is debounced."""
    # First call
    beads_sync.sync_with_debounce()

    # Second call immediately after
    start_time = time.time()
    beads_sync.sync_with_debounce()
    elapsed = time.time() - start_time

    # Should return immediately without syncing
    assert elapsed < 0.5


def test_debounce_sync_after_delay(beads_sync):
    """Test that sync happens after debounce period."""
    # Mock time to avoid waiting
    with patch('time.time') as mock_time:
        mock_time.return_value = 1000.0

        # First call
        beads_sync.sync_with_debounce()

        # Advance time by 6 seconds
        mock_time.return_value = 1006.0

        # Second call should execute
        result = beads_sync.sync_with_debounce()

        assert result is True


def test_debounce_reset_on_error(beads_sync, mock_subprocess):
    """Test that debounce is reset on sync error."""
    # Use time mocking from the start
    with patch('amplihack.memory.beads_sync.time.time') as mock_time:
        mock_time.return_value = 1000.0

        # First successful call
        beads_sync.sync_with_debounce()

        # Advance time past debounce window
        mock_time.return_value = 1010.0

        # Patch force_sync to raise error
        with patch.object(beads_sync, 'force_sync', side_effect=RuntimeError("Sync failed")):
            with pytest.raises(RuntimeError):
                beads_sync.sync_with_debounce()

        # Debounce should be reset, advance time and try again
        mock_time.return_value = 1020.0
        result = beads_sync.sync_with_debounce()
        assert result is True


def test_get_last_sync_time(beads_sync):
    """Test retrieving last sync timestamp."""
    # No sync yet
    last_sync = beads_sync.get_last_sync_time()
    assert last_sync is None

    # After sync
    beads_sync.sync_with_debounce()
    last_sync = beads_sync.get_last_sync_time()

    assert last_sync is not None
    assert isinstance(last_sync, datetime)


def test_force_sync_bypasses_debounce(beads_sync):
    """Test that force_sync bypasses debounce logic."""
    # First call
    beads_sync.sync_with_debounce()

    # Immediate second call with force should execute
    result = beads_sync.force_sync()

    assert result is True


# =============================================================================
# Full Sync Workflow Tests
# =============================================================================

def test_full_sync_workflow_success(beads_sync, mock_subprocess):
    """Test complete sync workflow: export -> stage -> commit -> push."""
    sample_issues = [
        {"id": "ISSUE-001", "title": "Issue 1"}
    ]

    result = beads_sync.full_sync(sample_issues, message="Update beads state")

    assert result is True

    # Verify all steps executed
    calls = [str(call) for call in mock_subprocess.call_args_list]
    assert any('add' in str(call) for call in calls)  # Stage
    assert any('commit' in str(call) for call in calls)  # Commit
    assert any('push' in str(call) for call in calls)  # Push


def test_full_sync_workflow_with_conflict(beads_sync, mock_subprocess, mock_git_repo):
    """Test sync workflow handling merge conflict."""
    # Create conflict
    jsonl_file = mock_git_repo / ".beads" / "export.jsonl"
    jsonl_file.write_text('<<<<<<< HEAD\n{"id": "ISSUE-001"}\n=======\n')

    sample_issues = [{"id": "ISSUE-001"}]

    with pytest.raises(RuntimeError, match="merge conflict"):
        beads_sync.full_sync(sample_issues)


def test_sync_workflow_pull_before_push(beads_sync, mock_subprocess):
    """Test that sync pulls before pushing."""
    sample_issues = [{"id": "ISSUE-001"}]

    beads_sync.full_sync(sample_issues, pull_first=True)

    # Verify pull happens before push
    calls = [str(call) for call in mock_subprocess.call_args_list]
    pull_idx = next(i for i, c in enumerate(calls) if 'pull' in c)
    push_idx = next(i for i, c in enumerate(calls) if 'push' in c)
    assert pull_idx < push_idx


def test_sync_workflow_dry_run(beads_sync, mock_subprocess):
    """Test sync workflow in dry-run mode."""
    sample_issues = [{"id": "ISSUE-001"}]

    result = beads_sync.full_sync(sample_issues, dry_run=True)

    assert result is True

    # Should not execute git commands
    assert mock_subprocess.call_count == 0


# =============================================================================
# Error Handling Tests
# =============================================================================

def test_sync_with_git_not_initialized(beads_sync, mock_git_repo):
    """Test sync fails gracefully when git not initialized."""
    # Remove .git directory
    import shutil
    shutil.rmtree(mock_git_repo / ".git")

    with pytest.raises(RuntimeError, match="not a git repository"):
        beads_sync.is_git_clean()


def test_sync_with_beads_not_initialized(beads_sync, mock_git_repo):
    """Test sync fails gracefully when beads not initialized."""
    # Remove .beads directory
    import shutil
    shutil.rmtree(mock_git_repo / ".beads")

    with pytest.raises(RuntimeError, match="beads not initialized"):
        beads_sync.has_jsonl_export()


def test_sync_network_error_handling(beads_sync, mock_subprocess):
    """Test handling of network errors during push/pull."""
    mock_subprocess.side_effect = RuntimeError("Network unreachable")

    with pytest.raises(RuntimeError, match="Network unreachable"):
        beads_sync.push_export()


def test_sync_permission_error_handling(beads_sync, mock_subprocess):
    """Test handling of permission errors."""
    mock_subprocess.side_effect = PermissionError("Permission denied")

    with pytest.raises(RuntimeError, match="Permission denied"):
        beads_sync.stage_export()


# =============================================================================
# Performance Tests
# =============================================================================

def test_sync_completes_quickly(beads_sync, mock_subprocess):
    """Test that sync operation completes in reasonable time."""
    sample_issues = [{"id": f"ISSUE-{i:03d}"} for i in range(100)]

    start_time = time.time()
    beads_sync.full_sync(sample_issues, message="Bulk update")
    elapsed = time.time() - start_time

    # Should complete in under 1 second with mocked subprocess
    assert elapsed < 1.0


def test_debounce_prevents_excessive_syncs(beads_sync):
    """Test that debounce prevents excessive sync operations."""
    sync_count = 0

    original_sync = beads_sync.force_sync

    def count_syncs():
        nonlocal sync_count
        sync_count += 1
        return original_sync()

    with patch.object(beads_sync, 'force_sync', side_effect=count_syncs):
        # Trigger 10 syncs rapidly
        for _ in range(10):
            beads_sync.sync_with_debounce()

        # Only first should execute
        assert sync_count == 1


# =============================================================================
# Configuration Tests
# =============================================================================

def test_configure_debounce_delay(beads_sync):
    """Test configuring debounce delay."""
    beads_sync.set_debounce_delay(10)  # 10 seconds

    assert beads_sync.get_debounce_delay() == 10


def test_configure_sync_on_change(beads_sync):
    """Test enabling/disabling auto-sync on change."""
    beads_sync.set_auto_sync(True)
    assert beads_sync.is_auto_sync_enabled() is True

    beads_sync.set_auto_sync(False)
    assert beads_sync.is_auto_sync_enabled() is False


def test_get_sync_statistics(beads_sync):
    """Test retrieving sync statistics."""
    # Perform some syncs
    beads_sync.force_sync()
    beads_sync.force_sync()

    stats = beads_sync.get_sync_stats()

    assert stats["total_syncs"] == 2
    assert stats["last_sync_time"] is not None
    assert "success_rate" in stats
