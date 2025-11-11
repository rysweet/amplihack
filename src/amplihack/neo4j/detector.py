"""Neo4j container detection for amplihack.

This module detects running amplihack Neo4j containers and extracts their configuration.
It follows the Zero-BS philosophy - all functions work or don't exist.
"""

import json
import logging
import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

# Neo4j default port numbers
BOLT_PORT = 7687  # Neo4j Bolt protocol port (connections)
HTTP_PORT = 7474  # Neo4j HTTP protocol port (browser, REST API)


@dataclass
class Neo4jContainer:
    """Represents a detected Neo4j container with its configuration.

    Attributes:
        container_id: Docker container ID
        name: Container name
        image: Docker image name
        status: Container status (running, stopped, etc.)
        ports: Exposed ports (e.g., {"7474/tcp": "7474", "7687/tcp": "7687"})
        username: Neo4j username (extracted from environment)
        password: Neo4j password (extracted from environment)
    """

    container_id: str
    name: str
    image: str
    status: str
    ports: dict
    username: Optional[str] = None
    password: Optional[str] = None

    def is_running(self) -> bool:
        """Check if container is running.

        Returns:
            True if status indicates container is running
        """
        status_lower = self.status.lower()
        return "running" in status_lower or "up" in status_lower

    def get_bolt_port(self) -> Optional[str]:
        """Get the Bolt protocol port.

        Returns:
            Port number as string, or None if not exposed
        """
        return self._get_port(str(BOLT_PORT))

    def get_http_port(self) -> Optional[str]:
        """Get the HTTP port.

        Returns:
            Port number as string, or None if not exposed
        """
        return self._get_port(str(HTTP_PORT))

    def _get_port(self, port_num: str) -> Optional[str]:
        """Get a specific port number from container port mappings.

        Args:
            port_num: Port number to find (e.g., "7687", "7474")

        Returns:
            Host port number as string, or None if not exposed
        """
        for port_mapping, host_port in self.ports.items():
            if port_num in port_mapping:
                return host_port
        return None


