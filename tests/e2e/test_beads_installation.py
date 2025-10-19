"""
E2E tests for beads installation and setup.

Tests beads detection, initialization, version compatibility,
and installation guidance when missing.

Following TDD approach - all tests should FAIL initially until implementation exists.
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch


@pytest.mark.e2e
def test_detect_beads_in_path():
    """Test detecting beads CLI in system PATH."""
    from amplihack.memory.beads_adapter import BeadsAdapter

    adapter = BeadsAdapter()

    # This will actually check the system
    is_available = adapter.is_available()

    # Test should document expected behavior
    assert isinstance(is_available, bool)


@pytest.mark.e2e
def test_beads_initialization_check():
    """Test checking if beads is initialized in current repo."""
    from amplihack.memory.beads_adapter import BeadsAdapter

    adapter = BeadsAdapter()

    if not adapter.is_available():
        pytest.skip("Beads CLI not available")

    # Check if initialized
    is_initialized = adapter.check_init()

    assert isinstance(is_initialized, bool)


@pytest.mark.e2e
def test_initialize_beads_in_repo(tmp_path):
    """Test initializing beads in a new repository."""
    from amplihack.memory.beads_adapter import BeadsAdapter

    adapter = BeadsAdapter()

    if not adapter.is_available():
        pytest.skip("Beads CLI not available")

    # Create test repo
    test_repo = tmp_path / "test-repo"
    test_repo.mkdir()
    (test_repo / ".git").mkdir()

    # Initialize beads
    result = adapter.initialize_repo(str(test_repo))

    assert result is True
    assert (test_repo / ".beads").exists()


@pytest.mark.e2e
def test_get_beads_version():
    """Test getting beads CLI version."""
    from amplihack.memory.beads_adapter import BeadsAdapter

    adapter = BeadsAdapter()

    if not adapter.is_available():
        pytest.skip("Beads CLI not available")

    version = adapter.get_version()

    assert version is not None
    assert isinstance(version, str)
    # Version should match semver pattern
    assert len(version.split('.')) >= 2


@pytest.mark.e2e
def test_check_version_compatibility():
    """Test checking version compatibility."""
    from amplihack.memory.beads_adapter import BeadsAdapter

    adapter = BeadsAdapter()

    if not adapter.is_available():
        pytest.skip("Beads CLI not available")

    # Test with minimum supported version
    is_compatible = adapter.check_version_compatibility(min_version="0.1.0")

    assert isinstance(is_compatible, bool)


@pytest.mark.e2e
def test_installation_guidance_when_missing():
    """Test that helpful guidance is provided when beads is not installed."""
    from amplihack.memory.beads_installer import BeadsInstaller

    installer = BeadsInstaller()

    # Get installation instructions
    instructions = installer.get_installation_instructions()

    assert instructions is not None
    assert "install" in instructions.lower()
    assert "bd" in instructions  # Command name


@pytest.mark.e2e
def test_auto_install_beads():
    """Test automatic beads installation (if supported)."""
    from amplihack.memory.beads_installer import BeadsInstaller

    installer = BeadsInstaller()

    if not installer.can_auto_install():
        pytest.skip("Auto-install not supported on this platform")

    # This should be opt-in only
    assert installer.requires_confirmation() is True


@pytest.mark.e2e
def test_verify_beads_setup():
    """Test complete beads setup verification."""
    from amplihack.memory.beads_setup import verify_beads_setup

    status = verify_beads_setup()

    assert "beads_available" in status
    assert "beads_initialized" in status
    assert "version" in status

    if status["beads_available"]:
        assert status["version"] is not None


@pytest.mark.e2e
def test_beads_health_check():
    """Test beads health check functionality."""
    from amplihack.memory.beads_adapter import BeadsAdapter

    adapter = BeadsAdapter()

    if not adapter.is_available():
        pytest.skip("Beads CLI not available")

    health = adapter.health_check()

    assert "status" in health
    assert health["status"] in ["healthy", "degraded", "unavailable"]

    if health["status"] == "healthy":
        assert "latency_ms" in health
        assert health["latency_ms"] < 1000  # Should be fast


@pytest.mark.e2e
def test_beads_cli_basic_operations():
    """Test basic beads CLI operations work correctly."""
    from amplihack.memory.beads_adapter import BeadsAdapter

    adapter = BeadsAdapter()

    if not adapter.is_available():
        pytest.skip("Beads CLI not available")

    # Test creating and retrieving issue
    issue_id = adapter.create_issue(
        title="Test CLI operation",
        description="Verify CLI works"
    )

    assert issue_id is not None

    # Retrieve the issue
    issue = adapter.get_issue(issue_id)

    assert issue is not None
    assert issue["id"] == issue_id
    assert issue["title"] == "Test CLI operation"


@pytest.mark.e2e
def test_beads_with_git_integration():
    """Test beads integration with git repository."""
    from amplihack.memory.beads_adapter import BeadsAdapter
    from amplihack.memory.beads_sync import BeadsSync

    adapter = BeadsAdapter()

    if not adapter.is_available():
        pytest.skip("Beads CLI not available")

    sync = BeadsSync()

    # Check git status
    is_git_clean = sync.is_git_clean()

    assert isinstance(is_git_clean, bool)


@pytest.mark.e2e
def test_error_handling_without_beads():
    """Test that system handles missing beads gracefully."""
    from amplihack.memory.beads_provider import BeadsMemoryProvider
    from amplihack.memory.beads_adapter import BeadsAdapter

    # Mock unavailable beads
    adapter = BeadsAdapter()

    with patch.object(adapter, 'is_available', return_value=False):
        provider = BeadsMemoryProvider(adapter=adapter)

        # Should not crash
        assert provider.is_available() is False

        # Operations should fail gracefully
        with pytest.raises(RuntimeError, match="beads.*not available"):
            provider.create_issue(title="Test", description="Test")


@pytest.mark.e2e
def test_migration_from_existing_system():
    """Test migrating from existing issue tracking to beads."""
    from amplihack.memory.beads_migrator import BeadsMigrator

    migrator = BeadsMigrator()

    # Mock existing issues
    existing_issues = [
        {"id": "GH-001", "title": "Test 1", "status": "open"},
        {"id": "GH-002", "title": "Test 2", "status": "closed"}
    ]

    # Generate migration plan
    plan = migrator.generate_migration_plan(existing_issues)

    assert plan is not None
    assert len(plan["issues_to_migrate"]) == 2


@pytest.mark.e2e
def test_beads_backup_and_restore():
    """Test beads data backup and restore functionality."""
    from amplihack.memory.beads_backup import BeadsBackup

    backup = BeadsBackup()

    if not backup.is_available():
        pytest.skip("Beads backup not available")

    # Create backup
    backup_path = backup.create_backup()

    assert backup_path is not None
    assert Path(backup_path).exists()

    # Verify backup contents
    assert backup.verify_backup(backup_path) is True
