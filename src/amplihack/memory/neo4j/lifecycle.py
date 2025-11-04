"""Neo4j container lifecycle management.

Handles Docker container operations with idempotent design:
- Starting container (detects if already running)
- Stopping container (graceful shutdown)
- Health checking (connection + query verification)
- Status reporting (detailed diagnostics)
"""

import logging
import os
import subprocess
import time
from enum import Enum
from typing import Optional

from .config import get_config
from .connector import Neo4jConnector

logger = logging.getLogger(__name__)


class ContainerStatus(Enum):
    """Container status states."""

    RUNNING = "running"
    STOPPED = "stopped"
    NOT_FOUND = "not_found"
    UNHEALTHY = "unhealthy"


class Neo4jContainerManager:
    """Manages Neo4j Docker container lifecycle.

    All operations are idempotent - safe to call multiple times.
    Uses docker CLI and docker-compose for container management.
    """

    def __init__(self):
        """Initialize container manager with configuration."""
        self.config = get_config()

    def start(self, wait_for_ready: bool = False) -> bool:
        """Start Neo4j container (idempotent).

        Args:
            wait_for_ready: If True, block until Neo4j is healthy

        Returns:
            True if started successfully, False otherwise

        Behavior:
            - If already running: Do nothing, return True
            - If stopped: Start existing container
            - If not found: Create and start new container
        """
        logger.info("Starting Neo4j container: %s", self.config.container_name)

        # Check current status
        status = self.get_status()

        if status == ContainerStatus.RUNNING:
            logger.info("Container already running")
            if wait_for_ready:
                return self.wait_for_healthy()
            return True

        if status == ContainerStatus.STOPPED:
            logger.info("Restarting stopped container")
            return self._restart_container(wait_for_ready)

        # Container doesn't exist - create it
        logger.info("Creating new container")
        return self._create_container(wait_for_ready)

    def stop(self, timeout: int = 30) -> bool:
        """Stop Neo4j container (graceful shutdown).

        Args:
            timeout: Seconds to wait for graceful shutdown

        Returns:
            True if stopped successfully, False otherwise
        """
        logger.info("Stopping Neo4j container: %s", self.config.container_name)

        status = self.get_status()
        if status != ContainerStatus.RUNNING:
            logger.info("Container not running")
            return True

        try:
            cmd = self.config.compose_cmd.split() + [
                "-f",
                str(self.config.compose_file),
                "stop",
                "--timeout",
                str(timeout),
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout + 10
            )

            if result.returncode == 0:
                logger.info("Container stopped successfully")
                return True

            logger.error("Failed to stop container: %s", result.stderr)
            return False

        except subprocess.TimeoutExpired:
            logger.error("Timeout stopping container")
            return False
        except Exception as e:
            logger.error("Error stopping container: %s", e)
            return False

    def get_status(self) -> ContainerStatus:
        """Get current container status.

        Returns:
            ContainerStatus enum value
        """
        try:
            cmd = [
                "docker",
                "ps",
                "-a",
                "--filter",
                f"name={self.config.container_name}",
                "--format",
                "{{.Status}}",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                logger.error("Failed to check container status: %s", result.stderr)
                return ContainerStatus.NOT_FOUND

            status_line = result.stdout.strip()

            if not status_line:
                return ContainerStatus.NOT_FOUND

            if status_line.startswith("Up"):
                # Container running - check if healthy
                if self.is_healthy():
                    return ContainerStatus.RUNNING
                else:
                    return ContainerStatus.UNHEALTHY

            return ContainerStatus.STOPPED

        except subprocess.TimeoutExpired:
            logger.error("Timeout checking container status")
            return ContainerStatus.NOT_FOUND
        except Exception as e:
            logger.error("Error checking container status: %s", e)
            return ContainerStatus.NOT_FOUND

    def is_healthy(self) -> bool:
        """Check if Neo4j is healthy (can connect and query).

        Returns:
            True if healthy, False otherwise
        """
        try:
            with Neo4jConnector() as conn:
                return conn.verify_connectivity()
        except Exception as e:
            logger.debug("Health check failed: %s", e)
            return False

    def wait_for_healthy(self, timeout: Optional[int] = None) -> bool:
        """Wait for Neo4j to become healthy.

        Args:
            timeout: Max seconds to wait (None = use config default)

        Returns:
            True if became healthy within timeout, False otherwise
        """
        timeout = timeout or self.config.startup_timeout
        interval = self.config.health_check_interval

        logger.info("Waiting for Neo4j to become healthy (timeout: %ds)", timeout)

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_healthy():
                elapsed = time.time() - start_time
                logger.info("Neo4j healthy after %.1f seconds", elapsed)
                return True

            time.sleep(interval)

        logger.error("Timeout waiting for Neo4j to become healthy")
        return False

    def get_logs(self, tail: int = 50) -> str:
        """Get container logs for debugging.

        Args:
            tail: Number of lines to retrieve

        Returns:
            Log output as string
        """
        try:
            cmd = ["docker", "logs", "--tail", str(tail), self.config.container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.stdout + result.stderr
        except Exception as e:
            return f"Failed to get logs: {e}"

    def _restart_container(self, wait_for_ready: bool) -> bool:
        """Restart existing stopped container."""
        try:
            cmd = ["docker", "start", self.config.container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error("Failed to restart container: %s", result.stderr)
                return False

            logger.info("Container restarted")

            if wait_for_ready:
                return self.wait_for_healthy()

            return True

        except subprocess.TimeoutExpired:
            logger.error("Timeout restarting container")
            return False
        except Exception as e:
            logger.error("Error restarting container: %s", e)
            return False

    def _create_container(self, wait_for_ready: bool) -> bool:
        """Create and start new container using direct docker run.

        No longer requires docker-compose file.
        """
        logger.info("Creating new Neo4j container with direct docker command")

        try:
            # Use direct docker run (no compose file needed)
            cmd = [
                "docker", "run", "-d",
                "--name", self.config.container_name,
                "--restart", "unless-stopped",
                "-p", f"127.0.0.1:{self.config.http_port}:7474",
                "-p", f"127.0.0.1:{self.config.bolt_port}:7687",
                "-e", f"NEO4J_AUTH=neo4j/{self.config.password}",
                "-e", 'NEO4J_PLUGINS=["apoc"]',
                "-e", "NEO4J_dbms_security_procedures_unrestricted=apoc.*",
                "-e", "NEO4J_dbms_security_procedures_allowlist=apoc.*",
                "-e", f"NEO4J_dbms_memory_heap_max__size={self.config.heap_size}",
                "-e", f"NEO4J_dbms_memory_pagecache_size={self.config.page_cache_size}",
                "-v", f"{self.config.container_name}-data:/data",
                self.config.image,
            ]

            logger.debug("Running: %s", " ".join(cmd))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.config.compose_file.parent.parent,  # Project root
                env=env,
            )

            if result.returncode != 0:
                logger.error("Failed to create container: %s", result.stderr)
                return False

            logger.info("Container created successfully")

            if wait_for_ready:
                return self.wait_for_healthy()

            return True

        except subprocess.TimeoutExpired:
            logger.error("Timeout creating container")
            return False
        except Exception as e:
            logger.error("Error creating container: %s", e)
            return False


# Module-level convenience functions


def ensure_neo4j_running(blocking: bool = False) -> bool:
    """Ensure Neo4j container is running (module convenience function).

    Args:
        blocking: If True, wait for Neo4j to be healthy before returning

    Returns:
        True if Neo4j is running (or started), False otherwise

    This is the main entry point for session integration.
    """
    try:
        manager = Neo4jContainerManager()
        return manager.start(wait_for_ready=blocking)
    except Exception as e:
        logger.error("Failed to ensure Neo4j running: %s", e)
        return False


def check_neo4j_prerequisites() -> dict:
    """Check all prerequisites for Neo4j.

    Returns:
        Dictionary with check results:
        {
            'docker_installed': bool,
            'docker_running': bool,
            'docker_compose_available': bool,
            'compose_file_exists': bool,
            'all_passed': bool,
            'issues': List[str],  # Human-readable fix instructions
        }
    """
    import os

    issues = []

    # Check Docker installed
    docker_installed = False
    try:
        result = subprocess.run(
            ["docker", "--version"], capture_output=True, timeout=5
        )
        docker_installed = result.returncode == 0
    except Exception as e:
        logger.debug("Docker version check failed: %s", e)

    if not docker_installed:
        issues.append(
            "Docker not installed. Install from: https://docs.docker.com/get-docker/"
        )

    # Check Docker daemon running
    docker_running = False
    if docker_installed:
        try:
            result = subprocess.run(["docker", "ps"], capture_output=True, timeout=5)
            docker_running = result.returncode == 0

            if not docker_running and "permission denied" in result.stderr.decode().lower():
                issues.append(
                    "Docker permission denied. Fix with:\n"
                    "  sudo usermod -aG docker $USER\n"
                    "  Then log out and log back in"
                )
            elif not docker_running:
                issues.append(
                    "Docker daemon not running. Start with:\n"
                    "  sudo systemctl start docker"
                )
        except Exception as e:
            logger.debug("Docker daemon check failed: %s", e)

    # Check Docker Compose available
    compose_available = False
    try:
        config = get_config()
        compose_available = True
    except RuntimeError as e:
        issues.append(str(e))

    # Check compose file exists
    compose_file_exists = False
    if compose_available:
        try:
            config = get_config()
            compose_file_exists = config.compose_file.exists()
            if not compose_file_exists:
                issues.append(
                    f"Docker Compose file not found: {config.compose_file}\n"
                    "  This file should be created during setup."
                )
        except Exception as e:
            logger.debug("Compose file check failed: %s", e)

    all_passed = (
        docker_installed and docker_running and compose_available and compose_file_exists
    )

    return {
        "docker_installed": docker_installed,
        "docker_running": docker_running,
        "docker_compose_available": compose_available,
        "compose_file_exists": compose_file_exists,
        "all_passed": all_passed,
        "issues": issues,
    }
