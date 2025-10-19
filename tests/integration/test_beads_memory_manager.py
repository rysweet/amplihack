"""
Integration tests for beads memory manager integration.

Tests BeadsMemoryProvider registration, provider selection logic,
memory operations through manager interface, and fallback behavior.

Following TDD approach - all tests should FAIL initially until implementation exists.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_beads_provider():
    """Mock BeadsMemoryProvider."""
    provider = Mock()
    provider.provider_type.return_value = "beads"
    provider.is_available.return_value = True
    provider.create_issue.return_value = "ISSUE-001"
    provider.get_issue.return_value = {"id": "ISSUE-001", "title": "Test"}
    return provider


@pytest.fixture
def memory_manager():
    """Create MemoryManager instance."""
    from amplihack.memory.manager import MemoryManager
    return MemoryManager()


# =============================================================================
# Provider Registration Tests
# =============================================================================

def test_register_beads_provider(memory_manager, mock_beads_provider):
    """Test registering BeadsMemoryProvider with memory manager."""
    memory_manager.register_provider("beads", mock_beads_provider)

    providers = memory_manager.get_providers()
    assert "beads" in providers
    assert providers["beads"] == mock_beads_provider


def test_register_multiple_providers(memory_manager, mock_beads_provider):
    """Test registering multiple memory providers."""
    mock_github_provider = Mock()
    mock_github_provider.provider_type.return_value = "github"

    memory_manager.register_provider("beads", mock_beads_provider)
    memory_manager.register_provider("github", mock_github_provider)

    providers = memory_manager.get_providers()
    assert len(providers) == 2
    assert "beads" in providers
    assert "github" in providers


def test_auto_register_beads_if_available(memory_manager):
    """Test automatic registration of beads provider if available."""
    with patch('amplihack.memory.beads_adapter.BeadsAdapter') as mock_adapter:
        mock_adapter.return_value.is_available.return_value = True

        memory_manager.auto_register_providers()

        providers = memory_manager.get_providers()
        assert "beads" in providers


def test_skip_auto_register_beads_if_unavailable(memory_manager):
    """Test that beads is not registered if unavailable."""
    with patch('amplihack.memory.beads_adapter.BeadsAdapter') as mock_adapter:
        mock_adapter.return_value.is_available.return_value = False

        memory_manager.auto_register_providers()

        providers = memory_manager.get_providers()
        assert "beads" not in providers


# =============================================================================
# Provider Selection Tests
# =============================================================================

def test_select_beads_provider_by_name(memory_manager, mock_beads_provider):
    """Test selecting beads provider by explicit name."""
    memory_manager.register_provider("beads", mock_beads_provider)

    provider = memory_manager.get_provider("beads")

    assert provider == mock_beads_provider


def test_select_default_provider_priority(memory_manager, mock_beads_provider):
    """Test that beads is selected as default if available."""
    mock_github_provider = Mock()
    mock_github_provider.provider_type.return_value = "github"

    memory_manager.register_provider("github", mock_github_provider)
    memory_manager.register_provider("beads", mock_beads_provider)

    # Beads should be preferred default
    provider = memory_manager.get_default_provider()

    assert provider == mock_beads_provider


def test_fallback_to_alternative_provider(memory_manager, mock_beads_provider):
    """Test fallback to alternative when primary unavailable."""
    mock_beads_provider.is_available.return_value = False

    mock_github_provider = Mock()
    mock_github_provider.is_available.return_value = True

    memory_manager.register_provider("beads", mock_beads_provider)
    memory_manager.register_provider("github", mock_github_provider)

    provider = memory_manager.get_default_provider()

    assert provider == mock_github_provider


def test_no_provider_available_returns_none(memory_manager):
    """Test that None is returned when no providers are available."""
    provider = memory_manager.get_provider("nonexistent")

    assert provider is None


# =============================================================================
# Memory Operations Through Manager Tests
# =============================================================================

def test_create_issue_through_manager(memory_manager, mock_beads_provider):
    """Test creating issue through memory manager interface."""
    memory_manager.register_provider("beads", mock_beads_provider)

    issue_id = memory_manager.create_issue(
        title="Test Issue",
        description="Test description",
        provider="beads"
    )

    assert issue_id == "ISSUE-001"
    mock_beads_provider.create_issue.assert_called_once()


def test_create_issue_uses_default_provider(memory_manager, mock_beads_provider):
    """Test that create_issue uses default provider when not specified."""
    memory_manager.register_provider("beads", mock_beads_provider)

    issue_id = memory_manager.create_issue(
        title="Test Issue",
        description="Test description"
    )

    assert issue_id == "ISSUE-001"


def test_get_issue_through_manager(memory_manager, mock_beads_provider):
    """Test retrieving issue through memory manager."""
    memory_manager.register_provider("beads", mock_beads_provider)

    issue = memory_manager.get_issue("ISSUE-001", provider="beads")

    assert issue["id"] == "ISSUE-001"
    mock_beads_provider.get_issue.assert_called_once_with("ISSUE-001")


def test_update_issue_through_manager(memory_manager, mock_beads_provider):
    """Test updating issue through memory manager."""
    mock_beads_provider.update_issue.return_value = True
    memory_manager.register_provider("beads", mock_beads_provider)

    result = memory_manager.update_issue(
        "ISSUE-001",
        status="in_progress",
        provider="beads"
    )

    assert result is True
    mock_beads_provider.update_issue.assert_called_once()


def test_add_relationship_through_manager(memory_manager, mock_beads_provider):
    """Test adding relationship through memory manager."""
    mock_beads_provider.add_relationship.return_value = True
    memory_manager.register_provider("beads", mock_beads_provider)

    result = memory_manager.add_relationship(
        "ISSUE-001",
        "ISSUE-002",
        relationship_type="blocks",
        provider="beads"
    )

    assert result is True
    mock_beads_provider.add_relationship.assert_called_once()


def test_get_ready_work_through_manager(memory_manager, mock_beads_provider):
    """Test querying ready work through memory manager."""
    mock_beads_provider.get_ready_work.return_value = [
        {"id": "ISSUE-001", "status": "open"}
    ]
    memory_manager.register_provider("beads", mock_beads_provider)

    ready_work = memory_manager.get_ready_work(provider="beads")

    assert len(ready_work) == 1
    assert ready_work[0]["id"] == "ISSUE-001"


# =============================================================================
# Cross-Provider Operations Tests
# =============================================================================

def test_sync_issue_across_providers(memory_manager, mock_beads_provider):
    """Test syncing issue between beads and GitHub."""
    mock_github_provider = Mock()
    mock_github_provider.create_issue.return_value = "123"

    memory_manager.register_provider("beads", mock_beads_provider)
    memory_manager.register_provider("github", mock_github_provider)

    # Create issue in beads, sync to GitHub
    result = memory_manager.sync_issue(
        "ISSUE-001",
        source_provider="beads",
        target_provider="github"
    )

    assert result["github_issue_id"] == "123"
    mock_beads_provider.get_issue.assert_called_once()
    mock_github_provider.create_issue.assert_called_once()


def test_link_issues_across_providers(memory_manager, mock_beads_provider):
    """Test linking beads issue with GitHub issue."""
    memory_manager.register_provider("beads", mock_beads_provider)

    result = memory_manager.link_issues(
        beads_issue_id="ISSUE-001",
        github_issue_id="123",
        repo="test/repo"
    )

    assert result is True
    # Should update beads issue with GitHub link
    mock_beads_provider.update_issue.assert_called()


# =============================================================================
# Fallback Behavior Tests
# =============================================================================

def test_fallback_when_beads_operation_fails(memory_manager, mock_beads_provider):
    """Test fallback to alternative provider when beads fails."""
    mock_beads_provider.create_issue.side_effect = RuntimeError("Beads error")

    mock_github_provider = Mock()
    mock_github_provider.create_issue.return_value = "123"

    memory_manager.register_provider("beads", mock_beads_provider)
    memory_manager.register_provider("github", mock_github_provider)
    memory_manager.set_fallback_enabled(True)

    issue_id = memory_manager.create_issue(
        title="Test",
        description="Test",
        with_fallback=True
    )

    # Should fall back to GitHub
    assert issue_id == "123"
    mock_github_provider.create_issue.assert_called_once()


def test_no_fallback_when_disabled(memory_manager, mock_beads_provider):
    """Test that fallback doesn't occur when disabled."""
    mock_beads_provider.create_issue.side_effect = RuntimeError("Beads error")
    memory_manager.register_provider("beads", mock_beads_provider)
    memory_manager.set_fallback_enabled(False)

    with pytest.raises(RuntimeError, match="Beads error"):
        memory_manager.create_issue(
            title="Test",
            description="Test",
            provider="beads"
        )


