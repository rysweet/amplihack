"""
Unit tests for Beads data models.

Tests dataclass validation, JSON serialization/deserialization, and model conversions
for BeadsIssue, BeadsRelationship, BeadsWorkstream, and related models.

Following TDD approach - all tests should FAIL initially until implementation exists.
"""

import pytest
import json
from datetime import datetime
from typing import List, Dict, Any


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_issue_data():
    """Sample issue data for model creation."""
    return {
        "id": "ISSUE-001",
        "title": "Implement authentication",
        "description": "Add JWT-based authentication to API endpoints",
        "status": "open",
        "created_at": "2025-10-18T10:00:00Z",
        "updated_at": "2025-10-18T10:00:00Z",
        "labels": ["feature", "security"],
        "assignee": "architect-agent",
        "metadata": {"priority": "high", "sprint": "2025-Q1"}
    }


@pytest.fixture
def sample_relationship_data():
    """Sample relationship data."""
    return {
        "type": "blocks",
        "source_id": "ISSUE-001",
        "target_id": "ISSUE-002",
        "created_at": "2025-10-18T10:00:00Z",
        "metadata": {"reason": "Dependency on API design"}
    }


@pytest.fixture
def sample_workstream_data():
    """Sample workstream data."""
    return {
        "id": "WS-001",
        "name": "Authentication Feature",
        "description": "Implement complete authentication system",
        "status": "active",
        "issues": ["ISSUE-001", "ISSUE-002", "ISSUE-003"],
        "created_at": "2025-10-18T09:00:00Z"
    }


# =============================================================================
# BeadsIssue Model Tests
# =============================================================================

def test_beads_issue_creation_with_all_fields(sample_issue_data):
    """Test creating BeadsIssue with all fields."""
    from amplihack.memory.beads_models import BeadsIssue

    issue = BeadsIssue(**sample_issue_data)

    assert issue.id == "ISSUE-001"
    assert issue.title == "Implement authentication"
    assert issue.status == "open"
    assert len(issue.labels) == 2
    assert issue.assignee == "architect-agent"
    assert issue.metadata["priority"] == "high"


def test_beads_issue_creation_minimal_fields():
    """Test creating BeadsIssue with only required fields."""
    from amplihack.memory.beads_models import BeadsIssue

    issue = BeadsIssue(
        id="ISSUE-002",
        title="Test Issue",
        description="Test description",
        status="open",
        created_at="2025-10-18T10:00:00Z",
        updated_at="2025-10-18T10:00:00Z"
    )

    assert issue.id == "ISSUE-002"
    assert issue.title == "Test Issue"
    assert issue.labels == []  # Default empty list
    assert issue.assignee is None


def test_beads_issue_validation_empty_id():
    """Test that empty ID raises validation error."""
    from amplihack.memory.beads_models import BeadsIssue

    with pytest.raises(ValueError, match="id.*cannot be empty"):
        BeadsIssue(
            id="",
            title="Test",
            description="Test",
            status="open",
            created_at="2025-10-18T10:00:00Z",
            updated_at="2025-10-18T10:00:00Z"
        )


def test_beads_issue_validation_empty_title():
    """Test that empty title raises validation error."""
    from amplihack.memory.beads_models import BeadsIssue

    with pytest.raises(ValueError, match="title.*cannot be empty"):
        BeadsIssue(
            id="ISSUE-001",
            title="",
            description="Test",
            status="open",
            created_at="2025-10-18T10:00:00Z",
            updated_at="2025-10-18T10:00:00Z"
        )


def test_beads_issue_validation_invalid_status():
    """Test that invalid status raises validation error."""
    from amplihack.memory.beads_models import BeadsIssue

    with pytest.raises(ValueError, match="status.*must be one of"):
        BeadsIssue(
            id="ISSUE-001",
            title="Test",
            description="Test",
            status="invalid_status",
            created_at="2025-10-18T10:00:00Z",
            updated_at="2025-10-18T10:00:00Z"
        )


def test_beads_issue_status_values():
    """Test that all valid status values are accepted."""
    from amplihack.memory.beads_models import BeadsIssue

    valid_statuses = ["open", "in_progress", "blocked", "completed", "closed"]

    for status in valid_statuses:
        issue = BeadsIssue(
            id=f"ISSUE-{status}",
            title="Test",
            description="Test",
            status=status,
            created_at="2025-10-18T10:00:00Z",
            updated_at="2025-10-18T10:00:00Z"
        )
        assert issue.status == status


