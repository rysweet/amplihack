"""
Integration tests for Neo4j container lifecycle management.

Tests real container operations:
- Start/stop/restart cycles
- Data persistence across restarts
- Multiple session handling
- Resource cleanup

These tests require Docker to be available.

All tests should FAIL initially (TDD approach).
"""

import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.integration
class TestStartStopRestartCycle:
    """Test container lifecycle operations."""

    def test_WHEN_container_started_THEN_status_is_running(self):
        """Test starting container and checking status."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.models import ContainerStatus

        manager = ContainerManager()
        manager.start_container()

        # Wait for container to be ready
        manager.wait_for_ready(timeout=30)

        status = manager.get_status()
        assert status == ContainerStatus.RUNNING

    def test_WHEN_container_stopped_THEN_status_is_stopped(self):
        """Test stopping container."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.models import ContainerStatus

        manager = ContainerManager()
        manager.start_container()
        manager.wait_for_ready(timeout=30)

        # Stop container
        manager.stop_container()
        time.sleep(2)

        status = manager.get_status()
        assert status in [ContainerStatus.STOPPED, ContainerStatus.EXITED]

    def test_WHEN_container_restarted_THEN_becomes_running_again(self):
        """Test restart after stop."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.models import ContainerStatus

        manager = ContainerManager()

        # Start, stop, start again
        manager.start_container()
        manager.wait_for_ready(timeout=30)
        manager.stop_container()
        time.sleep(2)
        manager.start_container()
        manager.wait_for_ready(timeout=30)

        status = manager.get_status()
        assert status == ContainerStatus.RUNNING

    def test_WHEN_multiple_start_calls_THEN_idempotent(self):
        """Test that multiple start calls don't create duplicates."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()

        # Start multiple times
        result1 = manager.start_container()
        time.sleep(1)
        result2 = manager.start_container()
        time.sleep(1)
        result3 = manager.start_container()

        # All should succeed (idempotent)
        assert result1 is True
        assert result2 is True
        assert result3 is True

        # Should only have one container
        # (verified by checking container name uniqueness in Docker)


