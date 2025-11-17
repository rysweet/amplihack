"""
Unit tests for Neo4j lifecycle port conflict resolution integration.

Tests the integration of port_manager.resolve_port_conflicts() with lifecycle._create_container().

Focus on:
- Port resolution before container creation
- Retry logic for race conditions
- Fallback behavior on resolution failure
- User messaging via logger
"""

import subprocess
from unittest.mock import Mock, patch

from amplihack.memory.neo4j.lifecycle import Neo4jContainerManager


class TestCreateContainerWithPortResolution:
    """Test _create_container() with port conflict resolution."""

    def test_WHEN_ports_available_THEN_container_created_successfully(self):
        """Test successful container creation when ports are available."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run:
            # Port resolution succeeds
            mock_resolve.return_value = (7787, 7774, ["✅ Ports 7787/7774 available"])

            # Docker run succeeds
            mock_run.return_value = Mock(returncode=0, stdout="container_id", stderr="")

            manager = Neo4jContainerManager()
            result = manager._create_container(wait_for_ready=False)

            assert result is True
            mock_resolve.assert_called_once()
            mock_run.assert_called_once()

            # Verify docker command uses resolved ports
            docker_cmd = mock_run.call_args[0][0]
            assert "-p" in docker_cmd
            assert "127.0.0.1:7774:7474" in docker_cmd
            assert "127.0.0.1:7787:7687" in docker_cmd

    def test_WHEN_port_conflict_detected_THEN_uses_alternative_ports(self):
        """Test container creation with alternative ports when conflicts detected."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run:
            # Port resolution finds alternatives
            mock_resolve.return_value = (
                7888,  # Alternative bolt port
                7874,  # Alternative HTTP port
                [
                    "⚠️ Port 7787 in use by another application",
                    "✅ Selected alternative bolt port: 7888",
                    "✅ Selected alternative HTTP port: 7874",
                ],
            )

            # Docker run succeeds with new ports
            mock_run.return_value = Mock(returncode=0, stdout="container_id", stderr="")

            manager = Neo4jContainerManager()
            result = manager._create_container(wait_for_ready=False)

            assert result is True

            # Verify docker command uses alternative ports
            docker_cmd = mock_run.call_args[0][0]
            assert "127.0.0.1:7874:7474" in docker_cmd
            assert "127.0.0.1:7888:7687" in docker_cmd

    def test_WHEN_existing_container_running_THEN_reuses_container_ports(self):
        """Test detection of existing container and port reuse."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run:
            # Resolve detects our container running on different ports
            mock_resolve.return_value = (
                8888,
                9999,
                [
                    "✅ Container 'amplihack-neo4j' found on ports 8888/9999",
                    "✅ Updated .env with actual container ports 8888/9999",
                ],
            )

            # Docker run succeeds
            mock_run.return_value = Mock(returncode=0, stdout="container_id", stderr="")

            manager = Neo4jContainerManager()
            result = manager._create_container(wait_for_ready=False)

            assert result is True

            # Verify docker command uses detected container ports
            docker_cmd = mock_run.call_args[0][0]
            assert "127.0.0.1:9999:7474" in docker_cmd
            assert "127.0.0.1:8888:7687" in docker_cmd


class TestRaceConditionRetryLogic:
    """Test retry logic for port binding race conditions."""

    def test_WHEN_port_binding_fails_once_THEN_retries_with_new_ports(self):
        """Test single retry on port binding race condition."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run:
            # First resolution
            mock_resolve.side_effect = [
                (7787, 7774, ["✅ Ports 7787/7774 available"]),
                (7888, 7874, ["✅ Ports 7888/7874 available"]),  # Retry resolution
            ]

            # First docker run fails with port binding error, second succeeds
            mock_run.side_effect = [
                Mock(returncode=1, stdout="", stderr="Error: bind: address already in use"),
                Mock(returncode=0, stdout="container_id", stderr=""),
            ]

            manager = Neo4jContainerManager()
            result = manager._create_container(wait_for_ready=False)

            assert result is True
            assert mock_resolve.call_count == 2
            assert mock_run.call_count == 2

    def test_WHEN_port_binding_fails_twice_THEN_retries_twice(self):
        """Test multiple retries on repeated port binding race conditions."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run:
            # Three resolutions (initial + 2 retries)
            mock_resolve.side_effect = [
                (7787, 7774, ["✅ Ports 7787/7774 available"]),
                (7888, 7874, ["✅ Ports 7888/7874 available"]),
                (7989, 7975, ["✅ Ports 7989/7975 available"]),
            ]

            # First two fail, third succeeds
            mock_run.side_effect = [
                Mock(returncode=1, stdout="", stderr="bind: address already in use"),
                Mock(returncode=1, stdout="", stderr="bind: address already in use"),
                Mock(returncode=0, stdout="container_id", stderr=""),
            ]

            manager = Neo4jContainerManager()
            result = manager._create_container(wait_for_ready=False)

            assert result is True
            assert mock_resolve.call_count == 3
            assert mock_run.call_count == 3

    def test_WHEN_max_retries_exceeded_THEN_creation_fails(self):
        """Test failure after max retries (3 attempts)."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run:
            # Three resolutions
            mock_resolve.side_effect = [
                (7787, 7774, ["✅ Ports available"]),
                (7888, 7874, ["✅ Ports available"]),
                (7989, 7975, ["✅ Ports available"]),
            ]

            # All three attempts fail
            mock_run.return_value = Mock(
                returncode=1, stdout="", stderr="bind: address already in use"
            )

            manager = Neo4jContainerManager()
            result = manager._create_container(wait_for_ready=False)

            assert result is False
            assert mock_run.call_count == 3