def test_beads_issue_to_dict(sample_issue_data):
    """Test converting BeadsIssue to dictionary."""
    from amplihack.memory.beads_models import BeadsIssue

    issue = BeadsIssue(**sample_issue_data)
    issue_dict = issue.to_dict()

    assert issue_dict["id"] == "ISSUE-001"
    assert issue_dict["title"] == "Implement authentication"
    assert issue_dict["labels"] == ["feature", "security"]
    assert isinstance(issue_dict, dict)


def test_beads_issue_from_dict(sample_issue_data):
    """Test creating BeadsIssue from dictionary."""
    from amplihack.memory.beads_models import BeadsIssue

    issue = BeadsIssue.from_dict(sample_issue_data)

    assert issue.id == "ISSUE-001"
    assert issue.title == "Implement authentication"


def test_beads_issue_to_json(sample_issue_data):
    """Test converting BeadsIssue to JSON string."""
    from amplihack.memory.beads_models import BeadsIssue

    issue = BeadsIssue(**sample_issue_data)
    json_str = issue.to_json()

    assert isinstance(json_str, str)
    parsed = json.loads(json_str)
    assert parsed["id"] == "ISSUE-001"


def test_beads_issue_from_json(sample_issue_data):
    """Test creating BeadsIssue from JSON string."""
    from amplihack.memory.beads_models import BeadsIssue

    json_str = json.dumps(sample_issue_data)
    issue = BeadsIssue.from_json(json_str)

    assert issue.id == "ISSUE-001"
    assert issue.title == "Implement authentication"


def test_beads_issue_datetime_parsing():
    """Test that datetime strings are properly parsed."""
    from amplihack.memory.beads_models import BeadsIssue

    issue = BeadsIssue(
        id="ISSUE-001",
        title="Test",
        description="Test",
        status="open",
        created_at="2025-10-18T10:00:00Z",
        updated_at="2025-10-18T11:00:00Z"
    )

    # Should accept ISO format strings
    assert issue.created_at == "2025-10-18T10:00:00Z"
    assert issue.updated_at == "2025-10-18T11:00:00Z"


# =============================================================================
# BeadsRelationship Model Tests
# =============================================================================

def test_beads_relationship_creation(sample_relationship_data):
    """Test creating BeadsRelationship with all fields."""
    from amplihack.memory.beads_models import BeadsRelationship

    rel = BeadsRelationship(**sample_relationship_data)

    assert rel.type == "blocks"
    assert rel.source_id == "ISSUE-001"
    assert rel.target_id == "ISSUE-002"
    assert rel.metadata["reason"] == "Dependency on API design"


def test_beads_relationship_types():
    """Test all valid relationship types."""
    from amplihack.memory.beads_models import BeadsRelationship

    valid_types = ["blocks", "blocked_by", "related", "parent", "child", "discovered-from"]

    for rel_type in valid_types:
        rel = BeadsRelationship(
            type=rel_type,
            source_id="ISSUE-001",
            target_id="ISSUE-002",
            created_at="2025-10-18T10:00:00Z"
        )
        assert rel.type == rel_type


def test_beads_relationship_invalid_type():
    """Test that invalid relationship type raises error."""
    from amplihack.memory.beads_models import BeadsRelationship

    with pytest.raises(ValueError, match="relationship type.*invalid"):
        BeadsRelationship(
            type="invalid-type",
            source_id="ISSUE-001",
            target_id="ISSUE-002",
            created_at="2025-10-18T10:00:00Z"
        )


def test_beads_relationship_self_reference():
    """Test that self-referential relationship raises error."""
    from amplihack.memory.beads_models import BeadsRelationship

    with pytest.raises(ValueError, match="cannot relate issue to itself"):
        BeadsRelationship(
            type="blocks",
            source_id="ISSUE-001",
            target_id="ISSUE-001",
            created_at="2025-10-18T10:00:00Z"
        )


def test_beads_relationship_to_dict(sample_relationship_data):
    """Test converting BeadsRelationship to dictionary."""
    from amplihack.memory.beads_models import BeadsRelationship

    rel = BeadsRelationship(**sample_relationship_data)
    rel_dict = rel.to_dict()

    assert rel_dict["type"] == "blocks"
    assert rel_dict["source_id"] == "ISSUE-001"
    assert rel_dict["target_id"] == "ISSUE-002"


def test_beads_relationship_from_dict(sample_relationship_data):
    """Test creating BeadsRelationship from dictionary."""
    from amplihack.memory.beads_models import BeadsRelationship

    rel = BeadsRelationship.from_dict(sample_relationship_data)

    assert rel.type == "blocks"
    assert rel.source_id == "ISSUE-001"