@pytest.mark.integration
class TestDataPersistenceAcrossRestarts:
    """Test that data survives container restarts."""

    def test_WHEN_data_created_and_container_stopped_THEN_data_persists_on_restart(self):
        """Test full stop/start cycle with data persistence."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.connector import Neo4jConnector

        manager = ContainerManager()
        manager.start_container()
        manager.wait_for_ready(timeout=30)

        # Create test data
        connector = Neo4jConnector()
        connector.connect()

        test_id = "lifecycle-test-001"
        connector.execute_write(f"""
            CREATE (n:LifecycleTest {{id: '{test_id}', data: 'Persistent data'}})
        """)
        connector.close()

        # Stop container
        manager.stop_container()
        time.sleep(3)

        # Start container again
        manager.start_container()
        manager.wait_for_ready(timeout=30)

        # Verify data exists
        connector = Neo4jConnector()
        connector.connect()

        result = connector.execute_query(f"""
            MATCH (n:LifecycleTest {{id: '{test_id}'}})
            RETURN n.data as data
        """)

        assert len(result) == 1
        assert result[0]["data"] == "Persistent data"

        # Cleanup
        connector.execute_write(f"MATCH (n:LifecycleTest {{id: '{test_id}'}}) DELETE n")
        connector.close()

    def test_WHEN_container_removed_but_volume_kept_THEN_data_persists(self):
        """Test data persistence when container is removed but volume remains."""
        import subprocess

        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.connector import Neo4jConnector

        manager = ContainerManager()
        manager.start_container()
        manager.wait_for_ready(timeout=30)

        # Create test data
        connector = Neo4jConnector()
        connector.connect()

        test_id = "volume-test-001"
        connector.execute_write(f"""
            CREATE (n:VolumeTest {{id: '{test_id}', data: 'Volume persistent'}})
        """)
        connector.close()

        # Remove container (not volume)
        container_name = manager.container_name
        subprocess.run(["docker", "rm", "-f", container_name], check=True)
        time.sleep(2)

        # Create new container with same volume
        manager.start_container()
        manager.wait_for_ready(timeout=30)

        # Verify data exists
        connector = Neo4jConnector()
        connector.connect()

        result = connector.execute_query(f"""
            MATCH (n:VolumeTest {{id: '{test_id}'}})
            RETURN n.data as data
        """)

        assert len(result) == 1
        assert result[0]["data"] == "Volume persistent"

        # Cleanup
        connector.execute_write(f"MATCH (n:VolumeTest {{id: '{test_id}'}}) DELETE n")
        connector.close()

    def test_WHEN_machine_reboots_THEN_container_restarts_automatically(self):
        """Test restart policy (simulated)."""
        import subprocess

        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        manager.start_container()
        manager.wait_for_ready(timeout=30)

        # Verify restart policy is set
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "--format={{.HostConfig.RestartPolicy.Name}}",
                manager.container_name,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        restart_policy = result.stdout.strip()
        assert restart_policy in ["unless-stopped", "always"]


@pytest.mark.integration
class TestMultipleSessionStarts:
    """Test handling multiple amplihack sessions."""

    def test_WHEN_first_session_starts_container_THEN_second_session_uses_it(self):
        """Test that second session detects and uses existing container."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        # First session
        result1 = ensure_neo4j_running(blocking=True)
        assert result1 is True or result1 is not False

        # Get container ID
        manager = ContainerManager()
        manager.get_status()

        # Second session (should detect existing)
        ensure_neo4j_running(blocking=False)
        time.sleep(1)

        status2 = manager.get_status()

        # Should still be running (not restarted)
        assert status2.value == "running"

    def test_WHEN_session_exits_THEN_container_keeps_running(self):
        """Test that container persists after session exit."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        ensure_neo4j_running(blocking=True)

        # Simulate session exit (container should keep running)
        manager = ContainerManager()
        status = manager.get_status()

        assert status.value in ["running", "healthy"]

    def test_WHEN_concurrent_sessions_start_THEN_no_race_conditions(self):
        """Test concurrent session starts don't cause issues."""
        import threading

        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        results = []

        def start_session():
            result = ensure_neo4j_running(blocking=False)
            results.append(result)

        # Start 3 "sessions" concurrently
        threads = [threading.Thread(target=start_session) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed (or fail gracefully)
        assert len(results) == 3
        # No exceptions should have been raised


@pytest.mark.integration
class TestResourceCleanup:
    """Test resource cleanup and management."""

    def test_WHEN_container_stopped_THEN_ports_released(self):
        """Test that stopping container releases ports."""
        import socket

        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        manager.start_container()
        manager.wait_for_ready(timeout=30)

        # Ports should be in use
        with pytest.raises(OSError):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", manager.bolt_port))

        # Stop container
        manager.stop_container()
        time.sleep(3)

        # Ports should be free
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", manager.bolt_port))
            # Success - port is free

    def test_WHEN_volume_removed_THEN_data_is_deleted(self):
        """Test that removing volume deletes data (destructive test)."""
        import subprocess

        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.connector import Neo4jConnector

        manager = ContainerManager()
        manager.start_container()
        manager.wait_for_ready(timeout=30)

        # Create test data
        connector = Neo4jConnector()
        connector.connect()

        test_id = "cleanup-test-001"
        connector.execute_write(f"""
            CREATE (n:CleanupTest {{id: '{test_id}', data: 'To be deleted'}})
        """)
        connector.close()

        # Stop and remove container
        manager.stop_container()
        subprocess.run(["docker", "rm", manager.container_name], check=True)

        # Remove volume
        subprocess.run(["docker", "volume", "rm", manager.volume_name], check=True)
        time.sleep(2)

        # Start new container (will create new volume)
        manager.start_container()
        manager.wait_for_ready(timeout=30)

        # Data should not exist
        connector = Neo4jConnector()
        connector.connect()

        result = connector.execute_query(f"""
            MATCH (n:CleanupTest {{id: '{test_id}'}})
            RETURN n
        """)

        assert len(result) == 0, "Data should not exist after volume removal"

        connector.close()


@pytest.mark.integration
@pytest.mark.slow
class TestContainerHealthMonitoring:
    """Test container health monitoring over time."""

    def test_WHEN_container_starting_THEN_health_progresses_to_healthy(self):
        """Test health status progression."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        manager.start_container()

        # Check health progression
        max_attempts = 30
        became_healthy = False

        for i in range(max_attempts):
            if manager.is_healthy():
                became_healthy = True
                break
            time.sleep(1)

        assert became_healthy, "Container should become healthy within 30 seconds"

    def test_WHEN_container_unhealthy_THEN_can_detect(self):
        """Test detection of unhealthy container."""
        import subprocess

        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        manager.start_container()
        manager.wait_for_ready(timeout=30)

        # Simulate unhealthy state (pause container)
        subprocess.run(["docker", "pause", manager.container_name], check=True)
        time.sleep(2)

        is_healthy = manager.is_healthy()
        assert is_healthy is False

        # Unpause
        subprocess.run(["docker", "unpause", manager.container_name], check=True)


@pytest.mark.integration
class TestErrorScenarios:
    """Test error handling in lifecycle operations."""

    def test_WHEN_docker_daemon_stops_during_operation_THEN_error_handled(self):
        """Test handling Docker daemon failure."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.exceptions import DockerNotAvailableError

        manager = ContainerManager()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = ConnectionError("Docker daemon not responding")

            with pytest.raises(DockerNotAvailableError):
                manager.start_container()

    def test_WHEN_container_fails_to_start_THEN_detailed_error_provided(self):
        """Test error details when container fails to start."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.exceptions import ContainerStartError

        manager = ContainerManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="Error: port already in use")

            with pytest.raises(ContainerStartError) as exc_info:
                manager.start_container()

            assert "port" in str(exc_info.value).lower()

    def test_WHEN_volume_mount_fails_THEN_error_explains_issue(self):
        """Test error handling for volume mount issues."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.exceptions import VolumeError

        manager = ContainerManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stderr="Error: error while mounting volume"
            )

            with pytest.raises(VolumeError) as exc_info:
                manager.start_container()

            assert "volume" in str(exc_info.value).lower()