def test_operation_succeeds_without_provider(memory_manager):
    """Test that operations gracefully handle no provider available."""
    result = memory_manager.create_issue(
        title="Test",
        description="Test",
        required=False
    )

    # Should return None but not raise error
    assert result is None


# =============================================================================
# Provider Status and Health Tests
# =============================================================================

def test_check_provider_health(memory_manager, mock_beads_provider):
    """Test checking provider health status."""
    mock_beads_provider.health_check.return_value = {
        "status": "healthy",
        "latency_ms": 50
    }
    memory_manager.register_provider("beads", mock_beads_provider)

    health = memory_manager.check_provider_health("beads")

    assert health["status"] == "healthy"
    assert health["latency_ms"] < 100


def test_get_all_providers_status(memory_manager, mock_beads_provider):
    """Test getting status of all registered providers."""
    memory_manager.register_provider("beads", mock_beads_provider)

    status = memory_manager.get_providers_status()

    assert "beads" in status
    assert status["beads"]["available"] is True


def test_provider_priority_ordering(memory_manager):
    """Test that providers are selected in priority order."""
    providers_config = [
        {"name": "beads", "priority": 1},
        {"name": "github", "priority": 2},
        {"name": "local", "priority": 3}
    ]

    memory_manager.set_provider_priorities(providers_config)

    # Beads should be tried first
    priority_order = memory_manager.get_provider_priority_order()

    assert priority_order[0] == "beads"
    assert priority_order[1] == "github"


