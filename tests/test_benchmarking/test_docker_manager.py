"""Tests for DockerManager module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import docker
import docker.errors
from pathlib import Path

import sys
from pathlib import Path

# Add .claude to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude"))

from tools.benchmarking.docker_manager import DockerManager, TrialResult


class TestDockerManagerContextManager:
    """Test context manager lifecycle."""

    def test_context_manager_success(self):
        """Should build image, start container, and cleanup on exit."""
        base = "FROM ubuntu:24.04\n"
        agent = "RUN apt-get update\n"

        with patch('docker.from_env') as mock_docker:
            mock_client = Mock()
            mock_docker.return_value = mock_client

            # Mock successful ping
            mock_client.ping.return_value = True

            # Mock image build
            mock_image = Mock()
            mock_image.id = "test-image-id"
            mock_client.images.build.return_value = (mock_image, [])

            # Mock container creation
            mock_container = Mock()
            mock_container.id = "test-container-id"
            mock_container.status = "running"
            mock_client.containers.run.return_value = mock_container

            with DockerManager(
                base_dockerfile=base,
                agent_dockerfile=agent,
                agent_name="test_agent",
                image_tag="test:latest",
                container_env={}
            ) as dm:
                assert dm.container is not None
                assert dm.image is not None
                assert dm.container.id == "test-container-id"
                assert dm.image.id == "test-image-id"

            # Verify cleanup was called
            mock_container.stop.assert_called_once()
            mock_container.remove.assert_called_once()
            mock_client.images.remove.assert_called_once_with("test-image-id")

    def test_context_manager_cleanup_on_error(self):
        """Should cleanup even when exception occurs inside block."""
        base = "FROM ubuntu:24.04\n"
        agent = "RUN apt-get update\n"

        with patch('docker.from_env') as mock_docker:
            mock_client = Mock()
            mock_docker.return_value = mock_client
            mock_client.ping.return_value = True

            mock_image = Mock()
            mock_image.id = "test-image-id"
            mock_client.images.build.return_value = (mock_image, [])

            mock_container = Mock()
            mock_container.id = "test-container-id"
            mock_client.containers.run.return_value = mock_container

            try:
                with DockerManager(
                    base_dockerfile=base,
                    agent_dockerfile=agent,
                    agent_name="test_agent",
                    image_tag="test:latest",
                    container_env={}
                ) as dm:
                    raise ValueError("Simulated error")
            except ValueError:
                pass

            # Verify cleanup was still called
            mock_container.stop.assert_called_once()
            mock_container.remove.assert_called_once()
            mock_client.images.remove.assert_called_once()


class TestDockerDaemon:
    """Test Docker daemon connectivity."""

    def test_docker_daemon_unreachable(self):
        """Should raise RuntimeError if Docker daemon not running."""
        base = "FROM ubuntu:24.04\n"
        agent = "RUN apt-get update\n"

        with patch('tools.benchmarking.docker_manager.docker.from_env',
                   side_effect=docker.errors.DockerException("Cannot connect")):
            with pytest.raises(RuntimeError, match="Cannot connect to Docker"):
                with DockerManager(
                    base_dockerfile=base,
                    agent_dockerfile=agent,
                    agent_name="test_agent",
                    image_tag="test:latest",
                    container_env={}
                ) as dm:
                    pass

    def test_ping_docker(self):
        """Should verify Docker daemon connectivity."""
        with patch('docker.from_env') as mock_docker:
            mock_client = Mock()
            mock_docker.return_value = mock_client
            mock_client.ping.return_value = True

            dm = DockerManager(
                base_dockerfile="FROM ubuntu:24.04\n",
                agent_dockerfile="",
                agent_name="test",
                image_tag="test:latest",
                container_env={}
            )

            assert dm.ping_docker() is True


class TestImageBuilding:
    """Test Docker image building."""

    def test_build_failure(self):
        """Should raise RuntimeError with logs when Dockerfile invalid."""
        base = "FROM ubuntu:24.04\n"
        agent = "RUN invalid-command-that-does-not-exist\n"

        with patch('docker.from_env') as mock_docker:
            mock_client = Mock()
            mock_docker.return_value = mock_client
            mock_client.ping.return_value = True

            # Mock build failure
            mock_client.images.build.side_effect = docker.errors.BuildError(
                "Build failed",
                ""
            )

            with pytest.raises(RuntimeError, match="Failed to build"):
                with DockerManager(
                    base_dockerfile=base,
                    agent_dockerfile=agent,
                    agent_name="test_agent",
                    image_tag="test:latest",
                    container_env={}
                ) as dm:
                    pass

    def test_combined_dockerfile(self):
        """Should correctly combine base + agent Dockerfiles."""
        base = "FROM ubuntu:24.04\nRUN apt-get update\n"
        agent = "RUN apt-get install -y curl\n"

        with patch('docker.from_env') as mock_docker:
            mock_client = Mock()
            mock_docker.return_value = mock_client
            mock_client.ping.return_value = True

            mock_image = Mock()
            mock_image.id = "test-image-id"
            mock_client.images.build.return_value = (mock_image, [])

            mock_container = Mock()
            mock_exec = Mock()
            mock_exec.output = b"curl 7.81.0\n"
            mock_container.exec_run.return_value = mock_exec
            mock_client.containers.run.return_value = mock_container

            with DockerManager(
                base_dockerfile=base,
                agent_dockerfile=agent,
                agent_name="test_agent",
                image_tag="test:latest",
                container_env={}
            ) as dm:
                # Verify build was called
                assert mock_client.images.build.called
                # Verify the fileobj contains combined dockerfile
                call_kwargs = mock_client.images.build.call_args[1]
                assert 'fileobj' in call_kwargs
                fileobj = call_kwargs['fileobj']
                # Read the content and verify it contains both base and agent
                content = fileobj.read()
                assert base.encode() in content
                assert agent.encode() in content


class TestCommandExecution:
    """Test command execution in containers."""

    def test_exec_command_success(self):
        """Should execute command and return result with exit code 0."""
        with patch('docker.from_env') as mock_docker:
            mock_client = Mock()
            mock_docker.return_value = mock_client
            mock_client.ping.return_value = True

            mock_image = Mock()
            mock_image.id = "test-image-id"
            mock_client.images.build.return_value = (mock_image, [])

            mock_container = Mock()
            mock_container.id = "test-container-id"
            mock_container.status = "running"

            # Mock exec_run
            mock_exec_result = Mock()
            mock_exec_result.exit_code = 0
            mock_exec_result.output = b"hello world\n"
            mock_container.exec_run.return_value = mock_exec_result

            mock_client.containers.run.return_value = mock_container

            with DockerManager(
                base_dockerfile="FROM ubuntu:24.04\n",
                agent_dockerfile="",
                agent_name="test_agent",
                image_tag="test:latest",
                container_env={}
            ) as dm:
                result = dm.exec_command("echo 'hello world'", timeout_seconds=10)

            assert result.exit_code == 0
            assert "hello world" in result.test_output
            assert result.timed_out is False
            assert result.duration_seconds < 10

    def test_exec_command_timeout(self):
        """Should timeout long-running command and kill container."""
        import time

        with patch('docker.from_env') as mock_docker:
            mock_client = Mock()
            mock_docker.return_value = mock_client
            mock_client.ping.return_value = True

            mock_image = Mock()
            mock_image.id = "test-image-id"
            mock_client.images.build.return_value = (mock_image, [])

            mock_container = Mock()
            mock_container.id = "test-container-id"
            mock_container.status = "running"

            # Mock exec_run that takes too long
            def slow_exec(*args, **kwargs):
                time.sleep(5)  # Longer than timeout
                mock_result = Mock()
                mock_result.exit_code = 0
                mock_result.output = b"output"
                return mock_result

            mock_container.exec_run = slow_exec
            mock_client.containers.run.return_value = mock_container

            with DockerManager(
                base_dockerfile="FROM ubuntu:24.04\n",
                agent_dockerfile="",
                agent_name="test_agent",
                image_tag="test:latest",
                container_env={}
            ) as dm:
                result = dm.exec_command("sleep 300", timeout_seconds=2)

            assert result.timed_out is True
            assert result.exit_code == 124  # Timeout convention
            assert result.duration_seconds >= 2

    def test_exec_command_nonzero_exit(self):
        """Should capture non-zero exit codes correctly."""
        with patch('docker.from_env') as mock_docker:
            mock_client = Mock()
            mock_docker.return_value = mock_client
            mock_client.ping.return_value = True

            mock_image = Mock()
            mock_image.id = "test-image-id"
            mock_client.images.build.return_value = (mock_image, [])

            mock_container = Mock()
            mock_container.id = "test-container-id"
            mock_container.status = "running"

            # Mock exec_run with non-zero exit
            mock_exec_result = Mock()
            mock_exec_result.exit_code = 42
            mock_exec_result.output = b""
            mock_container.exec_run.return_value = mock_exec_result

            mock_client.containers.run.return_value = mock_container

            with DockerManager(
                base_dockerfile="FROM ubuntu:24.04\n",
                agent_dockerfile="",
                agent_name="test_agent",
                image_tag="test:latest",
                container_env={}
            ) as dm:
                result = dm.exec_command("exit 42", timeout_seconds=10)

            assert result.exit_code == 42
            assert result.timed_out is False


class TestEnvironmentAndWorkdir:
    """Test environment variables and working directory."""

    def test_environment_injection(self):
        """Container should have access to injected environment variables."""
        env = {"TEST_VAR": "test_value"}

        with patch('docker.from_env') as mock_docker:
            mock_client = Mock()
            mock_docker.return_value = mock_client
            mock_client.ping.return_value = True

            mock_image = Mock()
            mock_image.id = "test-image-id"
            mock_client.images.build.return_value = (mock_image, [])

            mock_container = Mock()
            mock_container.id = "test-container-id"
            mock_container.status = "running"

            # Mock exec_run to return the env var value
            mock_exec_result = Mock()
            mock_exec_result.exit_code = 0
            mock_exec_result.output = b"test_value\n"
            mock_container.exec_run.return_value = mock_exec_result

            mock_client.containers.run.return_value = mock_container

            with DockerManager(
                base_dockerfile="FROM ubuntu:24.04\n",
                agent_dockerfile="",
                agent_name="test_agent",
                image_tag="test:latest",
                container_env=env
            ) as dm:
                result = dm.exec_command("echo $TEST_VAR", timeout_seconds=10)

            # Verify environment was passed to container
            call_args = mock_client.containers.run.call_args
            assert 'environment' in call_args[1]
            assert call_args[1]['environment'] == env

            assert "test_value" in result.test_output

    def test_working_directory(self):
        """Should set working directory to /project by default."""
        with patch('docker.from_env') as mock_docker:
            mock_client = Mock()
            mock_docker.return_value = mock_client
            mock_client.ping.return_value = True

            mock_image = Mock()
            mock_image.id = "test-image-id"
            mock_client.images.build.return_value = (mock_image, [])

            mock_container = Mock()
            mock_container.id = "test-container-id"
            mock_container.status = "running"

            # Mock exec_run to return pwd
            mock_exec_result = Mock()
            mock_exec_result.exit_code = 0
            mock_exec_result.output = b"/project\n"
            mock_container.exec_run.return_value = mock_exec_result

            mock_client.containers.run.return_value = mock_container

            with DockerManager(
                base_dockerfile="FROM ubuntu:24.04\n",
                agent_dockerfile="",
                agent_name="test_agent",
                image_tag="test:latest",
                container_env={},
                working_dir="/project"
            ) as dm:
                result = dm.exec_command("pwd", timeout_seconds=10)

            # Verify working_dir was passed to container
            call_args = mock_client.containers.run.call_args
            assert 'working_dir' in call_args[1]
            assert call_args[1]['working_dir'] == "/project"

            assert "/project" in result.test_output
