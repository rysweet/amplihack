"""Comprehensive tests for Neo4j container detection and credential synchronization.

This test suite covers:
1. Container detection with various configurations
2. Credential extraction from running containers
3. Credential synchronization with security validation
4. Edge cases and error handling
5. Integration with launcher
"""

import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest

from amplihack.neo4j.credential_sync import CredentialSync, SyncChoice
from amplihack.neo4j.detector import Neo4jContainer, Neo4jContainerDetector
from amplihack.neo4j.manager import Neo4jManager


class TestNeo4jContainer:
    """Tests for Neo4jContainer dataclass."""

    def test_is_running_with_running_status(self):
        """Test is_running returns True for running containers."""
        container = Neo4jContainer(
            container_id="abc123",
            name="amplihack-neo4j",
            image="neo4j:5.0",
            status="Up 2 hours",
            ports={}
        )
        assert container.is_running() is True

    def test_is_running_with_stopped_status(self):
        """Test is_running returns False for stopped containers."""
        container = Neo4jContainer(
            container_id="abc123",
            name="amplihack-neo4j",
            image="neo4j:5.0",
            status="Exited (0) 1 hour ago",
            ports={}
        )
        assert container.is_running() is False

    def test_get_bolt_port(self):
        """Test extracting Bolt port from container."""
        container = Neo4jContainer(
            container_id="abc123",
            name="amplihack-neo4j",
            image="neo4j:5.0",
            status="running",
            ports={"7687/tcp": "7687", "7474/tcp": "7474"}
        )
        assert container.get_bolt_port() == "7687"

    def test_get_http_port(self):
        """Test extracting HTTP port from container."""
        container = Neo4jContainer(
            container_id="abc123",
            name="amplihack-neo4j",
            image="neo4j:5.0",
            status="running",
            ports={"7687/tcp": "7687", "7474/tcp": "7474"}
        )
        assert container.get_http_port() == "7474"

    def test_get_bolt_port_not_exposed(self):
        """Test get_bolt_port returns None when not exposed."""
        container = Neo4jContainer(
            container_id="abc123",
            name="amplihack-neo4j",
            image="neo4j:5.0",
            status="running",
            ports={}
        )
        assert container.get_bolt_port() is None