class TestFallbackBehavior:
    """Test fallback behavior when port resolution fails."""

    def test_WHEN_port_resolution_fails_THEN_uses_config_ports(self):
        """Test fallback to config ports when resolution fails."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run:
            # Port resolution raises exception
            mock_resolve.side_effect = RuntimeError("Port resolution failed")

            # Docker run succeeds with config ports
            mock_run.return_value = Mock(returncode=0, stdout="container_id", stderr="")

            manager = Neo4jContainerManager()
            result = manager._create_container(wait_for_ready=False)

            assert result is True

            # Verify docker command uses config ports (fallback)
            docker_cmd = mock_run.call_args[0][0]
            # Should use original config ports (7787/7774 from defaults)
            assert "7787" in " ".join(docker_cmd)
            assert "7774" in " ".join(docker_cmd)

    def test_WHEN_retry_resolution_fails_THEN_creation_fails(self):
        """Test failure when retry port resolution fails."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run:
            # First resolution succeeds, retry resolution fails
            mock_resolve.side_effect = [
                (7787, 7774, ["✅ Ports available"]),
                RuntimeError("Failed to resolve new ports"),
            ]

            # First docker run fails with port binding error
            mock_run.return_value = Mock(
                returncode=1, stdout="", stderr="bind: address already in use"
            )

            manager = Neo4jContainerManager()
            result = manager._create_container(wait_for_ready=False)

            assert result is False


class TestUserMessaging:
    """Test that user messages are logged correctly."""

    def test_WHEN_port_resolution_succeeds_THEN_messages_logged(self):
        """Test that port resolution messages are logged for user visibility."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run, patch(
            "amplihack.memory.neo4j.lifecycle.logger"
        ) as mock_logger:
            mock_resolve.return_value = (
                7787,
                7774,
                ["✅ Ports 7787/7774 available", "No conflicts detected"],
            )

            mock_run.return_value = Mock(returncode=0, stdout="container_id", stderr="")

            manager = Neo4jContainerManager()
            manager._create_container(wait_for_ready=False)

            # Verify messages were logged
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("Ports 7787/7774 available" in msg for msg in info_calls)
            assert any("No conflicts detected" in msg for msg in info_calls)

    def test_WHEN_alternative_ports_selected_THEN_messages_logged(self):
        """Test that alternative port selection is communicated to user."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run, patch(
            "amplihack.memory.neo4j.lifecycle.logger"
        ) as mock_logger:
            mock_resolve.return_value = (
                7888,
                7874,
                [
                    "⚠️ Port 7787 in use by another application",
                    "✅ Selected alternative bolt port: 7888",
                    "✅ Selected alternative HTTP port: 7874",
                ],
            )

            mock_run.return_value = Mock(returncode=0, stdout="container_id", stderr="")

            manager = Neo4jContainerManager()
            manager._create_container(wait_for_ready=False)

            # Verify alternative port messages were logged
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("in use by another application" in msg for msg in info_calls)
            assert any("alternative bolt port: 7888" in msg for msg in info_calls)