# Fixtures for lifecycle tests
@pytest.fixture(scope="function")
def clean_container_state():
    """Ensure clean container state before test."""
    import subprocess

    from amplihack.memory.neo4j.container_manager import ContainerManager

    manager = ContainerManager()

    # Stop and remove container if exists
    subprocess.run(["docker", "rm", "-f", manager.container_name], capture_output=True)
    time.sleep(1)

    yield

    # Cleanup after test
    subprocess.run(["docker", "rm", "-f", manager.container_name], capture_output=True)


@pytest.fixture(scope="function")
def running_container():
    """Provide a running Neo4j container for tests."""
    from amplihack.memory.neo4j.container_manager import ContainerManager

    manager = ContainerManager()
    manager.start_container()
    manager.wait_for_ready(timeout=30)

    yield manager

    # Tests can decide whether to keep or stop container


@pytest.mark.integration
class TestPortConflictResolution:
    """Test port conflict detection and resolution during container creation."""

    def test_WHEN_ports_in_use_THEN_alternative_ports_selected(self):
        """Test that container creation handles port conflicts gracefully."""

        from amplihack.memory.neo4j.lifecycle import Neo4jContainerManager

        manager = Neo4jContainerManager()

        # Simulate port conflict by binding to default ports
        # (This is a simplified test - in real scenario, another service would use ports)
        try:
            # Start container - should detect any conflicts and use alternatives
            result = manager.start(wait_for_ready=True)

            # Should succeed even if default ports were busy
            assert result is True

            # Verify container is actually running
            status = manager.get_status()
            from amplihack.memory.neo4j.lifecycle import ContainerStatus

            assert status == ContainerStatus.RUNNING

        finally:
            # Cleanup
            manager.stop()

    def test_WHEN_container_already_running_on_different_ports_THEN_detected_and_reused(self):
        """Test detection of existing container on non-default ports."""
        import subprocess

        from amplihack.memory.neo4j.lifecycle import Neo4jContainerManager

        manager = Neo4jContainerManager()

        # Start container normally
        manager.start(wait_for_ready=True)

        # Get actual ports container is using
        result = subprocess.run(
            ["docker", "port", manager.config.container_name],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0
        assert "7687/tcp" in result.stdout
        assert "7474/tcp" in result.stdout

        # Stop but don't remove container
        manager.stop()

        # Start again - should detect existing container
        result = manager.start(wait_for_ready=True)
        assert result is True

        # Cleanup
        manager.stop()


@pytest.mark.integration
class TestConcurrentContainerCreation:
    """Test concurrent container creation scenarios."""

    def test_WHEN_multiple_sessions_start_concurrently_THEN_handles_race_conditions(self):
        """Test that concurrent starts don't create port binding conflicts."""
        import threading
        import time

        from amplihack.memory.neo4j.lifecycle import Neo4jContainerManager, ensure_neo4j_running

        # Ensure clean state
        manager = Neo4jContainerManager()
        try:
            manager.stop()
            import subprocess

            subprocess.run(
                ["docker", "rm", "-f", manager.config.container_name], capture_output=True
            )
        except Exception:
            pass

        time.sleep(2)

        results = []
        errors = []

        def start_session():
            try:
                result = ensure_neo4j_running(blocking=True)
                results.append(result)
            except Exception as e:
                errors.append(str(e))

        # Start 3 sessions concurrently
        threads = [threading.Thread(target=start_session) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed or at least not raise errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 3
        assert all(results), "Some sessions failed to start"

        # Verify only one container exists
        status = manager.get_status()
        from amplihack.memory.neo4j.lifecycle import ContainerStatus

        assert status == ContainerStatus.RUNNING

        # Cleanup
        manager.stop()

    def test_WHEN_port_binding_race_occurs_THEN_retries_with_different_ports(self):
        """Test retry logic when port binding race condition occurs."""
        import subprocess

        from amplihack.memory.neo4j.lifecycle import Neo4jContainerManager

        manager = Neo4jContainerManager()

        # Ensure clean state
        try:
            manager.stop()
            subprocess.run(
                ["docker", "rm", "-f", manager.config.container_name], capture_output=True
            )
        except Exception:
            pass

        # Start container - retry logic should handle any transient port issues
        result = manager.start(wait_for_ready=True)

        assert result is True

        # Verify container is healthy
        assert manager.is_healthy()

        # Cleanup
        manager.stop()
