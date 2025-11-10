"""
Unit tests for Neo4j container lifecycle management.

Tests the ContainerManager class responsible for:
- Starting/stopping Neo4j containers
- Health checks
- Status monitoring
- Container existence detection

All tests should FAIL initially (TDD approach).
"""

from unittest.mock import Mock, patch

import pytest


class TestContainerManagerStartup:
    """Test container startup functionality."""

    def test_WHEN_start_container_called_THEN_docker_compose_up_executed(self):
        """Test that start_container executes docker-compose up command."""
        # This will fail until ContainerManager is implemented
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Container started")

            result = manager.start_container()

            assert result is True
            mock_run.assert_called_once()
            # Verify docker-compose command was called
            call_args = mock_run.call_args[0][0]
            assert "docker" in call_args
            assert "compose" in call_args or "docker-compose" in call_args[0]

    def test_WHEN_container_already_running_THEN_start_is_idempotent(self):
        """Test that starting an already-running container is idempotent."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        with patch("subprocess.run") as mock_run:
            # First call: container already running
            mock_run.return_value = Mock(returncode=0, stdout="amplihack-neo4j", stderr="")

            result = manager.start_container()

            assert result is True
            # Should detect existing container and not create duplicate

    def test_WHEN_docker_not_available_THEN_appropriate_error_raised(self):
        """Test error handling when Docker daemon is not available."""
        from amplihack.memory.neo4j.container_manager import ContainerManager
        from amplihack.memory.neo4j.exceptions import DockerNotAvailableError

        manager = ContainerManager()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("docker not found")

            with pytest.raises(DockerNotAvailableError) as exc_info:
                manager.start_container()

            assert "docker" in str(exc_info.value).lower()

    def test_WHEN_docker_compose_file_missing_THEN_config_error_raised(self):
        """Test error when docker-compose configuration file is missing."""
        from amplihack.memory.neo4j.container_manager import ContainerManager
        from amplihack.memory.neo4j.exceptions import ConfigurationError

        # Point to non-existent compose file
        manager = ContainerManager(compose_file="/nonexistent/docker-compose.yml")

        with pytest.raises(ConfigurationError) as exc_info:
            manager.start_container()

        assert "compose" in str(exc_info.value).lower()


class TestContainerManagerShutdown:
    """Test container shutdown functionality."""

    def test_WHEN_stop_container_called_THEN_docker_compose_down_executed(self):
        """Test that stop_container executes docker-compose down command."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Container stopped")

            result = manager.stop_container()

            assert result is True
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "down" in call_args or "stop" in call_args

    def test_WHEN_container_not_running_THEN_stop_is_graceful(self):
        """Test that stopping a non-running container doesn't error."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="No containers to stop")

            # Should not raise exception
            result = manager.stop_container()
            assert result is True


class TestContainerHealthCheck:
    """Test container health monitoring."""

    def test_WHEN_container_healthy_THEN_health_check_returns_true(self):
        """Test health check on a healthy container."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        with patch("subprocess.run") as mock_run:
            # Simulate healthy container response
            mock_run.return_value = Mock(returncode=0, stdout='{"Status": "healthy"}')

            is_healthy = manager.is_healthy()

            assert is_healthy is True

    def test_WHEN_container_unhealthy_THEN_health_check_returns_false(self):
        """Test health check on an unhealthy container."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"Status": "unhealthy"}')

            is_healthy = manager.is_healthy()

            assert is_healthy is False

    def test_WHEN_health_check_times_out_THEN_returns_false(self):
        """Test health check timeout handling."""
        import subprocess

        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=5)

            is_healthy = manager.is_healthy(timeout=5)

            assert is_healthy is False

    def test_WHEN_health_check_with_custom_timeout_THEN_timeout_is_respected(self):
        """Test that custom timeout is passed to subprocess."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"Status": "healthy"}')

            manager.is_healthy(timeout=10)

            # Verify timeout parameter was passed
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs.get("timeout") == 10


