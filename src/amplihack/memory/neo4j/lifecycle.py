"""Neo4j container lifecycle management.

Handles Docker container operations with idempotent design:
- Starting container (detects if already running)
- Stopping container (graceful shutdown)
- Health checking (connection + query verification)
- Status reporting (detailed diagnostics)
"""

import logging
import subprocess
import time
from enum import Enum
from typing import Optional

from .config import get_config, update_password
from .connector import Neo4jConnector
from .credential_detector import detect_container_password
from .port_manager import resolve_port_conflicts

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

    def _check_container_exists(self) -> bool:
        """Check if container exists (any status).

        Returns:
            True if container exists, False otherwise
        """
        try:
            cmd = [
                "docker",
                "ps",
                "-a",
                "--filter",
                f"name=^{self.config.container_name}$",
                "--format",
                "{{.Names}}",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                return False

            # Check for exact name match
            names = result.stdout.strip().split("\n")
            return self.config.container_name in names

        except Exception as e:
            logger.debug("Error checking container existence: %s", e)
            return False

    def _update_password(self, password: str) -> None:
        """Update config password dynamically.

        Args:
            password: New password to use

        Note:
            This updates the singleton config instance to use detected credentials.
        """
        # Update the config singleton with detected password
        update_password(password)
        # Reload config to pick up the new password
        self.config = get_config()

    def _persist_password_to_env(self, password: str) -> None:
        """Persist detected password to .env file for session continuity.

        Args:
            password: Password to persist

        Note:
            This ensures passwords survive between sessions by writing
            to the .env file. Without this, detected passwords are lost
            when the session ends.
        """
        try:
            from pathlib import Path

            # Find project root
            project_root = Path.cwd()
            while project_root != project_root.parent:
                if (project_root / ".claude").exists() or (project_root / ".env").exists():
                    break
                project_root = project_root.parent

            env_file = project_root / ".env"

            # Read existing .env content
            env_content = ""
            if env_file.exists():
                env_content = env_file.read_text()

            # Check if NEO4J_PASSWORD already set correctly
            import re
            password_pattern = r'^NEO4J_PASSWORD=.*$'
            existing_match = re.search(password_pattern, env_content, re.MULTILINE)

            if existing_match:
                # Update existing password
                new_content = re.sub(
                    password_pattern,
                    f'NEO4J_PASSWORD={password}',
                    env_content,
                    flags=re.MULTILINE
                )
            else:
                # Add new password entry
                if env_content and not env_content.endswith('\n'):
                    env_content += '\n'
                new_content = env_content + f'NEO4J_PASSWORD={password}\n'

            # Only write if changed
            if new_content != env_content:
                env_file.write_text(new_content)
                logger.info("✅ Persisted Neo4j password to .env for session continuity")

        except Exception as e:
            logger.warning("Could not persist password to .env: %s", e)
            # Non-fatal - password is still in memory

    def _restart_container_only(self) -> bool:
        """Restart container without credential detection.

        This is a simpler restart that just starts the container
        without the full credential detection flow. Used when we
        need the container running BEFORE we can detect credentials.

        Returns:
            True if container started, False otherwise
        """
        try:
            cmd = ["docker", "start", self.config.container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error("Failed to restart container: %s", result.stderr)
                return False

            logger.info("Container restarted (waiting for startup)")
            return True

        except subprocess.TimeoutExpired:
            logger.error("Timeout restarting container")
            return False
        except Exception as e:
            logger.error("Error restarting container: %s", e)
            return False

    def _handle_unhealthy_container(self) -> bool:
        """Handle unhealthy container by restarting.

        Returns:
            True if container is now healthy, False otherwise
        """
        logger.warning("Container is unhealthy, attempting restart...")

        try:
            # Stop container
            cmd = ["docker", "stop", self.config.container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error("Failed to stop unhealthy container: %s", result.stderr)
                return False

            # Wait a moment
            time.sleep(2)

            # Start container
            cmd = ["docker", "start", self.config.container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error("Failed to restart container: %s", result.stderr)
                return False

            logger.info("Container restarted, waiting for healthy status...")
            return self.wait_for_healthy()

        except subprocess.TimeoutExpired:
            logger.error("Timeout handling unhealthy container")
            return False
        except Exception as e:
            logger.error("Error handling unhealthy container: %s", e)
            return False

    def start(self, wait_for_ready: bool = False) -> bool:
        """Start Neo4j container (idempotent).

        Args:
            wait_for_ready: If True, block until Neo4j is healthy

        Returns:
            True if started successfully, False otherwise

        Behavior:
            - Checks if container exists first
            - If exists: check status → start if needed → detect credentials → update config
            - If not exists: create new container with environment password

        Note:
            Credential detection happens AFTER container is running to ensure
            we can inspect the container's environment variables reliably.
            Detected passwords are persisted to .env for session continuity.
        """
        logger.info("Starting Neo4j container: %s", self.config.container_name)

        # Step 1: Check if container exists (any status)
        container_exists = self._check_container_exists()

        if container_exists:
            logger.info("Container exists, checking status...")

            # Step 2: Check container status FIRST (before credential detection)
            status = self.get_status()

            # Step 3: Ensure container is running before credential detection
            if status == ContainerStatus.STOPPED:
                logger.info("○ Container %s is stopped, restarting...", self.config.container_name)
                if not self._restart_container_only():
                    return False
                # Wait for Docker container to initialize before credential detection.
                # 2 seconds is empirically determined: allows Docker to complete startup
                # and populate environment variables accessible via `docker inspect`.
                # Shorter waits cause intermittent credential detection failures on
                # slower systems or under load.
                time.sleep(2)
                # Update status to reflect the restart
                status = ContainerStatus.RUNNING

            elif status == ContainerStatus.UNHEALTHY:
                logger.warning("⚠ Container %s is unhealthy, attempting restart...", self.config.container_name)
                if not self._handle_unhealthy_container():
                    return False
                # Container is now running after unhealthy recovery
                status = ContainerStatus.RUNNING

            # Step 4: NOW detect credentials (container is running)
            logger.info("Detecting credentials from running container...")
            detected_password = detect_container_password(self.config.container_name)

            # Step 5: Update config AND persist to .env if password detected
            if detected_password:
                logger.info("🔑 Detected credentials from container")
                self._update_password(detected_password)
                self._persist_password_to_env(detected_password)
            else:
                logger.info("No credentials detected, using environment password")

            # Step 6: Final status check - container should be running now
            # Note: status was updated in Step 3 if container was restarted
            if status == ContainerStatus.RUNNING:
                logger.info("✓ Container %s is running", self.config.container_name)
                if wait_for_ready:
                    return self.wait_for_healthy()
                return True

            logger.error("Unexpected container status after start: %s", self.get_status())
            return False

        # Container doesn't exist - create it
        logger.info("✨ Creating new container: %s", self.config.container_name)
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
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)

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
        """Create and start new container with port conflict resolution.

        Automatically detects and resolves port conflicts before creating container.
        Includes retry logic for race conditions.
        """
        logger.info("Creating new Neo4j container with port conflict resolution")

        # Resolve port conflicts BEFORE attempting to create container
        try:
            # Find project root by walking up to find .claude directory
            from pathlib import Path

            project_root = Path.cwd()
            while project_root != project_root.parent:
                if (project_root / ".claude").exists():
                    break
                project_root = project_root.parent

            bolt_port, http_port, messages = resolve_port_conflicts(
                bolt_port=self.config.bolt_port,
                http_port=self.config.http_port,
                password=self.config.password,
                project_root=project_root,
                container_name=self.config.container_name,
            )

            # Display port resolution messages to user
            for msg in messages:
                logger.info(msg)

            # Use resolved ports (may differ from config if conflicts detected)
            actual_bolt_port = bolt_port
            actual_http_port = http_port

        except Exception as e:
            logger.warning("Port resolution failed, using config ports: %s", e)
            # Fallback: use config ports if resolution fails
            actual_bolt_port = self.config.bolt_port
            actual_http_port = self.config.http_port

        # Retry logic for race conditions (max 3 attempts)
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info("Container creation attempt %d/%d", attempt, max_attempts)

                # Use direct docker run (no compose file needed)
                cmd = [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    self.config.container_name,
                    "--restart",
                    "unless-stopped",
                    "-p",
                    f"127.0.0.1:{actual_http_port}:7474",
                    "-p",
                    f"127.0.0.1:{actual_bolt_port}:7687",
                    "-e",
                    f"NEO4J_AUTH=neo4j/{self.config.password}",
                    "-e",
                    'NEO4J_PLUGINS=["apoc"]',
                    "-e",
                    "NEO4J_dbms_security_procedures_unrestricted=apoc.*",
                    "-e",
                    "NEO4J_dbms_security_procedures_allowlist=apoc.*",
                    "-e",
                    f"NEO4J_dbms_memory_heap_max__size={self.config.heap_size}",
                    "-e",
                    f"NEO4J_dbms_memory_pagecache_size={self.config.page_cache_size}",
                    "-v",
                    f"{self.config.container_name}-data:/data",
                    self.config.image,
                ]

                logger.debug("Running: %s", " ".join(cmd))

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode != 0:
                    error_msg = result.stderr.lower()

                    # Check for port binding errors (race condition)
                    if "bind" in error_msg and "address already in use" in error_msg:
                        logger.warning(
                            "Port binding race condition detected on attempt %d", attempt
                        )

                        if attempt < max_attempts:
                            # Try to find new ports and retry
                            logger.info("Resolving new ports for retry...")
                            try:
                                bolt_port, http_port, messages = resolve_port_conflicts(
                                    bolt_port=actual_bolt_port + 1,  # Start search from next port
                                    http_port=actual_http_port + 1,
                                    password=self.config.password,
                                    project_root=project_root,
                                    container_name=self.config.container_name,
                                )
                                actual_bolt_port = bolt_port
                                actual_http_port = http_port

                                for msg in messages:
                                    logger.info(msg)

                                continue  # Retry with new ports
                            except Exception as e:
                                logger.error("Failed to resolve new ports: %s", e)
                                return False
                        else:
                            logger.error("Max retries exceeded for port binding")
                            return False

                    # Other errors
                    logger.error("Failed to create container: %s", result.stderr)
                    return False

                # Success!
                logger.info(
                    "Container created successfully on ports %d/%d",
                    actual_bolt_port,
                    actual_http_port,
                )

                if wait_for_ready:
                    return self.wait_for_healthy()

                return True

            except subprocess.TimeoutExpired:
                logger.error("Timeout creating container on attempt %d", attempt)
                if attempt == max_attempts:
                    return False
                # Retry on timeout
                continue

            except Exception as e:
                logger.error("Error creating container on attempt %d: %s", attempt, e)
                if attempt == max_attempts:
                    return False
                # Retry on exception
                continue

        # All attempts failed
        logger.error("Failed to create container after %d attempts", max_attempts)
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

    issues = []

    # Check Docker installed
    docker_installed = False
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, timeout=5)
        docker_installed = result.returncode == 0
    except Exception as e:
        logger.debug("Docker version check failed: %s", e)

    if not docker_installed:
        issues.append("Docker not installed. Install from: https://docs.docker.com/get-docker/")

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
                    "Docker daemon not running. Start with:\n  sudo systemctl start docker"
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

    all_passed = docker_installed and docker_running and compose_available and compose_file_exists

    return {
        "docker_installed": docker_installed,
        "docker_running": docker_running,
        "docker_compose_available": compose_available,
        "compose_file_exists": compose_file_exists,
        "all_passed": all_passed,
        "issues": issues,
    }
