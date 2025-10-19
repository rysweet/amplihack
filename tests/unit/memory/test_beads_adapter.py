"""
Unit tests for BeadsAdapter.

Tests the CLI wrapper for beads command-line tool, including:
- Command construction
- JSON output parsing
- Subprocess error handling
- Retry logic for transient failures

Following TDD approach - all tests should FAIL initially until implementation exists.
"""

import pytest
import subprocess
import json
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def beads_adapter():
    """Create BeadsAdapter instance for testing."""
    # This import will fail initially (TDD)
    from amplihack.memory.beads_adapter import BeadsAdapter
    return BeadsAdapter()


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for CLI command testing."""
    with patch('subprocess.run') as mock:
        # Default success response
        mock.return_value = subprocess.CompletedProcess(
            args=['bd'],
            returncode=0,
            stdout='{"status": "success"}',
            stderr=''
        )
        yield mock


@pytest.fixture
def sample_issue_json():
    """Sample issue JSON output from beads CLI."""
    return json.dumps({
        "id": "ISSUE-001",
        "title": "Test Issue",
        "description": "Test description",
        "status": "open",
        "created_at": "2025-10-18T10:00:00Z",
        "updated_at": "2025-10-18T10:00:00Z",
        "labels": ["feature"],
        "assignee": "test-agent",
        "relationships": []
    })


# =============================================================================
# Beads CLI Availability Tests
# =============================================================================

def test_is_available_when_bd_in_path(beads_adapter, mock_subprocess):
    """Test that is_available returns True when 'bd' command exists."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['which', 'bd'],
        returncode=0,
        stdout='/usr/local/bin/bd\n',
        stderr=''
    )

    assert beads_adapter.is_available() is True


def test_is_available_when_bd_not_in_path(beads_adapter, mock_subprocess):
    """Test that is_available returns False when 'bd' command not found."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['which', 'bd'],
        returncode=1,
        stdout='',
        stderr='bd not found'
    )

    assert beads_adapter.is_available() is False


def test_is_available_caches_result(beads_adapter, mock_subprocess):
    """Test that availability check is cached to avoid repeated checks."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['which', 'bd'],
        returncode=0,
        stdout='/usr/local/bin/bd\n',
        stderr=''
    )

    # Call twice
    beads_adapter.is_available()
    beads_adapter.is_available()

    # Should only check once
    assert mock_subprocess.call_count == 1


def test_check_init_success(beads_adapter, mock_subprocess):
    """Test checking if beads is initialized in current repo."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'status'],
        returncode=0,
        stdout='{"initialized": true}',
        stderr=''
    )

    assert beads_adapter.check_init() is True


def test_check_init_not_initialized(beads_adapter, mock_subprocess):
    """Test checking repo without beads initialization."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'status'],
        returncode=1,
        stdout='',
        stderr='Not a beads repository'
    )

    assert beads_adapter.check_init() is False


# =============================================================================
# Issue Creation Command Tests
# =============================================================================

def test_create_issue_basic_command(beads_adapter, mock_subprocess, sample_issue_json):
    """Test basic issue creation command construction."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'create'],
        returncode=0,
        stdout='{"id": "ISSUE-001"}',
        stderr=''
    )

    issue_id = beads_adapter.create_issue(
        title="Test Issue",
        description="Test description"
    )

    assert issue_id == "ISSUE-001"

    # Verify command construction
    call_args = mock_subprocess.call_args[0][0]
    assert call_args[0] == 'bd'
    assert call_args[1] == 'create'
    assert '--json' in call_args


def test_create_issue_with_labels(beads_adapter, mock_subprocess):
    """Test issue creation with labels."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'create'],
        returncode=0,
        stdout='{"id": "ISSUE-002"}',
        stderr=''
    )

    beads_adapter.create_issue(
        title="Test Issue",
        description="Test",
        labels=["bug", "critical"]
    )

    call_args = mock_subprocess.call_args[0][0]
    assert '--label' in call_args or '-l' in call_args
    assert 'bug' in call_args
    assert 'critical' in call_args


def test_create_issue_with_assignee(beads_adapter, mock_subprocess):
    """Test issue creation with assignee."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'create'],
        returncode=0,
        stdout='{"id": "ISSUE-003"}',
        stderr=''
    )

    beads_adapter.create_issue(
        title="Test Issue",
        description="Test",
        assignee="builder-agent"
    )

    call_args = mock_subprocess.call_args[0][0]
    assert '--assignee' in call_args or '-a' in call_args
    assert 'builder-agent' in call_args


def test_create_issue_with_metadata(beads_adapter, mock_subprocess):
    """Test issue creation with custom metadata."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'create'],
        returncode=0,
        stdout='{"id": "ISSUE-004"}',
        stderr=''
    )

    beads_adapter.create_issue(
        title="Test Issue",
        description="Test",
        metadata={"priority": "high", "sprint": "2025-Q1"}
    )

    call_args = mock_subprocess.call_args[0][0]
    # Metadata should be passed as JSON or key-value pairs
    assert '--metadata' in call_args or '-m' in call_args