class TestNeo4jContainerDetector:
    """Tests for Neo4jContainerDetector."""

    def test_is_docker_available_success(self):
        """Test Docker availability check when Docker is running."""
        detector = Neo4jContainerDetector()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = detector.is_docker_available()
            assert result is True
            mock_run.assert_called_once()

    def test_is_docker_available_failure(self):
        """Test Docker availability check when Docker is not running."""
        detector = Neo4jContainerDetector()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1)

            result = detector.is_docker_available()
            assert result is False

    def test_is_docker_available_timeout(self):
        """Test Docker availability check handles timeout."""
        detector = Neo4jContainerDetector()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("docker", 5)

            result = detector.is_docker_available()
            assert result is False

    def test_is_docker_available_not_installed(self):
        """Test Docker availability check when Docker is not installed."""
        detector = Neo4jContainerDetector()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = detector.is_docker_available()
            assert result is False

    def test_detect_containers_no_docker(self):
        """Test container detection when Docker is unavailable."""
        detector = Neo4jContainerDetector()
        detector._docker_available = False

        result = detector.detect_containers()
        assert result == []

    def test_detect_containers_with_amplihack_neo4j(self):
        """Test detecting amplihack Neo4j containers."""
        detector = Neo4jContainerDetector()

        container_data = json.dumps({
            "ID": "abc123",
            "Names": "amplihack-neo4j",
            "Image": "neo4j:5.0",
            "Status": "Up 2 hours",
            "Ports": "0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp"
        })

        with patch.object(detector, "is_docker_available", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout=container_data + "\n"
                )

                result = detector.detect_containers()
                assert len(result) == 1
                assert result[0].name == "amplihack-neo4j"
                assert result[0].image == "neo4j:5.0"

    def test_detect_containers_filters_non_neo4j(self):
        """Test that non-Neo4j containers are filtered out."""
        detector = Neo4jContainerDetector()

        containers_data = "\n".join([
            json.dumps({
                "ID": "abc123",
                "Names": "postgres",
                "Image": "postgres:14",
                "Status": "Up 2 hours",
                "Ports": ""
            }),
            json.dumps({
                "ID": "def456",
                "Names": "amplihack-neo4j",
                "Image": "neo4j:5.0",
                "Status": "Up 1 hour",
                "Ports": ""
            })
        ])

        with patch.object(detector, "is_docker_available", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout=containers_data + "\n"
                )

                result = detector.detect_containers()
                assert len(result) == 1
                assert result[0].name == "amplihack-neo4j"

    def test_detect_containers_filters_non_amplihack(self):
        """Test that non-amplihack Neo4j containers are filtered out."""
        detector = Neo4jContainerDetector()

        containers_data = "\n".join([
            json.dumps({
                "ID": "abc123",
                "Names": "other-neo4j",
                "Image": "neo4j:5.0",
                "Status": "Up 2 hours",
                "Ports": ""
            }),
            json.dumps({
                "ID": "def456",
                "Names": "amplihack-neo4j",
                "Image": "neo4j:5.0",
                "Status": "Up 1 hour",
                "Ports": ""
            })
        ])

        with patch.object(detector, "is_docker_available", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout=containers_data + "\n"
                )

                result = detector.detect_containers()
                assert len(result) == 1
                assert result[0].name == "amplihack-neo4j"

    def test_extract_credentials_from_running_container(self):
        """Test extracting credentials from running container."""
        detector = Neo4jContainerDetector()

        container = Neo4jContainer(
            container_id="abc123",
            name="amplihack-neo4j",
            image="neo4j:5.0",
            status="Up 2 hours",
            ports={}
        )

        inspect_data = [{
            "Config": {
                "Env": [
                    "PATH=/usr/local/bin",
                    "NEO4J_AUTH=neo4j/testpassword123",
                    "NEO4J_VERSION=5.0"
                ]
            }
        }]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(inspect_data)
            )

            detector.extract_credentials(container)

            assert container.username == "neo4j"
            assert container.password == "testpassword123"

    def test_extract_credentials_separate_env_vars(self):
        """Test extracting credentials from separate environment variables."""
        detector = Neo4jContainerDetector()

        container = Neo4jContainer(
            container_id="abc123",
            name="amplihack-neo4j",
            image="neo4j:5.0",
            status="Up 2 hours",
            ports={}
        )

        inspect_data = [{
            "Config": {
                "Env": [
                    "NEO4J_USER=admin",
                    "NEO4J_PASSWORD=securepass",
                ]
            }
        }]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(inspect_data)
            )

            detector.extract_credentials(container)

            assert container.username == "admin"
            assert container.password == "securepass"

    def test_extract_credentials_stopped_container(self):
        """Test that credentials are not extracted from stopped containers."""
        detector = Neo4jContainerDetector()

        container = Neo4jContainer(
            container_id="abc123",
            name="amplihack-neo4j",
            image="neo4j:5.0",
            status="Exited (0)",
            ports={}
        )

        detector.extract_credentials(container)

        assert container.username is None
        assert container.password is None

    def test_parse_ports(self):
        """Test parsing Docker port strings."""
        detector = Neo4jContainerDetector()

        ports_str = "0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp"
        result = detector._parse_ports(ports_str)

        assert result == {
            "7474/tcp": "7474",
            "7687/tcp": "7687"
        }

    def test_parse_ports_empty(self):
        """Test parsing empty port string."""
        detector = Neo4jContainerDetector()

        result = detector._parse_ports("")
        assert result == {}

    def test_is_amplihack_container(self):
        """Test identifying amplihack containers."""
        detector = Neo4jContainerDetector()

        # Should match
        assert detector._is_amplihack_container("amplihack-neo4j", "neo4j:5.0") is True
        assert detector._is_amplihack_container("neo4j-amplihack", "neo4j:5.0") is True
        assert detector._is_amplihack_container("my-container", "amplihack/neo4j:latest") is True

        # Should not match
        assert detector._is_amplihack_container("other-neo4j", "neo4j:5.0") is False
        assert detector._is_amplihack_container("postgres", "postgres:14") is False


