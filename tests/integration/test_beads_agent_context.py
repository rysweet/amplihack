"""
Integration tests for beads agent context restoration.

Tests agent startup queries beads for workstream state, context restoration
from issue history, dependency chain retrieval, and discovery tracking.

Following TDD approach - all tests should FAIL initially until implementation exists.
"""

import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def mock_beads_provider():
    """Mock BeadsMemoryProvider."""
    provider = Mock()
    provider.is_available.return_value = True
    provider.get_issue.return_value = {
        "id": "ISSUE-001",
        "title": "Implement authentication",
        "status": "in_progress",
        "metadata": {"context": "JWT auth", "dependencies": ["ISSUE-002"]}
    }
    provider.get_relationships.return_value = [
        {"type": "blocks", "target_id": "ISSUE-002"},
        {"type": "discovered-from", "target_id": "ISSUE-000"}
    ]
    return provider


@pytest.fixture
def agent_context_manager():
    """Create AgentContextManager."""
    from amplihack.agents.context_manager import AgentContextManager
    return AgentContextManager()


def test_agent_startup_queries_beads_for_context(agent_context_manager, mock_beads_provider):
    """Test that agent queries beads on startup for context."""
    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        context = agent_context_manager.restore_context("architect-agent")

        assert context is not None
        mock_beads_provider.get_ready_work.assert_called()


def test_restore_context_from_issue_history(agent_context_manager, mock_beads_provider):
    """Test restoring agent context from issue history."""
    mock_beads_provider.get_issue.return_value = {
        "id": "ISSUE-001",
        "title": "Implement auth",
        "description": "Add JWT authentication",
        "metadata": {
            "progress": "Design complete, implementation in progress",
            "decisions": ["Use JWT", "HS256 algorithm"],
            "blockers": []
        }
    }

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        context = agent_context_manager.restore_context_from_issue("ISSUE-001")

        assert context["current_task"] == "Implement auth"
        assert "JWT" in context["decisions"]


def test_retrieve_dependency_chain(agent_context_manager, mock_beads_provider):
    """Test retrieving full dependency chain for issue."""
    mock_beads_provider.get_relationships.side_effect = [
        [{"type": "blocks", "target_id": "ISSUE-002"}],
        [{"type": "blocks", "target_id": "ISSUE-003"}],
        []
    ]

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        chain = agent_context_manager.get_dependency_chain("ISSUE-001")

        assert len(chain) >= 2
        assert "ISSUE-002" in chain
        assert "ISSUE-003" in chain


def test_track_discovery_relationships(agent_context_manager, mock_beads_provider):
    """Test tracking 'discovered-from' relationships."""
    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        agent_context_manager.track_discovery("ISSUE-001", "ISSUE-005", reason="Found during implementation")

        mock_beads_provider.add_relationship.assert_called_with(
            "ISSUE-005", "ISSUE-001", "discovered-from"
        )


def test_get_agent_workstream_state(agent_context_manager, mock_beads_provider):
    """Test getting agent's current workstream state."""
    mock_beads_provider.query_issues.return_value = [
        {"id": "ISSUE-001", "status": "in_progress", "assignee": "architect-agent"},
        {"id": "ISSUE-002", "status": "blocked", "assignee": "architect-agent"}
    ]

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        workstream = agent_context_manager.get_workstream_state("architect-agent")

        assert len(workstream["active_issues"]) == 1
        assert len(workstream["blocked_issues"]) == 1


def test_context_includes_related_issues(agent_context_manager, mock_beads_provider):
    """Test that restored context includes related issues."""
    mock_beads_provider.get_relationships.return_value = [
        {"type": "related", "target_id": "ISSUE-010"},
        {"type": "related", "target_id": "ISSUE-011"}
    ]

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        context = agent_context_manager.restore_context_from_issue("ISSUE-001")

        assert "related_issues" in context
        assert len(context["related_issues"]) == 2


def test_agent_context_cache(agent_context_manager, mock_beads_provider):
    """Test that agent context is cached to avoid repeated queries."""
    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        # Call twice
        context1 = agent_context_manager.restore_context("builder-agent")
        context2 = agent_context_manager.restore_context("builder-agent")

        # Should only query once
        assert mock_beads_provider.get_ready_work.call_count == 1


def test_invalidate_context_cache(agent_context_manager, mock_beads_provider):
    """Test invalidating context cache on updates."""
    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        agent_context_manager.restore_context("builder-agent")
        agent_context_manager.invalidate_cache("builder-agent")
        agent_context_manager.restore_context("builder-agent")

        # Should query twice after cache invalidation
        assert mock_beads_provider.get_ready_work.call_count == 2
