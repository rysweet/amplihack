"""
Unit tests for BeadsMemoryProvider.

Tests the memory provider interface implementation for beads integration,
including issue creation, retrieval, updates, relationships, and error handling.

Following TDD approach - all tests should FAIL initially until implementation exists.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_beads_adapter():
    """Mock BeadsAdapter for isolated testing."""
    adapter = Mock()
    adapter.is_available.return_value = True
    adapter.create_issue.return_value = "ISSUE-001"
    adapter.get_issue.return_value = {
        "id": "ISSUE-001",
        "title": "Test Issue",
        "status": "open",
        "description": "Test description",
        "created_at": "2025-10-18T10:00:00Z",
        "relationships": []
    }
    return adapter


@pytest.fixture
def beads_provider(mock_beads_adapter):
    """Create BeadsMemoryProvider with mocked adapter."""
    # This import will fail initially (TDD)
    from amplihack.memory.beads_provider import BeadsMemoryProvider
    return BeadsMemoryProvider(adapter=mock_beads_adapter)


@pytest.fixture
def sample_issue_data():
    """Sample issue data for testing."""
    return {
        "title": "Implement user authentication",
        "description": "Add JWT-based authentication to API endpoints",
        "status": "open",
        "labels": ["feature", "security"],
        "assignee": "architect-agent"
    }


# =============================================================================
# Issue Creation Tests
# =============================================================================

def test_create_issue_success(beads_provider, mock_beads_adapter, sample_issue_data):
    """Test successful issue creation returns issue ID."""
    issue_id = beads_provider.create_issue(
        title=sample_issue_data["title"],
        description=sample_issue_data["description"],
        labels=sample_issue_data["labels"]
    )

    assert issue_id == "ISSUE-001"
    mock_beads_adapter.create_issue.assert_called_once()


def test_create_issue_with_all_fields(beads_provider, mock_beads_adapter):
    """Test issue creation with all optional fields."""
    mock_beads_adapter.update_issue.return_value = True

    issue_id = beads_provider.create_issue(
        title="Test Issue",
        description="Description",
        status="in_progress",
        labels=["bug", "critical"],
        assignee="test-agent",
        metadata={"priority": "high", "sprint": "2025-Q1"}
    )

    assert issue_id is not None
    create_call_args = mock_beads_adapter.create_issue.call_args
    assert create_call_args[1]["assignee"] == "test-agent"
    assert create_call_args[1]["metadata"]["priority"] == "high"

    # Status is set via update_issue since adapter.create_issue doesn't support it
    update_call_args = mock_beads_adapter.update_issue.call_args
    assert update_call_args[1]["status"] == "in_progress"


def test_create_issue_minimal_fields(beads_provider, mock_beads_adapter):
    """Test issue creation with only required fields."""
    issue_id = beads_provider.create_issue(
        title="Minimal Issue",
        description="Minimal description"
    )

    assert issue_id == "ISSUE-001"
    mock_beads_adapter.create_issue.assert_called_once()


def test_create_issue_empty_title_raises_error(beads_provider):
    """Test that empty title raises ValueError."""
    with pytest.raises(ValueError, match="title.*required"):
        beads_provider.create_issue(title="", description="Description")


def test_create_issue_empty_description_raises_error(beads_provider):
    """Test that empty description raises ValueError."""
    with pytest.raises(ValueError, match="description.*required"):
        beads_provider.create_issue(title="Title", description="")


def test_create_issue_adapter_unavailable_raises_error(beads_provider, mock_beads_adapter):
    """Test that unavailable adapter raises RuntimeError."""
    mock_beads_adapter.is_available.return_value = False

    with pytest.raises(RuntimeError, match="beads.*not available"):
        beads_provider.create_issue(title="Test", description="Test")


def test_create_issue_adapter_error_propagates(beads_provider, mock_beads_adapter):
    """Test that adapter errors propagate correctly."""
    mock_beads_adapter.create_issue.side_effect = RuntimeError("Beads CLI error")

    with pytest.raises(RuntimeError, match="Beads CLI error"):
        beads_provider.create_issue(title="Test", description="Test")


# =============================================================================
# Issue Retrieval Tests
# =============================================================================

def test_get_issue_success(beads_provider, mock_beads_adapter):
    """Test successful issue retrieval returns issue data."""
    issue = beads_provider.get_issue("ISSUE-001")

    assert issue is not None
    assert issue["id"] == "ISSUE-001"
    assert issue["title"] == "Test Issue"
    assert issue["status"] == "open"
    mock_beads_adapter.get_issue.assert_called_once_with("ISSUE-001")


def test_get_issue_not_found_returns_none(beads_provider, mock_beads_adapter):
    """Test that non-existent issue returns None."""
    mock_beads_adapter.get_issue.return_value = None

    issue = beads_provider.get_issue("NONEXISTENT")

    assert issue is None


def test_get_issue_with_relationships(beads_provider, mock_beads_adapter):
    """Test issue retrieval includes relationship data."""
    mock_beads_adapter.get_issue.return_value = {
        "id": "ISSUE-001",
        "title": "Test Issue",
        "status": "open",
        "relationships": [
            {"type": "blocks", "target_id": "ISSUE-002"},
            {"type": "related", "target_id": "ISSUE-003"}
        ]
    }

    issue = beads_provider.get_issue("ISSUE-001")

    assert len(issue["relationships"]) == 2
    assert issue["relationships"][0]["type"] == "blocks"


def test_get_issue_invalid_id_raises_error(beads_provider):
    """Test that invalid issue ID raises ValueError."""
    with pytest.raises(ValueError, match="issue.*id.*invalid"):
        beads_provider.get_issue("")


# =============================================================================
# Issue Update Tests
# =============================================================================

def test_update_issue_status(beads_provider, mock_beads_adapter):
    """Test updating issue status."""
    mock_beads_adapter.update_issue.return_value = True

    result = beads_provider.update_issue("ISSUE-001", status="in_progress")

    assert result is True
    mock_beads_adapter.update_issue.assert_called_once_with(
        "ISSUE-001", status="in_progress"
    )


def test_update_issue_multiple_fields(beads_provider, mock_beads_adapter):
    """Test updating multiple issue fields at once."""
    mock_beads_adapter.update_issue.return_value = True

    result = beads_provider.update_issue(
        "ISSUE-001",
        status="completed",
        assignee="new-agent",
        labels=["feature", "done"]
    )

    assert result is True
    call_args = mock_beads_adapter.update_issue.call_args
    assert call_args[1]["status"] == "completed"
    assert call_args[1]["assignee"] == "new-agent"


def test_update_issue_add_metadata(beads_provider, mock_beads_adapter):
    """Test adding metadata to existing issue."""
    mock_beads_adapter.update_issue.return_value = True

    result = beads_provider.update_issue(
        "ISSUE-001",
        metadata={"test_results": "passed", "duration": "5m"}
    )

    assert result is True


def test_update_issue_not_found_returns_false(beads_provider, mock_beads_adapter):
    """Test updating non-existent issue returns False."""
    mock_beads_adapter.update_issue.return_value = False

    result = beads_provider.update_issue("NONEXISTENT", status="closed")

    assert result is False


# =============================================================================
# Issue Closure Tests
# =============================================================================

def test_close_issue_success(beads_provider, mock_beads_adapter):
    """Test successful issue closure."""
    mock_beads_adapter.update_issue.return_value = True

    result = beads_provider.close_issue("ISSUE-001", resolution="completed")

    assert result is True
    call_args = mock_beads_adapter.update_issue.call_args
    assert call_args[1]["status"] == "closed"
    assert call_args[1]["resolution"] == "completed"


def test_close_issue_with_metadata(beads_provider, mock_beads_adapter):
    """Test closing issue with completion metadata."""
    mock_beads_adapter.update_issue.return_value = True

    result = beads_provider.close_issue(
        "ISSUE-001",
        resolution="completed",
        metadata={"closed_by": "test-agent", "notes": "All tests passing"}
    )

    assert result is True


def test_close_issue_already_closed(beads_provider, mock_beads_adapter):
    """Test closing already closed issue succeeds (idempotent)."""
    mock_beads_adapter.update_issue.return_value = True

    result = beads_provider.close_issue("ISSUE-001", resolution="completed")

    assert result is True


# =============================================================================
# Relationship Tests
# =============================================================================

def test_add_relationship_blocks(beads_provider, mock_beads_adapter):
    """Test adding 'blocks' relationship between issues."""
    mock_beads_adapter.add_relationship.return_value = True

    result = beads_provider.add_relationship(
        "ISSUE-001", "ISSUE-002", relationship_type="blocks"
    )

    assert result is True
    mock_beads_adapter.add_relationship.assert_called_once_with(
        "ISSUE-001", "ISSUE-002", "blocks"
    )


def test_add_relationship_related(beads_provider, mock_beads_adapter):
    """Test adding 'related' relationship between issues."""
    mock_beads_adapter.add_relationship.return_value = True

    result = beads_provider.add_relationship(
        "ISSUE-001", "ISSUE-003", relationship_type="related"
    )

    assert result is True


def test_add_relationship_parent_child(beads_provider, mock_beads_adapter):
    """Test adding parent-child relationship."""
    mock_beads_adapter.add_relationship.return_value = True

    result = beads_provider.add_relationship(
        "ISSUE-001", "ISSUE-004", relationship_type="parent-child"
    )

    assert result is True


def test_add_relationship_discovered_from(beads_provider, mock_beads_adapter):
    """Test adding 'discovered-from' relationship for investigation tracking."""
    mock_beads_adapter.add_relationship.return_value = True

    result = beads_provider.add_relationship(
        "ISSUE-001", "ISSUE-005", relationship_type="discovered-from"
    )

    assert result is True


def test_add_relationship_invalid_type_raises_error(beads_provider):
    """Test that invalid relationship type raises ValueError."""
    with pytest.raises(ValueError, match="relationship.*type.*invalid"):
        beads_provider.add_relationship(
            "ISSUE-001", "ISSUE-002", relationship_type="invalid-type"
        )


def test_add_relationship_same_issue_raises_error(beads_provider):
    """Test that self-referential relationship raises ValueError."""
    with pytest.raises(ValueError, match="cannot relate issue to itself"):
        beads_provider.add_relationship(
            "ISSUE-001", "ISSUE-001", relationship_type="blocks"
        )


# =============================================================================
# Relationship Retrieval Tests
# =============================================================================

def test_get_relationships_all_types(beads_provider, mock_beads_adapter):
    """Test retrieving all relationships for an issue."""
    mock_beads_adapter.get_relationships.return_value = [
        {"type": "blocks", "target_id": "ISSUE-002", "created_at": "2025-10-18T10:00:00Z"},
        {"type": "related", "target_id": "ISSUE-003", "created_at": "2025-10-18T10:00:00Z"}
    ]

    relationships = beads_provider.get_relationships("ISSUE-001")

    assert len(relationships) == 2
    assert relationships[0]["type"] == "blocks"
    assert relationships[1]["type"] == "related"


def test_get_relationships_filtered_by_type(beads_provider, mock_beads_adapter):
    """Test retrieving relationships filtered by type."""
    mock_beads_adapter.get_relationships.return_value = [
        {"type": "blocks", "target_id": "ISSUE-002"}
    ]

    relationships = beads_provider.get_relationships("ISSUE-001", relationship_type="blocks")

    assert len(relationships) == 1
    assert relationships[0]["type"] == "blocks"


def test_get_relationships_empty_list_when_none(beads_provider, mock_beads_adapter):
    """Test that issue with no relationships returns empty list."""
    mock_beads_adapter.get_relationships.return_value = []

    relationships = beads_provider.get_relationships("ISSUE-001")

    assert relationships == []


# =============================================================================
# Ready Work Query Tests
# =============================================================================

def test_get_ready_work_no_blockers(beads_provider, mock_beads_adapter):
    """Test retrieving issues with no blocking dependencies."""
    mock_beads_adapter.query_issues.return_value = [
        {"id": "ISSUE-001", "title": "Ready Issue 1", "status": "open"},
        {"id": "ISSUE-002", "title": "Ready Issue 2", "status": "open"}
    ]

    ready_issues = beads_provider.get_ready_work()

    assert len(ready_issues) == 2
    assert ready_issues[0]["id"] == "ISSUE-001"
    mock_beads_adapter.query_issues.assert_called_once_with(
        status="open", has_blockers=False
    )


def test_get_ready_work_filtered_by_assignee(beads_provider, mock_beads_adapter):
    """Test retrieving ready work for specific agent."""
    mock_beads_adapter.query_issues.return_value = [
        {"id": "ISSUE-001", "title": "Ready Issue", "assignee": "builder-agent"}
    ]

    ready_issues = beads_provider.get_ready_work(assignee="builder-agent")

    assert len(ready_issues) == 1
    assert ready_issues[0]["assignee"] == "builder-agent"


def test_get_ready_work_filtered_by_labels(beads_provider, mock_beads_adapter):
    """Test retrieving ready work filtered by labels."""
    mock_beads_adapter.query_issues.return_value = [
        {"id": "ISSUE-001", "labels": ["feature", "high-priority"]}
    ]

    ready_issues = beads_provider.get_ready_work(labels=["feature"])

    assert len(ready_issues) == 1


def test_get_ready_work_empty_when_all_blocked(beads_provider, mock_beads_adapter):
    """Test that no ready work returned when all issues are blocked."""
    mock_beads_adapter.query_issues.return_value = []

    ready_issues = beads_provider.get_ready_work()

    assert ready_issues == []


# =============================================================================
# Error Handling Tests
# =============================================================================

def test_provider_unavailable_beads_not_installed(mock_beads_adapter):
    """Test provider reports unavailable when beads not installed."""
    mock_beads_adapter.is_available.return_value = False

    from amplihack.memory.beads_provider import BeadsMemoryProvider
    provider = BeadsMemoryProvider(adapter=mock_beads_adapter)

    assert provider.is_available() is False


def test_provider_unavailable_beads_not_initialized(mock_beads_adapter):
    """Test provider reports unavailable when beads not initialized in repo."""
    mock_beads_adapter.is_available.return_value = False
    mock_beads_adapter.check_init.return_value = False

    from amplihack.memory.beads_provider import BeadsMemoryProvider
    provider = BeadsMemoryProvider(adapter=mock_beads_adapter)

    assert provider.is_available() is False


def test_adapter_error_wrapped_with_context(beads_provider, mock_beads_adapter):
    """Test that adapter errors are wrapped with helpful context."""
    mock_beads_adapter.create_issue.side_effect = Exception("Generic error")

    with pytest.raises(RuntimeError, match="Failed to create issue.*Generic error"):
        beads_provider.create_issue(title="Test", description="Test")


def test_retry_on_transient_failure(beads_provider, mock_beads_adapter):
    """Test automatic retry on transient failures."""
    # First call fails, second succeeds
    mock_beads_adapter.create_issue.side_effect = [
        RuntimeError("Temporary error"),
        "ISSUE-001"
    ]

    issue_id = beads_provider.create_issue(title="Test", description="Test", retry=True)

    assert issue_id == "ISSUE-001"
    assert mock_beads_adapter.create_issue.call_count == 2


# =============================================================================
# Performance Tests
# =============================================================================

def test_get_issue_completes_quickly(beads_provider, mock_beads_adapter):
    """Test that issue retrieval completes in under 100ms."""
    import time

    start = time.time()
    beads_provider.get_issue("ISSUE-001")
    duration = time.time() - start

    assert duration < 0.1, f"get_issue took {duration*1000:.1f}ms, expected < 100ms"


def test_get_relationships_completes_quickly(beads_provider, mock_beads_adapter):
    """Test that relationship retrieval completes in under 100ms."""
    import time

    mock_beads_adapter.get_relationships.return_value = [
        {"type": "blocks", "target_id": f"ISSUE-{i:03d}"} for i in range(10)
    ]

    start = time.time()
    beads_provider.get_relationships("ISSUE-001")
    duration = time.time() - start

    assert duration < 0.1, f"get_relationships took {duration*1000:.1f}ms, expected < 100ms"


# =============================================================================
# Integration with Memory Manager Interface Tests
# =============================================================================

def test_implements_memory_provider_interface(beads_provider):
    """Test that BeadsMemoryProvider implements MemoryProvider interface."""
    # Check required methods exist
    assert hasattr(beads_provider, 'create_issue')
    assert hasattr(beads_provider, 'get_issue')
    assert hasattr(beads_provider, 'update_issue')
    assert hasattr(beads_provider, 'close_issue')
    assert hasattr(beads_provider, 'add_relationship')
    assert hasattr(beads_provider, 'get_relationships')
    assert hasattr(beads_provider, 'get_ready_work')
    assert hasattr(beads_provider, 'is_available')


def test_provider_type_identifier(beads_provider):
    """Test that provider correctly identifies its type."""
    assert beads_provider.provider_type() == "beads"