def test_beads_relationship_bidirectional():
    """Test creating bidirectional relationship pair."""
    from amplihack.memory.beads_models import BeadsRelationship

    # Create "blocks" relationship
    blocks_rel = BeadsRelationship(
        type="blocks",
        source_id="ISSUE-001",
        target_id="ISSUE-002",
        created_at="2025-10-18T10:00:00Z"
    )

    # Create inverse "blocked_by" relationship
    blocked_by_rel = blocks_rel.create_inverse()

    assert blocked_by_rel.type == "blocked_by"
    assert blocked_by_rel.source_id == "ISSUE-002"
    assert blocked_by_rel.target_id == "ISSUE-001"


# =============================================================================
# BeadsWorkstream Model Tests
# =============================================================================

def test_beads_workstream_creation(sample_workstream_data):
    """Test creating BeadsWorkstream with all fields."""
    from amplihack.memory.beads_models import BeadsWorkstream

    ws = BeadsWorkstream(**sample_workstream_data)

    assert ws.id == "WS-001"
    assert ws.name == "Authentication Feature"
    assert ws.status == "active"
    assert len(ws.issues) == 3


def test_beads_workstream_minimal_fields():
    """Test creating BeadsWorkstream with minimal fields."""
    from amplihack.memory.beads_models import BeadsWorkstream

    ws = BeadsWorkstream(
        id="WS-002",
        name="Test Workstream",
        description="Test",
        status="active",
        created_at="2025-10-18T10:00:00Z"
    )

    assert ws.id == "WS-002"
    assert ws.issues == []  # Default empty list


def test_beads_workstream_add_issue():
    """Test adding issue to workstream."""
    from amplihack.memory.beads_models import BeadsWorkstream

    ws = BeadsWorkstream(
        id="WS-001",
        name="Test",
        description="Test",
        status="active",
        created_at="2025-10-18T10:00:00Z"
    )

    ws.add_issue("ISSUE-001")

    assert "ISSUE-001" in ws.issues
    assert len(ws.issues) == 1


def test_beads_workstream_remove_issue():
    """Test removing issue from workstream."""
    from amplihack.memory.beads_models import BeadsWorkstream

    ws = BeadsWorkstream(
        id="WS-001",
        name="Test",
        description="Test",
        status="active",
        issues=["ISSUE-001", "ISSUE-002"],
        created_at="2025-10-18T10:00:00Z"
    )

    ws.remove_issue("ISSUE-001")

    assert "ISSUE-001" not in ws.issues
    assert len(ws.issues) == 1


def test_beads_workstream_duplicate_issue():
    """Test that adding duplicate issue is prevented."""
    from amplihack.memory.beads_models import BeadsWorkstream

    ws = BeadsWorkstream(
        id="WS-001",
        name="Test",
        description="Test",
        status="active",
        issues=["ISSUE-001"],
        created_at="2025-10-18T10:00:00Z"
    )

    ws.add_issue("ISSUE-001")  # Try to add duplicate

    assert ws.issues.count("ISSUE-001") == 1


def test_beads_workstream_status_values():
    """Test valid workstream status values."""
    from amplihack.memory.beads_models import BeadsWorkstream

    valid_statuses = ["active", "paused", "completed", "archived"]

    for status in valid_statuses:
        ws = BeadsWorkstream(
            id=f"WS-{status}",
            name="Test",
            description="Test",
            status=status,
            created_at="2025-10-18T10:00:00Z"
        )
        assert ws.status == status


def test_beads_workstream_to_dict(sample_workstream_data):
    """Test converting BeadsWorkstream to dictionary."""
    from amplihack.memory.beads_models import BeadsWorkstream

    ws = BeadsWorkstream(**sample_workstream_data)
    ws_dict = ws.to_dict()

    assert ws_dict["id"] == "WS-001"
    assert ws_dict["name"] == "Authentication Feature"
    assert len(ws_dict["issues"]) == 3


# =============================================================================
# Model Conversion Tests
# =============================================================================

def test_convert_cli_output_to_issue(sample_issue_data):
    """Test converting beads CLI JSON output to BeadsIssue."""
    from amplihack.memory.beads_models import BeadsIssue

    issue = BeadsIssue.from_cli_output(sample_issue_data)

    assert issue.id == "ISSUE-001"
    assert issue.title == "Implement authentication"


def test_convert_issue_to_cli_input():
    """Test converting BeadsIssue to CLI input format."""
    from amplihack.memory.beads_models import BeadsIssue

    issue = BeadsIssue(
        id="ISSUE-001",
        title="Test Issue",
        description="Test description",
        status="open",
        labels=["feature"],
        created_at="2025-10-18T10:00:00Z",
        updated_at="2025-10-18T10:00:00Z"
    )

    cli_input = issue.to_cli_input()

    assert cli_input["title"] == "Test Issue"
    assert cli_input["description"] == "Test description"
    assert cli_input["labels"] == ["feature"]
    # Should not include read-only fields like id, created_at
    assert "id" not in cli_input
    assert "created_at" not in cli_input


