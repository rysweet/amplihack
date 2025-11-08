"""Smart port management for Neo4j with conflict detection and auto-selection.

Handles:
- Port conflict detection
- Auto port selection if conflicts found
- Verification it's OUR Neo4j vs another instance
- .env updates with selected ports
"""

import logging
import socket
import subprocess
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Safer defaults (not standard Neo4j ports to avoid conflicts)
DEFAULT_BOLT_PORT = 7787  # Not 7687 (standard)
DEFAULT_HTTP_PORT = 7774  # Not 7474 (standard)


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if port is in use.

    Args:
        port: Port number to check
        host: Host to check (default localhost)

    Returns:
        True if port is in use, False if available
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0  # 0 means connection successful (port in use)
    except Exception as e:
        logger.debug("Port check failed for %d: %s", port, e)
        return False


def find_available_port(start_port: int, max_attempts: int = 100) -> Optional[int]:
    """Find an available port starting from start_port.

    Args:
        start_port: Port to start searching from
        max_attempts: Maximum ports to try

    Returns:
        Available port number, or None if none found
    """
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            return port
    return None


def is_our_neo4j_container(container_name: str = "amplihack-neo4j") -> bool:
    """Check if our Neo4j container is running.

    Args:
        container_name: Expected container name

    Returns:
        True if our container is running
    """
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            timeout=5,
            text=True,
        )
        return container_name in result.stdout
    except Exception as e:
        logger.debug("Container check failed: %s", e)
        return False


def _parse_port_from_docker_line(line: str, container_port: str, port_type: str) -> Optional[int]:
    """Parse host port number from docker port output line.

    Args:
        line: Output line from 'docker port' command
        container_port: Container port to match (e.g., "7687/tcp")
        port_type: Port type for logging (e.g., "bolt", "HTTP")

    Returns:
        Host port number if successfully parsed, None otherwise

    Example:
        >>> _parse_port_from_docker_line("7687/tcp -> 0.0.0.0:7787", "7687/tcp", "bolt")
        7787
    """
    if container_port not in line or "->" not in line:
        return None

    parts = line.split("->")
    if len(parts) != 2:
        return None

    host_part = parts[1].strip()
    # Format is "0.0.0.0:PORT" or "[::]:PORT"
    if ":" not in host_part:
        return None

    port_str = host_part.split(":")[-1]
    try:
        return int(port_str)
    except ValueError:
        logger.debug("Could not parse %s port from: %s", port_type, line)
        return None


def get_container_ports(container_name: str = "amplihack-neo4j") -> Optional[Tuple[int, int]]:
    """Get the actual mapped ports from a running Docker container.

    Uses `docker port <container>` to retrieve the host-side port mappings
    for the Neo4j bolt (7687) and HTTP (7474) ports.

    Args:
        container_name: Name of the Docker container to query

    Returns:
        (bolt_port, http_port) tuple if container is running and ports are mapped,
        None if container not found, not running, or ports cannot be determined

    Example:
        >>> ports = get_container_ports("amplihack-neo4j")
        >>> if ports:
        ...     bolt_port, http_port = ports
        ...     print(f"Container using ports {bolt_port}/{http_port}")
    """
    try:
        # Run docker port command to get port mappings
        result = subprocess.run(
            ["docker", "port", container_name],
            capture_output=True,
            timeout=5,
            text=True,
            check=False,  # Don't raise on non-zero exit (container might not exist)
        )

        # If command failed (e.g., container not found), return None
        if result.returncode != 0:
            logger.debug("docker port command failed for %s: %s", container_name, result.stderr)
            return None

        # Parse output to find port mappings
        # Expected format:
        # 7474/tcp -> 0.0.0.0:7774
        # 7687/tcp -> 0.0.0.0:7787
        bolt_port = None
        http_port = None

        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue

            # Parse bolt port (7687)
            if bolt_port is None:
                bolt_port = _parse_port_from_docker_line(line, "7687/tcp", "bolt")

            # Parse HTTP port (7474)
            if http_port is None:
                http_port = _parse_port_from_docker_line(line, "7474/tcp", "HTTP")

        # Return tuple only if both ports found
        if bolt_port and http_port:
            logger.debug("Found container ports: bolt=%d, http=%d", bolt_port, http_port)
            return (bolt_port, http_port)

        logger.debug("Could not find both ports in docker output for %s", container_name)
        return None

    except subprocess.TimeoutExpired:
        logger.debug("docker port command timed out for %s", container_name)
        return None
    except Exception as e:
        logger.debug("Error getting container ports for %s: %s", container_name, e)
        return None


def detect_neo4j_on_port(port: int, password: str) -> Tuple[bool, bool]:
    """Detect if there's a Neo4j instance on port and if we can connect.

    Args:
        port: Port to check
        password: Our Neo4j password

    Returns:
        (is_neo4j, can_connect) tuple
    """
    if not is_port_in_use(port):
        return False, False

    # Port is in use - try to connect as Neo4j
    try:
        from neo4j import GraphDatabase
        from neo4j.exceptions import AuthError, ServiceUnavailable

        driver = GraphDatabase.driver(f"bolt://localhost:{port}", auth=("neo4j", password))

        try:
            # Try a simple query
            with driver.session() as session:
                session.run("RETURN 1")
            driver.close()
            return True, True  # Is Neo4j, can connect
        except AuthError:
            driver.close()
            return True, False  # Is Neo4j, wrong password
        except Exception:
            driver.close()
            return False, False  # Not Neo4j or connection failed

    except ServiceUnavailable:
        return False, False  # Not Neo4j (or not responding)
    except Exception as e:
        logger.debug("Neo4j connection test failed: %s", e)
        return False, False