def test_create_issue_cli_error_raises_exception(beads_adapter, mock_subprocess):
    """Test that CLI errors are properly raised."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'create'],
        returncode=1,
        stdout='',
        stderr='Error: Invalid issue format'
    )

    with pytest.raises(RuntimeError, match="Invalid issue format"):
        beads_adapter.create_issue(title="Test", description="Test")


# =============================================================================
# Issue Retrieval Tests
# =============================================================================

def test_get_issue_success(beads_adapter, mock_subprocess, sample_issue_json):
    """Test successful issue retrieval."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'get', 'ISSUE-001'],
        returncode=0,
        stdout=sample_issue_json,
        stderr=''
    )

    issue = beads_adapter.get_issue("ISSUE-001")

    assert issue is not None
    assert issue["id"] == "ISSUE-001"
    assert issue["title"] == "Test Issue"

    call_args = mock_subprocess.call_args[0][0]
    assert 'bd' in call_args
    assert 'get' in call_args
    assert 'ISSUE-001' in call_args
    assert '--json' in call_args


def test_get_issue_not_found(beads_adapter, mock_subprocess):
    """Test retrieving non-existent issue."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'get', 'NONEXISTENT'],
        returncode=1,
        stdout='',
        stderr='Error: Issue not found'
    )

    issue = beads_adapter.get_issue("NONEXISTENT")

    assert issue is None


def test_get_issue_invalid_json_raises_error(beads_adapter, mock_subprocess):
    """Test that invalid JSON from CLI raises parsing error."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'get', 'ISSUE-001'],
        returncode=0,
        stdout='Invalid JSON {',
        stderr=''
    )

    with pytest.raises(json.JSONDecodeError):
        beads_adapter.get_issue("ISSUE-001")


# =============================================================================
# Issue Update Tests
# =============================================================================

def test_update_issue_status(beads_adapter, mock_subprocess):
    """Test updating issue status."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'update'],
        returncode=0,
        stdout='{"success": true}',
        stderr=''
    )

    result = beads_adapter.update_issue("ISSUE-001", status="in_progress")

    assert result is True

    call_args = mock_subprocess.call_args[0][0]
    assert 'bd' in call_args
    assert 'update' in call_args
    assert 'ISSUE-001' in call_args
    assert '--status' in call_args
    assert 'in_progress' in call_args


def test_update_issue_multiple_fields(beads_adapter, mock_subprocess):
    """Test updating multiple fields at once."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'update'],
        returncode=0,
        stdout='{"success": true}',
        stderr=''
    )

    result = beads_adapter.update_issue(
        "ISSUE-001",
        status="completed",
        assignee="new-agent",
        labels=["done"]
    )

    assert result is True


def test_update_issue_cli_error(beads_adapter, mock_subprocess):
    """Test that update errors are properly handled."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'update'],
        returncode=1,
        stdout='',
        stderr='Error: Issue not found'
    )

    result = beads_adapter.update_issue("NONEXISTENT", status="closed")

    assert result is False


# =============================================================================
# Relationship Management Tests
# =============================================================================

def test_add_relationship_blocks(beads_adapter, mock_subprocess):
    """Test adding 'blocks' relationship."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'relate'],
        returncode=0,
        stdout='{"success": true}',
        stderr=''
    )

    result = beads_adapter.add_relationship("ISSUE-001", "ISSUE-002", "blocks")

    assert result is True

    call_args = mock_subprocess.call_args[0][0]
    assert 'bd' in call_args
    assert 'relate' in call_args or 'link' in call_args
    assert 'ISSUE-001' in call_args
    assert 'ISSUE-002' in call_args
    assert 'blocks' in call_args