def test_issue_equality():
    """Test BeadsIssue equality comparison."""
    from amplihack.memory.beads_models import BeadsIssue

    issue1 = BeadsIssue(
        id="ISSUE-001",
        title="Test",
        description="Test",
        status="open",
        created_at="2025-10-18T10:00:00Z",
        updated_at="2025-10-18T10:00:00Z"
    )

    issue2 = BeadsIssue(
        id="ISSUE-001",
        title="Test",
        description="Test",
        status="open",
        created_at="2025-10-18T10:00:00Z",
        updated_at="2025-10-18T10:00:00Z"
    )

    issue3 = BeadsIssue(
        id="ISSUE-002",
        title="Different",
        description="Different",
        status="open",
        created_at="2025-10-18T10:00:00Z",
        updated_at="2025-10-18T10:00:00Z"
    )

    assert issue1 == issue2
    assert issue1 != issue3


def test_issue_hash():
    """Test BeadsIssue hashing for set/dict usage."""
    from amplihack.memory.beads_models import BeadsIssue

    issue1 = BeadsIssue(
        id="ISSUE-001",
        title="Test",
        description="Test",
        status="open",
        created_at="2025-10-18T10:00:00Z",
        updated_at="2025-10-18T10:00:00Z"
    )

    issue2 = BeadsIssue(
        id="ISSUE-001",
        title="Test",
        description="Test",
        status="open",
        created_at="2025-10-18T10:00:00Z",
        updated_at="2025-10-18T10:00:00Z"
    )

    # Should be hashable and equal issues have same hash
    issue_set = {issue1, issue2}
    assert len(issue_set) == 1  # Same ID, so only one in set


# =============================================================================
# Validation Edge Cases Tests
# =============================================================================

def test_issue_with_very_long_title():
    """Test issue creation with very long title."""
    from amplihack.memory.beads_models import BeadsIssue

    long_title = "A" * 1000

    with pytest.raises(ValueError, match="title.*too long"):
        BeadsIssue(
            id="ISSUE-001",
            title=long_title,
            description="Test",
            status="open",
            created_at="2025-10-18T10:00:00Z",
            updated_at="2025-10-18T10:00:00Z"
        )


def test_issue_with_very_long_description():
    """Test issue creation with very long description (should succeed)."""
    from amplihack.memory.beads_models import BeadsIssue

    long_description = "A" * 10000

    issue = BeadsIssue(
        id="ISSUE-001",
        title="Test",
        description=long_description,
        status="open",
        created_at="2025-10-18T10:00:00Z",
        updated_at="2025-10-18T10:00:00Z"
    )

    assert len(issue.description) == 10000


def test_issue_with_special_characters():
    """Test issue creation with special characters in fields."""
    from amplihack.memory.beads_models import BeadsIssue

    issue = BeadsIssue(
        id="ISSUE-001",
        title="Test with émojis 🚀 and spëcial çhars",
        description="Description with\nnewlines\tand\ttabs",
        status="open",
        created_at="2025-10-18T10:00:00Z",
        updated_at="2025-10-18T10:00:00Z"
    )

    assert "🚀" in issue.title
    assert "\n" in issue.description


@pytest.mark.parametrize("invalid_id", [
    "",
    " ",
    "ISSUE 001",  # No spaces allowed
    "ISSUE-001!",  # No special chars
])
def test_issue_id_format_validation(invalid_id):
    """Test that issue ID format is validated."""
    from amplihack.memory.beads_models import BeadsIssue

    with pytest.raises(ValueError, match="id.*format"):
        BeadsIssue(
            id=invalid_id,
            title="Test",
            description="Test",
            status="open",
            created_at="2025-10-18T10:00:00Z",
            updated_at="2025-10-18T10:00:00Z"
        )


def test_relationship_with_metadata():
    """Test relationship with complex metadata."""
    from amplihack.memory.beads_models import BeadsRelationship

    rel = BeadsRelationship(
        type="blocks",
        source_id="ISSUE-001",
        target_id="ISSUE-002",
        created_at="2025-10-18T10:00:00Z",
        metadata={
            "reason": "Dependency on API design",
            "priority": "high",
            "notes": ["Note 1", "Note 2"],
            "nested": {"key": "value"}
        }
    )

    assert rel.metadata["notes"] == ["Note 1", "Note 2"]
    assert rel.metadata["nested"]["key"] == "value"