class TestCredentialSync:
    """Tests for CredentialSync."""

    def test_validate_credentials_valid(self):
        """Test validating correct credentials."""
        sync = CredentialSync()

        is_valid, error = sync.validate_credentials("neo4j", "testpassword123")
        assert is_valid is True
        assert error is None

    def test_validate_credentials_empty_username(self):
        """Test validation fails for empty username."""
        sync = CredentialSync()

        is_valid, error = sync.validate_credentials("", "testpassword123")
        assert is_valid is False
        assert "Username cannot be empty" in error

    def test_validate_credentials_empty_password(self):
        """Test validation fails for empty password."""
        sync = CredentialSync()

        is_valid, error = sync.validate_credentials("neo4j", "")
        assert is_valid is False
        assert "Password cannot be empty" in error

    def test_validate_credentials_password_too_short(self):
        """Test validation fails for short password."""
        sync = CredentialSync()

        is_valid, error = sync.validate_credentials("neo4j", "short")
        assert is_valid is False
        assert "too short" in error

    def test_validate_credentials_password_too_long(self):
        """Test validation fails for long password."""
        sync = CredentialSync()

        is_valid, error = sync.validate_credentials("neo4j", "x" * 200)
        assert is_valid is False
        assert "too long" in error

    def test_validate_credentials_invalid_characters(self):
        """Test validation fails for invalid characters."""
        sync = CredentialSync()

        is_valid, error = sync.validate_credentials("neo4j\n", "testpassword123")
        assert is_valid is False
        assert "invalid characters" in error

        is_valid, error = sync.validate_credentials("neo4j", "test\x00pass")
        assert is_valid is False
        assert "invalid characters" in error

    def test_get_existing_credentials_no_file(self):
        """Test getting credentials when .env doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            sync = CredentialSync(env_file)

            username, password = sync.get_existing_credentials()
            assert username is None
            assert password is None

    def test_get_existing_credentials_success(self):
        """Test getting credentials from .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(
                "NEO4J_USERNAME=neo4j\n"
                "NEO4J_PASSWORD=testpassword123\n"
            )
            os.chmod(env_file, stat.S_IRUSR | stat.S_IWUSR)

            sync = CredentialSync(env_file)
            username, password = sync.get_existing_credentials()

            assert username == "neo4j"
            assert password == "testpassword123"

    def test_get_existing_credentials_with_quotes(self):
        """Test getting credentials with quotes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(
                'NEO4J_USERNAME="neo4j"\n'
                "NEO4J_PASSWORD='testpassword123'\n"
            )
            os.chmod(env_file, stat.S_IRUSR | stat.S_IWUSR)

            sync = CredentialSync(env_file)
            username, password = sync.get_existing_credentials()

            assert username == "neo4j"
            assert password == "testpassword123"

    def test_has_credentials(self):
        """Test checking if credentials exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"

            sync = CredentialSync(env_file)
            assert sync.has_credentials() is False

            env_file.write_text(
                "NEO4J_USERNAME=neo4j\n"
                "NEO4J_PASSWORD=testpassword123\n"
            )

            assert sync.has_credentials() is True

    def test_write_credentials_success(self):
        """Test writing credentials to .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            sync = CredentialSync(env_file)

            success = sync._write_credentials("neo4j", "testpassword123")
            assert success is True

            # Verify file exists and has correct permissions
            assert env_file.exists()
            file_mode = os.stat(env_file).st_mode
            assert file_mode & (stat.S_IRGRP | stat.S_IROTH) == 0  # No group/other read

            # Verify content
            content = env_file.read_text()
            assert "NEO4J_USERNAME=neo4j" in content
            assert "NEO4J_PASSWORD=testpassword123" in content

    def test_write_credentials_preserves_other_vars(self):
        """Test that writing credentials preserves other environment variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(
                "OTHER_VAR=value\n"
                "NEO4J_USERNAME=olduser\n"
                "ANOTHER_VAR=value2\n"
            )

            sync = CredentialSync(env_file)
            success = sync._write_credentials("newuser", "newpassword123")
            assert success is True

            content = env_file.read_text()
            assert "OTHER_VAR=value" in content
            assert "ANOTHER_VAR=value2" in content
            assert "NEO4J_USERNAME=newuser" in content
            assert "NEO4J_PASSWORD=newpassword123" in content
            assert "olduser" not in content

    def test_sync_credentials_use_container(self):
        """Test syncing with USE_CONTAINER choice."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            sync = CredentialSync(env_file)

            container = Neo4jContainer(
                container_id="abc123",
                name="amplihack-neo4j",
                image="neo4j:5.0",
                status="running",
                ports={},
                username="neo4j",
                password="containerpass123"
            )

            success = sync.sync_credentials(container, SyncChoice.USE_CONTAINER)
            assert success is True

            username, password = sync.get_existing_credentials()
            assert username == "neo4j"
            assert password == "containerpass123"

    def test_sync_credentials_manual(self):
        """Test syncing with MANUAL choice."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            sync = CredentialSync(env_file)

            container = Neo4jContainer(
                container_id="abc123",
                name="amplihack-neo4j",
                image="neo4j:5.0",
                status="running",
                ports={}
            )

            success = sync.sync_credentials(
                container,
                SyncChoice.MANUAL,
                manual_username="customuser",
                manual_password="custompass123"
            )
            assert success is True

            username, password = sync.get_existing_credentials()
            assert username == "customuser"
            assert password == "custompass123"

    def test_sync_credentials_skip(self):
        """Test syncing with SKIP choice."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            sync = CredentialSync(env_file)

            container = Neo4jContainer(
                container_id="abc123",
                name="amplihack-neo4j",
                image="neo4j:5.0",
                status="running",
                ports={}
            )

            success = sync.sync_credentials(container, SyncChoice.SKIP)
            assert success is True
            assert not env_file.exists()

    def test_needs_sync_no_container_credentials(self):
        """Test needs_sync when container has no credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            sync = CredentialSync(env_file)

            container = Neo4jContainer(
                container_id="abc123",
                name="amplihack-neo4j",
                image="neo4j:5.0",
                status="running",
                ports={}
            )

            assert sync.needs_sync(container) is False

    def test_needs_sync_no_env_credentials(self):
        """Test needs_sync when .env has no credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            sync = CredentialSync(env_file)

            container = Neo4jContainer(
                container_id="abc123",
                name="amplihack-neo4j",
                image="neo4j:5.0",
                status="running",
                ports={},
                username="neo4j",
                password="testpassword123"
            )

            assert sync.needs_sync(container) is True

    def test_needs_sync_credentials_differ(self):
        """Test needs_sync when credentials differ."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(
                "NEO4J_USERNAME=neo4j\n"
                "NEO4J_PASSWORD=oldpassword\n"
            )

            sync = CredentialSync(env_file)

            container = Neo4jContainer(
                container_id="abc123",
                name="amplihack-neo4j",
                image="neo4j:5.0",
                status="running",
                ports={},
                username="neo4j",
                password="newpassword"
            )

            assert sync.needs_sync(container) is True

    def test_needs_sync_credentials_match(self):
        """Test needs_sync when credentials match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(
                "NEO4J_USERNAME=neo4j\n"
                "NEO4J_PASSWORD=testpassword123\n"
            )

            sync = CredentialSync(env_file)

            container = Neo4jContainer(
                container_id="abc123",
                name="amplihack-neo4j",
                image="neo4j:5.0",
                status="running",
                ports={},
                username="neo4j",
                password="testpassword123"
            )

            assert sync.needs_sync(container) is False


class TestNeo4jManager:
    """Tests for Neo4jManager."""

    def test_check_and_sync_no_docker(self):
        """Test check_and_sync when Docker is not available."""
        manager = Neo4jManager(interactive=False)

        with patch.object(manager.detector, "is_docker_available", return_value=False):
            result = manager.check_and_sync()
            assert result is True

    def test_check_and_sync_no_containers(self):
        """Test check_and_sync when no containers are found."""
        manager = Neo4jManager(interactive=False)

        with patch.object(manager.detector, "is_docker_available", return_value=True):
            with patch.object(manager.detector, "get_running_containers", return_value=[]):
                result = manager.check_and_sync()
                assert result is True

    def test_check_and_sync_credentials_already_synced(self):
        """Test check_and_sync when credentials are already synchronized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(
                "NEO4J_USERNAME=neo4j\n"
                "NEO4J_PASSWORD=testpassword123\n"
            )

            manager = Neo4jManager(env_file=env_file, interactive=False)

            container = Neo4jContainer(
                container_id="abc123",
                name="amplihack-neo4j",
                image="neo4j:5.0",
                status="running",
                ports={},
                username="neo4j",
                password="testpassword123"
            )

            with patch.object(manager.detector, "is_docker_available", return_value=True):
                with patch.object(manager.detector, "get_running_containers", return_value=[container]):
                    result = manager.check_and_sync()
                    assert result is True

    def test_check_and_sync_with_sync_needed(self):
        """Test check_and_sync when synchronization is needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            manager = Neo4jManager(env_file=env_file, interactive=False)

            container = Neo4jContainer(
                container_id="abc123",
                name="amplihack-neo4j",
                image="neo4j:5.0",
                status="running",
                ports={},
                username="neo4j",
                password="testpassword123"
            )

            with patch.object(manager.detector, "is_docker_available", return_value=True):
                with patch.object(manager.detector, "get_running_containers", return_value=[container]):
                    result = manager.check_and_sync()
                    assert result is True

                    # Verify credentials were synced
                    username, password = manager.credential_sync.get_existing_credentials()
                    assert username == "neo4j"
                    assert password == "testpassword123"


class TestIntegrationWithLauncher:
    """Integration tests for Neo4j detection with launcher."""

    def test_launcher_graceful_degradation_no_docker(self):
        """Test that launcher handles Neo4j detection gracefully when Docker is unavailable."""
        from amplihack.launcher.core import ClaudeLauncher

        launcher = ClaudeLauncher()

        # Mock Docker unavailable
        with patch("amplihack.neo4j.detector.Neo4jContainerDetector.is_docker_available", return_value=False):
            # Should not raise exception
            launcher._check_neo4j_credentials()

    def test_launcher_graceful_degradation_error(self):
        """Test that launcher handles Neo4j detection errors gracefully."""
        from amplihack.launcher.core import ClaudeLauncher

        launcher = ClaudeLauncher()

        # Mock an exception in Neo4j detection
        with patch("amplihack.neo4j.manager.Neo4jManager.check_and_sync") as mock_check:
            mock_check.side_effect = Exception("Test error")

            # Should not raise exception
            launcher._check_neo4j_credentials()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
