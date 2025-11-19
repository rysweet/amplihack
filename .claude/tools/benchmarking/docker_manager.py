"""Docker container lifecycle management with guaranteed cleanup."""

import docker
import docker.errors
from dataclasses import dataclass
from typing import Optional, Dict
from io import BytesIO
import time
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class TrialResult:
    """Result of a single command execution."""
    score: int
    duration_seconds: float
    timed_out: bool
    test_output: str
    exit_code: int
    error_message: Optional[str] = None


class DockerManager:
    """Context manager for Docker container lifecycle with automatic cleanup."""

    def __init__(
        self,
        base_dockerfile: str,
        agent_dockerfile: str,
        agent_name: str,
        image_tag: str,
        container_env: Dict[str, str],
        working_dir: str = "/project"
    ):
        """
        Initialize Docker manager.

        Args:
            base_dockerfile: Base Dockerfile content (common setup)
            agent_dockerfile: Agent-specific Dockerfile (install.dockerfile)
            agent_name: Agent identifier for logging
            image_tag: Docker image tag (e.g., "eval-recipes/claude_code:latest")
            container_env: Environment variables to inject
            working_dir: Container working directory
        """
        self.base_dockerfile = base_dockerfile
        self.agent_dockerfile = agent_dockerfile
        self.agent_name = agent_name
        self.image_tag = image_tag
        self.container_env = container_env
        self.working_dir = working_dir

        # Will be set in __enter__
        self.client: Optional[docker.DockerClient] = None
        self.container: Optional[docker.models.containers.Container] = None
        self.image: Optional[docker.models.images.Image] = None

    def ping_docker(self) -> bool:
        """
        Test Docker daemon connectivity.

        Returns:
            True if Docker is accessible

        Raises:
            RuntimeError: If Docker daemon unreachable
        """
        try:
            if self.client is None:
                self.client = docker.from_env()
            self.client.ping()
            return True
        except docker.errors.DockerException as e:
            raise RuntimeError(f"Cannot connect to Docker daemon: {e}")

    def __enter__(self) -> 'DockerManager':
        """
        Build image and start container.

        Returns:
            self: DockerManager instance for use in context

        Raises:
            RuntimeError: If Docker daemon unreachable
            docker.errors.BuildError: If image build fails
            docker.errors.ContainerError: If container start fails
        """
        try:
            # Connect to Docker daemon
            try:
                self.client = docker.from_env()
                self.ping_docker()
            except docker.errors.DockerException as e:
                raise RuntimeError(f"Cannot connect to Docker daemon: {e}")

            # Combine Dockerfiles
            combined_dockerfile = self.base_dockerfile + "\n" + self.agent_dockerfile

            # Build image
            logger.info(f"Building Docker image: {self.image_tag}")
            try:
                dockerfile_bytes = BytesIO(combined_dockerfile.encode('utf-8'))
                self.image, build_logs = self.client.images.build(
                    fileobj=dockerfile_bytes,
                    tag=self.image_tag,
                    rm=True,  # Remove intermediate containers
                    forcerm=True  # Always remove intermediate containers
                )
                logger.info(f"Image built successfully: {self.image.id}")
            except docker.errors.BuildError as e:
                logger.error(f"Failed to build image: {e}")
                raise RuntimeError(f"Failed to build Docker image: {e}")

            # Start container
            logger.info(f"Starting container for agent: {self.agent_name}")
            try:
                self.container = self.client.containers.run(
                    self.image.id,
                    command="tail -f /dev/null",  # Keep container alive
                    detach=True,
                    environment=self.container_env,
                    working_dir=self.working_dir,
                    mem_limit='4g',  # Resource limits
                    memswap_limit='4g',
                    cpu_period=100000,
                    cpu_quota=200000  # 2 CPUs
                )
                logger.info(f"Container started: {self.container.id}")
            except docker.errors.ContainerError as e:
                logger.error(f"Failed to start container: {e}")
                # Cleanup image on container failure
                if self.image:
                    try:
                        self.client.images.remove(self.image.id)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup image: {cleanup_error}")
                raise RuntimeError(f"Failed to start container: {e}")

            return self

        except Exception as e:
            # Ensure cleanup on any error
            self.__exit__(type(e), e, None)
            raise

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Cleanup: stop and remove container and image.
        Always runs, even on exceptions.
        """
        # Cleanup container
        if self.container is not None:
            try:
                logger.info(f"Stopping container: {self.container.id}")
                self.container.stop(timeout=10)
            except Exception as e:
                logger.warning(f"Failed to stop container: {e}")

            try:
                logger.info(f"Removing container: {self.container.id}")
                self.container.remove()
            except Exception as e:
                logger.warning(f"Failed to remove container: {e}")

        # Cleanup image
        if self.image is not None and self.client is not None:
            try:
                logger.info(f"Removing image: {self.image.id}")
                self.client.images.remove(self.image.id)
            except Exception as e:
                logger.warning(f"Failed to remove image: {e}")

        # Don't suppress exceptions
        return None

    def exec_command(
        self,
        command: str,
        timeout_seconds: int = 180
    ) -> TrialResult:
        """
        Execute command in container with timeout.

        Args:
            command: Shell command to execute
            timeout_seconds: Maximum execution time

        Returns:
            TrialResult with exit code, output, duration, timeout status

        Raises:
            RuntimeError: If no container is running
        """
        if self.container is None:
            raise RuntimeError("No container is running")

        start_time = time.time()
        timed_out = False
        exit_code = 0
        output = ""
        error_message = None

        # Result storage for thread
        result_storage = {
            'exit_code': 0,
            'output': b'',
            'completed': False
        }

        def execute_in_thread():
            """Execute command in thread to enable timeout."""
            try:
                exec_result = self.container.exec_run(
                    command,
                    stdout=True,
                    stderr=True,
                    stream=False
                )
                result_storage['exit_code'] = exec_result.exit_code
                result_storage['output'] = exec_result.output
                result_storage['completed'] = True
            except Exception as e:
                logger.error(f"Command execution failed: {e}")
                result_storage['exit_code'] = 1
                result_storage['output'] = str(e).encode('utf-8')
                result_storage['completed'] = True

        # Start execution thread
        exec_thread = threading.Thread(target=execute_in_thread)
        exec_thread.daemon = True
        exec_thread.start()

        # Wait for completion or timeout
        exec_thread.join(timeout=timeout_seconds)

        duration = time.time() - start_time

        if exec_thread.is_alive():
            # Timeout occurred
            timed_out = True
            exit_code = 124  # Timeout convention
            output = "Command timed out"
            error_message = f"Command exceeded timeout of {timeout_seconds}s"

            # Kill container
            try:
                self.container.kill()
                logger.warning(f"Killed container due to timeout: {self.container.id}")
            except Exception as e:
                logger.error(f"Failed to kill container: {e}")

        else:
            # Command completed
            exit_code = result_storage['exit_code']
            output = result_storage['output'].decode('utf-8', errors='replace')

            if exit_code != 0:
                error_message = f"Command exited with code {exit_code}"

        return TrialResult(
            score=0,  # Will be set by test script
            duration_seconds=duration,
            timed_out=timed_out,
            test_output=output,
            exit_code=exit_code,
            error_message=error_message
        )