class Neo4jContainerDetector:
    """Detects amplihack Neo4j containers and extracts credentials.

    This detector:
    1. Searches for containers with Neo4j images
    2. Filters for amplihack-related containers
    3. Extracts credentials from container environment
    4. Handles all edge cases gracefully
    """

    # Patterns to identify amplihack Neo4j containers
    AMPLIHACK_PATTERNS = [
        r"amplihack.*neo4j",
        r"neo4j.*amplihack",
        r"amplihack-neo4j",
        r"neo4j-amplihack",
    ]

    def __init__(self):
        """Initialize the detector."""
        self._docker_available: Optional[bool] = None

    def is_docker_available(self) -> bool:
        """Check if Docker is available and running.

        Returns:
            True if Docker daemon is accessible
        """
        if self._docker_available is not None:
            return self._docker_available

        try:
            result = subprocess.run(
                ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
            )
            self._docker_available = result.returncode == 0
            return self._docker_available
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            self._docker_available = False
            return False

    def detect_containers(self) -> List[Neo4jContainer]:
        """Detect all amplihack Neo4j containers.

        Returns:
            List of detected Neo4j containers (empty if none found or Docker unavailable)
        """
        if not self.is_docker_available():
            return []

        try:
            # Get all containers with Neo4j image
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{json .}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return []

            containers = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                try:
                    container_data = json.loads(line)

                    # Check if it's a Neo4j container
                    image = container_data.get("Image", "")
                    if "neo4j" not in image.lower():
                        continue

                    # Check if it's amplihack-related
                    name = container_data.get("Names", "")
                    if not self._is_amplihack_container(name, image):
                        continue

                    # Parse container info
                    container = self._parse_container(container_data)
                    if container:
                        containers.append(container)

                except (json.JSONDecodeError, KeyError):
                    # Skip malformed container data
                    continue

            logger.info(f'Detected {len(containers)} Neo4j containers')
        return containers

        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return []

    def _is_amplihack_container(self, name: str, image: str) -> bool:
        """Check if container is amplihack-related.

        Args:
            name: Container name
            image: Container image

        Returns:
            True if container matches amplihack patterns
        """
        combined = f"{name} {image}".lower()
        return any(
            re.search(pattern, combined, re.IGNORECASE) for pattern in self.AMPLIHACK_PATTERNS
        )

    def _parse_container(self, container_data: dict) -> Optional[Neo4jContainer]:
        """Parse container data into Neo4jContainer object.

        Args:
            container_data: Docker container data from ps command

        Returns:
            Neo4jContainer object or None if parsing fails
        """
        try:
            container_id = container_data.get("ID", "")
            name = container_data.get("Names", "")
            image = container_data.get("Image", "")
            status = container_data.get("Status", "")

            # Parse ports
            ports = self._parse_ports(container_data.get("Ports", ""))

            # Create container object (credentials will be extracted separately)
            return Neo4jContainer(
                container_id=container_id, name=name, image=image, status=status, ports=ports
            )

        except (KeyError, ValueError):
            return None

    def _parse_ports(self, ports_str: str) -> dict:
        """Parse Docker ports string into dictionary.

        Args:
            ports_str: Docker ports string (e.g., "0.0.0.0:7474->7474/tcp")

        Returns:
            Dictionary mapping container ports to host ports
        """
        ports = {}

        if not ports_str:
            return ports

        # Split multiple port mappings
        for port_mapping in ports_str.split(","):
            port_mapping = port_mapping.strip()

            # Parse format: "0.0.0.0:7474->7474/tcp" or "7474/tcp"
            match = re.search(r"(?:[\d.]+:)?(\d+)->(\d+)/(tcp|udp)", port_mapping)
            if match:
                host_port, container_port, protocol = match.groups()
                ports[f"{container_port}/{protocol}"] = host_port

        return ports

    def extract_credentials(self, container: Neo4jContainer) -> None:
        """Extract credentials from running container.

        This method modifies the container object in-place, setting username and password.

        Args:
            container: Neo4jContainer to extract credentials for
        """
        if not container.is_running():
            # Can't extract credentials from stopped container
            return

        try:
            # Inspect container to get environment variables
            result = subprocess.run(
                ["docker", "inspect", container.container_id],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.warning(
                    "Failed to inspect container %s: docker command returned %d. "
                    "Neo4j credentials cannot be extracted. User should verify Neo4j configuration manually.",
                    container.container_id[:12],
                    result.returncode,
                )
                return

            inspect_data = json.loads(result.stdout)
            if not inspect_data:
                logger.warning(
                    "Container %s returned empty inspection data. "
                    "Neo4j credentials cannot be extracted.",
                    container.container_id[:12],
                )
                return

            # Extract environment variables
            env_vars = inspect_data[0].get("Config", {}).get("Env", [])

            for env_var in env_vars:
                if "=" not in env_var:
                    continue

                key, value = env_var.split("=", 1)

                # Look for Neo4j auth variables
                if key == "NEO4J_AUTH":
                    # Format: username/password
                    if "/" in value:
                        username, password = value.split("/", 1)
                        container.username = username
                        container.password = password
                elif key == "NEO4J_USER":
                    container.username = value
                elif key == "NEO4J_PASSWORD":
                    container.password = value

        except subprocess.TimeoutExpired:
            logger.warning(
                "Timeout while inspecting container %s (10s timeout). "
                "Neo4j credentials cannot be extracted in time.",
                container.container_id[:12],
            )
        except subprocess.SubprocessError as e:
            logger.warning(
                "Subprocess error while inspecting container %s: %s. "
                "Neo4j credentials cannot be extracted.",
                container.container_id[:12],
                str(e),
            )
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(
                "Failed to parse container inspection data for %s: %s. "
                "Neo4j credentials cannot be extracted. Container configuration may be malformed.",
                container.container_id[:12],
                str(e),
            )

    def get_running_containers(self) -> List[Neo4jContainer]:
        """Get all running amplihack Neo4j containers with credentials.

        Returns:
            List of running containers with extracted credentials
        """
        all_containers = self.detect_containers()
        running_containers = [c for c in all_containers if c.is_running()]

        # Extract credentials for running containers
        for container in running_containers:
            self.extract_credentials(container)

        return running_containers

    def has_amplihack_neo4j(self) -> bool:
        """Quick check if any amplihack Neo4j containers exist.

        Returns:
            True if at least one amplihack Neo4j container exists
        """
        return bool(self.detect_containers())

    def has_running_neo4j(self) -> bool:
        """Quick check if any amplihack Neo4j containers are running.

        Returns:
            True if at least one amplihack Neo4j container is running
        """
        return bool(self.get_running_containers())