def resolve_port_conflicts(
    bolt_port: int,
    http_port: int,
    password: str,
    project_root: Optional[Path] = None,
) -> Tuple[int, int, list[str]]:
    """Resolve port conflicts and select safe ports.

    Strategy:
    1. Check if ports are in use
    2. If in use, check if it's OUR Neo4j container
    3. If our container: reuse ports
    4. If NOT our container: find different ports and update .env

    Args:
        bolt_port: Desired bolt port
        http_port: Desired HTTP port
        password: Neo4j password
        project_root: Project root for .env updates

    Returns:
        (final_bolt_port, final_http_port, messages)
    """
    messages = []

    # Check if our container is running and get its actual ports
    container_ports = get_container_ports()
    if container_ports:
        actual_bolt, actual_http = container_ports

        # If container ports match what we expect, we're good
        if actual_bolt == bolt_port and actual_http == http_port:
            messages.append(f"✅ Our Neo4j container found on ports {bolt_port}/{http_port}")
            return bolt_port, http_port, messages

        # Container is running but on different ports than .env
        # This happens when .env is out of sync with actual container
        messages.append(
            f"⚠️  Container running on ports {actual_bolt}/{actual_http}, "
            f"but .env specifies {bolt_port}/{http_port}"
        )
        messages.append("    Updating .env to match actual container ports...")

        # Update .env to match reality
        if project_root:
            try:
                _update_env_ports(project_root, actual_bolt, actual_http)
                messages.append(f"✅ Updated .env with actual container ports {actual_bolt}/{actual_http}")
            except Exception as e:
                messages.append(f"⚠️  Could not update .env: {e}")

        return actual_bolt, actual_http, messages

    # Check bolt port
    bolt_in_use = is_port_in_use(bolt_port)
    http_in_use = is_port_in_use(http_port)

    if not bolt_in_use and not http_in_use:
        messages.append(f"✅ Ports {bolt_port}/{http_port} available")
        return bolt_port, http_port, messages

    # Port conflict detected
    if bolt_in_use:
        is_neo4j, can_connect = detect_neo4j_on_port(bolt_port, password)

        if is_neo4j and can_connect:
            messages.append(
                f"✅ Found existing Neo4j on port {bolt_port} (our credentials work - reusing)"
            )
            return bolt_port, http_port, messages
        if is_neo4j and not can_connect:
            # Neo4j on port but WRONG password - belongs to ANOTHER app!
            messages.append(
                f"⚠️  CONFLICT: Neo4j on port {bolt_port} belongs to another application"
            )
            messages.append("    (Cannot authenticate - different instance)")
            messages.append("    Selecting alternative port to avoid interference...")

            # MUST select different port - can't use this one
            new_bolt = find_available_port(bolt_port + 100)
            if new_bolt:
                messages.append(f"✅ Selected safe alternative bolt port: {new_bolt}")
                bolt_port = new_bolt
            else:
                messages.append("❌ Could not find available bolt port")
                # Try wider range
                new_bolt = find_available_port(8000, max_attempts=1000)
                if new_bolt:
                    messages.append(f"✅ Found alternative in range 8000+: {new_bolt}")
                    bolt_port = new_bolt
        else:
            messages.append(f"⚠️  Port {bolt_port} in use by another application")
            # Find alternative port
            new_bolt = find_available_port(bolt_port + 100)
            if new_bolt:
                messages.append(f"✅ Selected alternative bolt port: {new_bolt}")
                bolt_port = new_bolt
            else:
                messages.append("❌ Could not find available bolt port")

    if http_in_use:
        new_http = find_available_port(http_port + 100)
        if new_http:
            messages.append(f"✅ Selected alternative HTTP port: {new_http}")
            http_port = new_http

    # Update .env with new ports
    if project_root:
        try:
            _update_env_ports(project_root, bolt_port, http_port)
            messages.append(f"✅ Updated .env with ports {bolt_port}/{http_port}")
        except Exception as e:
            messages.append(f"⚠️  Could not update .env: {e}")

    return bolt_port, http_port, messages


def _update_env_ports(project_root: Path, bolt_port: int, http_port: int) -> None:
    """Update .env file with selected ports."""
    env_file = project_root / ".env"

    if not env_file.exists():
        return  # Will be created by auto_setup

    lines = env_file.read_text().splitlines()
    updated_lines = []
    bolt_found = False
    http_found = False

    for line in lines:
        if line.startswith("NEO4J_BOLT_PORT="):
            updated_lines.append(f"NEO4J_BOLT_PORT={bolt_port}")
            bolt_found = True
        elif line.startswith("NEO4J_HTTP_PORT="):
            updated_lines.append(f"NEO4J_HTTP_PORT={http_port}")
            http_found = True
        elif line.startswith("NEO4J_URI="):
            updated_lines.append(f"NEO4J_URI=bolt://localhost:{bolt_port}")
        else:
            updated_lines.append(line)

    # Add if not found
    if not bolt_found:
        updated_lines.append(f"NEO4J_BOLT_PORT={bolt_port}")
    if not http_found:
        updated_lines.append(f"NEO4J_HTTP_PORT={http_port}")

    env_file.write_text("\n".join(updated_lines))
    logger.info("Updated .env with ports: bolt=%d, http=%d", bolt_port, http_port)


if __name__ == "__main__":
    # Test port conflict detection
    print("=" * 70)
    print("Testing Port Conflict Detection")
    print("=" * 70)

    bolt, http, msgs = resolve_port_conflicts(7787, 7774, "test_password", Path.cwd())

    for msg in msgs:
        print(msg)

    print(f"\nFinal ports: bolt={bolt}, http={http}")