class TestContainerStatus:
    """Test container status monitoring."""

    def test_WHEN_container_running_THEN_status_returns_running(self):
        """Test status check for running container."""
        from amplihack.memory.neo4j.container_manager import ContainerManager
        from amplihack.memory.neo4j.models import ContainerStatus

        manager = ContainerManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Up 2 hours")

            status = manager.get_status()

            assert status == ContainerStatus.RUNNING

    def test_WHEN_container_stopped_THEN_status_returns_stopped(self):
        """Test status check for stopped container."""
        from amplihack.memory.neo4j.container_manager import ContainerManager
        from amplihack.memory.neo4j.models import ContainerStatus

        manager = ContainerManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Exited (0) 5 minutes ago")

            status = manager.get_status()

            assert status == ContainerStatus.STOPPED

    def test_WHEN_container_not_found_THEN_status_returns_not_found(self):
        """Test status check when container doesn't exist."""
        from amplihack.memory.neo4j.container_manager import ContainerManager
        from amplihack.memory.neo4j.models import ContainerStatus

        manager = ContainerManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")

            status = manager.get_status()

            assert status == ContainerStatus.NOT_FOUND

    def test_WHEN_container_starting_THEN_status_returns_starting(self):
        """Test status check for container in starting state."""
        from amplihack.memory.neo4j.container_manager import ContainerManager
        from amplihack.memory.neo4j.models import ContainerStatus

        manager = ContainerManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Up 2 seconds (health: starting)")

            status = manager.get_status()

            assert status == ContainerStatus.STARTING


class TestContainerConfiguration:
    """Test container configuration management."""

    def test_WHEN_custom_ports_specified_THEN_ports_are_used(self):
        """Test custom port configuration."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager(bolt_port=7688, http_port=7475)

        assert manager.bolt_port == 7688
        assert manager.http_port == 7475

    def test_WHEN_no_ports_specified_THEN_defaults_are_used(self):
        """Test default port configuration."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()

        assert manager.bolt_port == 7687
        assert manager.http_port == 7474

    def test_WHEN_container_name_specified_THEN_name_is_used(self):
        """Test custom container name."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager(container_name="custom-neo4j")

        assert manager.container_name == "custom-neo4j"

    def test_WHEN_volume_name_specified_THEN_volume_is_used(self):
        """Test custom volume configuration."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager(volume_name="custom_neo4j_data")

        assert manager.volume_name == "custom_neo4j_data"


class TestContainerWaitForReady:
    """Test waiting for container to be ready."""

    def test_WHEN_wait_for_ready_and_becomes_ready_THEN_returns_true(self):
        """Test waiting for container to become ready."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        with patch.object(manager, "is_healthy") as mock_healthy:
            # Simulate container becoming healthy after 2 checks
            mock_healthy.side_effect = [False, False, True]

            result = manager.wait_for_ready(timeout=10, poll_interval=0.1)

            assert result is True

    def test_WHEN_wait_for_ready_times_out_THEN_returns_false(self):
        """Test timeout when waiting for container."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        with patch.object(manager, "is_healthy") as mock_healthy:
            # Container never becomes healthy
            mock_healthy.return_value = False

            result = manager.wait_for_ready(timeout=0.5, poll_interval=0.1)

            assert result is False

    def test_WHEN_wait_for_ready_with_zero_timeout_THEN_checks_once(self):
        """Test immediate check without waiting."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()
        with patch.object(manager, "is_healthy") as mock_healthy:
            mock_healthy.return_value = True

            result = manager.wait_for_ready(timeout=0)

            assert result is True
            mock_healthy.assert_called_once()


@pytest.mark.integration
class TestContainerManagerIntegration:
    """Integration tests requiring Docker (marked as integration)."""

    def test_WHEN_real_docker_available_THEN_container_lifecycle_works(self):
        """Test full container lifecycle with real Docker.

        This test is marked as integration and will be skipped in unit test runs.
        """
        pytest.skip("Requires real Docker daemon - run with: pytest -m integration")