class TestContainerCreationWithWaitForReady:
    """Test container creation with wait_for_ready flag."""

    def test_WHEN_wait_for_ready_true_THEN_waits_for_healthy(self):
        """Test that wait_for_ready=True triggers health check wait."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run, patch.object(
            Neo4jContainerManager, "wait_for_healthy"
        ) as mock_wait:
            mock_resolve.return_value = (7787, 7774, ["✅ Ports available"])
            mock_run.return_value = Mock(returncode=0, stdout="container_id", stderr="")
            mock_wait.return_value = True

            manager = Neo4jContainerManager()
            result = manager._create_container(wait_for_ready=True)

            assert result is True
            mock_wait.assert_called_once()

    def test_WHEN_wait_for_ready_false_THEN_returns_immediately(self):
        """Test that wait_for_ready=False returns without waiting."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run, patch.object(
            Neo4jContainerManager, "wait_for_healthy"
        ) as mock_wait:
            mock_resolve.return_value = (7787, 7774, ["✅ Ports available"])
            mock_run.return_value = Mock(returncode=0, stdout="container_id", stderr="")

            manager = Neo4jContainerManager()
            result = manager._create_container(wait_for_ready=False)

            assert result is True
            mock_wait.assert_not_called()


class TestTimeoutHandling:
    """Test timeout handling during container creation."""

    def test_WHEN_docker_run_times_out_THEN_retries(self):
        """Test retry on timeout."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run:
            mock_resolve.return_value = (7787, 7774, ["✅ Ports available"])

            # First attempt times out, second succeeds
            mock_run.side_effect = [
                subprocess.TimeoutExpired(cmd=["docker", "run"], timeout=60),
                Mock(returncode=0, stdout="container_id", stderr=""),
            ]

            manager = Neo4jContainerManager()
            result = manager._create_container(wait_for_ready=False)

            assert result is True
            assert mock_run.call_count == 2

    def test_WHEN_all_attempts_timeout_THEN_creation_fails(self):
        """Test failure when all attempts timeout."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run:
            mock_resolve.return_value = (7787, 7774, ["✅ Ports available"])

            # All attempts timeout
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["docker", "run"], timeout=60)

            manager = Neo4jContainerManager()
            result = manager._create_container(wait_for_ready=False)

            assert result is False
            assert mock_run.call_count == 3  # Max attempts


class TestNonPortErrors:
    """Test handling of non-port-related errors."""

    def test_WHEN_docker_error_not_port_related_THEN_fails_immediately(self):
        """Test that non-port errors don't trigger retry logic."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run:
            mock_resolve.return_value = (7787, 7774, ["✅ Ports available"])

            # Docker fails with non-port error
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error: image not found")

            manager = Neo4jContainerManager()
            result = manager._create_container(wait_for_ready=False)

            assert result is False
            # Should only try once (no retry for non-port errors)
            assert mock_run.call_count == 1

    def test_WHEN_exception_during_docker_run_THEN_retries(self):
        """Test retry on general exception during docker run."""
        with patch(
            "amplihack.memory.neo4j.lifecycle.resolve_port_conflicts"
        ) as mock_resolve, patch("subprocess.run") as mock_run:
            mock_resolve.return_value = (7787, 7774, ["✅ Ports available"])

            # First attempt raises exception, second succeeds
            mock_run.side_effect = [
                RuntimeError("Unexpected error"),
                Mock(returncode=0, stdout="container_id", stderr=""),
            ]

            manager = Neo4jContainerManager()
            result = manager._create_container(wait_for_ready=False)

            assert result is True
            assert mock_run.call_count == 2