def test_add_relationship_related(beads_adapter, mock_subprocess):
    """Test adding 'related' relationship."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'relate'],
        returncode=0,
        stdout='{"success": true}',
        stderr=''
    )

    result = beads_adapter.add_relationship("ISSUE-001", "ISSUE-003", "related")

    assert result is True


def test_get_relationships(beads_adapter, mock_subprocess):
    """Test retrieving issue relationships."""
    relationships_json = json.dumps([
        {"type": "blocks", "target_id": "ISSUE-002", "created_at": "2025-10-18T10:00:00Z"},
        {"type": "related", "target_id": "ISSUE-003", "created_at": "2025-10-18T10:00:00Z"}
    ])

    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'relationships'],
        returncode=0,
        stdout=relationships_json,
        stderr=''
    )

    relationships = beads_adapter.get_relationships("ISSUE-001")

    assert len(relationships) == 2
    assert relationships[0]["type"] == "blocks"
    assert relationships[1]["type"] == "related"


def test_get_relationships_filtered_by_type(beads_adapter, mock_subprocess):
    """Test retrieving relationships filtered by type."""
    relationships_json = json.dumps([
        {"type": "blocks", "target_id": "ISSUE-002"}
    ])

    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'relationships'],
        returncode=0,
        stdout=relationships_json,
        stderr=''
    )

    relationships = beads_adapter.get_relationships("ISSUE-001", relationship_type="blocks")

    assert len(relationships) == 1

    call_args = mock_subprocess.call_args[0][0]
    assert '--type' in call_args
    assert 'blocks' in call_args


# =============================================================================
# Issue Query Tests
# =============================================================================

def test_query_issues_by_status(beads_adapter, mock_subprocess):
    """Test querying issues by status."""
    issues_json = json.dumps([
        {"id": "ISSUE-001", "status": "open"},
        {"id": "ISSUE-002", "status": "open"}
    ])

    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'query'],
        returncode=0,
        stdout=issues_json,
        stderr=''
    )

    issues = beads_adapter.query_issues(status="open")

    assert len(issues) == 2

    call_args = mock_subprocess.call_args[0][0]
    assert 'bd' in call_args
    assert 'query' in call_args or 'list' in call_args
    assert '--status' in call_args
    assert 'open' in call_args


def test_query_issues_by_assignee(beads_adapter, mock_subprocess):
    """Test querying issues by assignee."""
    issues_json = json.dumps([
        {"id": "ISSUE-001", "assignee": "builder-agent"}
    ])

    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'query'],
        returncode=0,
        stdout=issues_json,
        stderr=''
    )

    issues = beads_adapter.query_issues(assignee="builder-agent")

    assert len(issues) == 1


def test_query_issues_with_no_blockers(beads_adapter, mock_subprocess):
    """Test querying issues with no blocking dependencies (ready work)."""
    issues_json = json.dumps([
        {"id": "ISSUE-001", "status": "open", "blocked": False},
        {"id": "ISSUE-002", "status": "open", "blocked": False}
    ])

    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'query'],
        returncode=0,
        stdout=issues_json,
        stderr=''
    )

    issues = beads_adapter.query_issues(status="open", has_blockers=False)

    assert len(issues) == 2

    call_args = mock_subprocess.call_args[0][0]
    assert '--no-blockers' in call_args or '--ready' in call_args


def test_query_issues_by_labels(beads_adapter, mock_subprocess):
    """Test querying issues by labels."""
    issues_json = json.dumps([
        {"id": "ISSUE-001", "labels": ["bug", "critical"]}
    ])

    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'query'],
        returncode=0,
        stdout=issues_json,
        stderr=''
    )

    issues = beads_adapter.query_issues(labels=["bug"])

    assert len(issues) == 1


# =============================================================================
# JSON Output Parsing Tests
# =============================================================================

def test_parse_json_output_success(beads_adapter):
    """Test successful JSON parsing."""
    json_str = '{"id": "ISSUE-001", "title": "Test"}'

    result = beads_adapter._parse_json_output(json_str)

    assert result["id"] == "ISSUE-001"
    assert result["title"] == "Test"


def test_parse_json_output_with_whitespace(beads_adapter):
    """Test JSON parsing handles leading/trailing whitespace."""
    json_str = '\n  {"id": "ISSUE-001"}  \n'

    result = beads_adapter._parse_json_output(json_str)

    assert result["id"] == "ISSUE-001"


def test_parse_json_output_empty_string(beads_adapter):
    """Test parsing empty JSON output."""
    with pytest.raises(json.JSONDecodeError):
        beads_adapter._parse_json_output('')


def test_parse_json_output_invalid_json(beads_adapter):
    """Test parsing invalid JSON raises error."""
    with pytest.raises(json.JSONDecodeError):
        beads_adapter._parse_json_output('Not valid JSON {')


def test_parse_json_output_array(beads_adapter):
    """Test parsing JSON array."""
    json_str = '[{"id": "ISSUE-001"}, {"id": "ISSUE-002"}]'

    result = beads_adapter._parse_json_output(json_str)

    assert isinstance(result, list)
    assert len(result) == 2


# =============================================================================
# Subprocess Error Handling Tests
# =============================================================================

def test_subprocess_timeout_raises_error(beads_adapter, mock_subprocess):
    """Test that subprocess timeout is properly handled."""
    mock_subprocess.side_effect = subprocess.TimeoutExpired(
        cmd='bd get ISSUE-001',
        timeout=30
    )

    with pytest.raises(RuntimeError, match="timeout"):
        beads_adapter.get_issue("ISSUE-001")


def test_subprocess_called_process_error(beads_adapter, mock_subprocess):
    """Test handling of CalledProcessError."""
    mock_subprocess.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd='bd get ISSUE-001',
        output='',
        stderr='Error: Issue not found'
    )

    # CalledProcessError is caught and wrapped, but get_issue returns None for "not found" errors
    result = beads_adapter.get_issue("ISSUE-001")
    assert result is None


def test_subprocess_permission_error(beads_adapter, mock_subprocess):
    """Test handling of permission errors."""
    mock_subprocess.side_effect = PermissionError("Permission denied: bd")

    with pytest.raises(RuntimeError, match="Permission denied"):
        beads_adapter.get_issue("ISSUE-001")


# =============================================================================
# Retry Logic Tests
# =============================================================================

def test_retry_on_transient_failure(beads_adapter, mock_subprocess):
    """Test automatic retry on transient failures."""
    # First call fails with transient error, second succeeds
    mock_subprocess.side_effect = [
        subprocess.CompletedProcess(
            args=['bd', 'get'],
            returncode=1,
            stdout='',
            stderr='Error: Temporary lock file exists'
        ),
        subprocess.CompletedProcess(
            args=['bd', 'get'],
            returncode=0,
            stdout='{"id": "ISSUE-001"}',
            stderr=''
        )
    ]

    issue = beads_adapter.get_issue("ISSUE-001", retry=True)

    assert issue["id"] == "ISSUE-001"
    assert mock_subprocess.call_count == 2


def test_retry_max_attempts(beads_adapter, mock_subprocess):
    """Test that retry stops after max attempts."""
    # All calls fail with a transient error that triggers retry
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', 'get'],
        returncode=1,
        stdout='',
        stderr='Error: Temporary lock file exists'
    )

    with pytest.raises(RuntimeError):
        beads_adapter.get_issue("ISSUE-001", retry=True, max_retries=3)

    # Should try initial + 3 retries = 4 total
    assert mock_subprocess.call_count == 4


def test_retry_exponential_backoff(beads_adapter, mock_subprocess):
    """Test that retry uses exponential backoff."""
    import time

    call_times = []

    def track_time(*args, **kwargs):
        call_times.append(time.time())
        return subprocess.CompletedProcess(
            args=['bd', 'get'],
            returncode=1,
            stdout='',
            stderr='Error: Transient'
        )

    mock_subprocess.side_effect = track_time

    try:
        beads_adapter.get_issue("ISSUE-001", retry=True, max_retries=2)
    except RuntimeError:
        pass

    # Verify delays increase (approximately 1s, 2s pattern)
    if len(call_times) >= 2:
        delay1 = call_times[1] - call_times[0]
        assert 0.5 < delay1 < 1.5  # ~1 second
        if len(call_times) >= 3:
            delay2 = call_times[2] - call_times[1]
            assert 1.5 < delay2 < 2.5  # ~2 seconds


# =============================================================================
# Command Construction Helpers Tests
# =============================================================================

def test_build_command_basic(beads_adapter):
    """Test basic command building."""
    cmd = beads_adapter._build_command('get', 'ISSUE-001')

    assert cmd[0] == 'bd'
    assert cmd[1] == 'get'
    assert 'ISSUE-001' in cmd
    assert '--json' in cmd


def test_build_command_with_flags(beads_adapter):
    """Test command building with boolean flags."""
    cmd = beads_adapter._build_command(
        'query',
        status='open',
        no_blockers=True
    )

    assert '--status' in cmd
    assert 'open' in cmd
    assert '--no-blockers' in cmd


def test_build_command_with_list_args(beads_adapter):
    """Test command building with list arguments."""
    cmd = beads_adapter._build_command(
        'create',
        labels=['bug', 'critical']
    )

    # Implementation uses --labels (plural)
    assert '--labels' in cmd
    assert 'bug' in cmd
    assert 'critical' in cmd


# =============================================================================
# Version Check Tests
# =============================================================================

def test_get_version(beads_adapter, mock_subprocess):
    """Test getting beads CLI version."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', '--version'],
        returncode=0,
        stdout='beads 0.1.0\n',
        stderr=''
    )

    version = beads_adapter.get_version()

    assert version == "0.1.0"


def test_check_version_compatibility(beads_adapter, mock_subprocess):
    """Test version compatibility checking."""
    mock_subprocess.return_value = subprocess.CompletedProcess(
        args=['bd', '--version'],
        returncode=0,
        stdout='beads 0.1.0\n',
        stderr=''
    )

    is_compatible = beads_adapter.check_version_compatibility(min_version="0.1.0")

    assert is_compatible is True