# =============================================================================
# Configuration Tests
# =============================================================================

def test_configure_provider_settings(memory_manager, mock_beads_provider):
    """Test configuring provider-specific settings."""
    settings = {
        "auto_sync": True,
        "debounce_delay": 10,
        "retry_attempts": 3
    }

    memory_manager.register_provider("beads", mock_beads_provider)
    memory_manager.configure_provider("beads", settings)

    config = memory_manager.get_provider_config("beads")

    assert config["auto_sync"] is True
    assert config["debounce_delay"] == 10


def test_enable_disable_provider(memory_manager, mock_beads_provider):
    """Test enabling/disabling provider."""
    memory_manager.register_provider("beads", mock_beads_provider)

    memory_manager.disable_provider("beads")
    provider = memory_manager.get_provider("beads")
    assert provider is None

    memory_manager.enable_provider("beads")
    provider = memory_manager.get_provider("beads")
    assert provider == mock_beads_provider


# =============================================================================
# Error Handling Tests
# =============================================================================

def test_handle_provider_not_found_error(memory_manager):
    """Test handling of provider not found error."""
    with pytest.raises(ValueError, match="Provider.*not found"):
        memory_manager.create_issue(
            title="Test",
            description="Test",
            provider="nonexistent",
            required=True
        )


def test_handle_provider_unavailable_error(memory_manager, mock_beads_provider):
    """Test handling of provider unavailable error."""
    mock_beads_provider.is_available.return_value = False
    memory_manager.register_provider("beads", mock_beads_provider)

    with pytest.raises(RuntimeError, match="Provider.*unavailable"):
        memory_manager.create_issue(
            title="Test",
            description="Test",
            provider="beads",
            required=True
        )
