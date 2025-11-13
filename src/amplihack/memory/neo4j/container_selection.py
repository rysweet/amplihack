"""Container naming and selection system for Neo4j.

Provides intelligent container naming and selection with:
- Directory-based default naming (amplihack-<dirname>)
- Interactive mode for selecting existing containers
- Auto mode for non-interactive operation
- Priority hierarchy: CLI > ENV > Default
"""

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from .credential_detector import detect_container_password

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContainerInfo:
    """Information about a Neo4j container.

    Attributes:
        name: Container name
        status: Container status (e.g., "Up", "Exited")
        ports: List of port mappings
    """

    name: str
    status: str
    ports: List[str]


@dataclass(frozen=True)
class NameResolutionContext:
    """Context for resolving container name.

    Attributes:
        cli_arg: Container name from CLI argument (--use-memory-db)
        env_var: Container name from environment (NEO4J_CONTAINER_NAME)
        current_dir: Current working directory path
        auto_mode: Whether running in auto mode (non-interactive)
    """

    cli_arg: Optional[str]
    env_var: Optional[str]
    current_dir: Path
    auto_mode: bool


def sanitize_directory_name(dirname: str) -> str:
    """Sanitize directory name for use in container name.

    Replaces special characters with dashes and truncates at 40 chars.

    Args:
        dirname: Directory name to sanitize

    Returns:
        Sanitized container name component

    Example:
        >>> sanitize_directory_name("my-project_v2.0")
        'my-project-v2-0'
        >>> sanitize_directory_name("a" * 50)  # Returns 40 chars
        'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    """
    # Replace special chars with dashes
    sanitized = re.sub(r"[^a-zA-Z0-9-]", "-", dirname)

    # Remove consecutive dashes
    sanitized = re.sub(r"-+", "-", sanitized)

    # Remove leading/trailing dashes
    sanitized = sanitized.strip("-")

    # Truncate at 40 chars
    return sanitized[:40]


def get_default_container_name(current_dir: Optional[Path] = None) -> str:
    """Generate default container name based on current directory.

    Args:
        current_dir: Directory to base name on (defaults to cwd)

    Returns:
        Default container name (amplihack-<sanitized-dirname>)

    Example:
        >>> # In directory /home/user/my-project
        >>> get_default_container_name()
        'amplihack-my-project'
    """
    if current_dir is None:
        current_dir = Path.cwd()

    dirname = current_dir.name
    sanitized = sanitize_directory_name(dirname)

    return f"amplihack-{sanitized}"


def extract_ports(container_name: str) -> List[str]:
    """Extract port mappings from a container.

    Args:
        container_name: Name of the container

    Returns:
        List of port mapping strings (e.g., ["7787->7687", "7774->7474"])
    """
    try:
        import subprocess

        result = subprocess.run(
            ["docker", "inspect", container_name, "--format", "{{json .NetworkSettings.Ports}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return []

        # Parse port mappings from JSON
        import json

        ports_data = json.loads(result.stdout)

        port_mappings = []
        for internal_port, bindings in ports_data.items():
            if bindings:
                for binding in bindings:
                    host_port = binding.get("HostPort", "?")
                    # Remove /tcp or /udp suffix from internal port
                    clean_internal = internal_port.split("/")[0]
                    port_mappings.append(f"{host_port}->{clean_internal}")

        return sorted(port_mappings)

    except Exception as e:
        logger.debug("Failed to extract ports: %s", e)
        return []


def format_ports(ports: List[str]) -> str:
    """Format port list for display.

    Args:
        ports: List of port mappings

    Returns:
        Formatted string (e.g., "7787->7687, 7774->7474")
    """
    if not ports:
        return "no ports"
    return ", ".join(ports)


def discover_amplihack_containers() -> List[ContainerInfo]:
    """Discover all amplihack-* containers.

    Returns:
        List of ContainerInfo objects for all amplihack-* containers

    Note:
        Returns empty list if Docker is not available
    """
    try:
        import subprocess

        # Check if Docker is available
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=amplihack-", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            logger.debug("Docker not available or error listing containers")
            return []

        container_names = [name.strip() for name in result.stdout.splitlines() if name.strip()]

        # Get detailed info for each container
        containers = []
        for name in container_names:
            status_result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={name}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            status = status_result.stdout.strip() if status_result.returncode == 0 else "Unknown"
            ports = extract_ports(name)

            containers.append(ContainerInfo(name=name, status=status, ports=ports))

        return containers

    except subprocess.TimeoutExpired:
        logger.warning("Timeout discovering containers")
        return []
    except FileNotFoundError:
        logger.debug("Docker not installed")
        return []
    except Exception as e:
        logger.warning("Failed to discover containers: %s", e)
        return []


def select_container_interactive(containers: List[ContainerInfo], default_name: str) -> str:
    """Interactive menu for selecting or creating a container.

    Args:
        containers: List of existing containers
        default_name: Default name for new container

    Returns:
        Selected container name

    Raises:
        KeyboardInterrupt: If user cancels selection (Ctrl+C)
    """
    print("\n" + "=" * 70)
    print("Neo4j Container Selection")
    print("=" * 70)

    if not containers:
        print("\nNo existing amplihack-* containers found.")
        print(f"Creating new container: {default_name}")
        return default_name

    print("\nExisting containers:")
    for i, container in enumerate(containers, 1):
        status_icon = "✓" if "Up" in container.status else "○"
        ports_str = format_ports(container.ports)

        # Detect credentials for this container
        detected_password = detect_container_password(container.name)
        cred_icon = "🔑" if detected_password else "⚠️"

        print(f"  {i}. {status_icon} {cred_icon} {container.name}")
        print(f"     Status: {container.status}")
        print(f"     Ports: {ports_str}")
        if detected_password:
            print("     Credentials: Detected")
        else:
            print("     Credentials: Not detected (will use environment)")

    print(f"\n  {len(containers) + 1}. Create new container: {default_name}")

    while True:
        try:
            choice = input(f"\nSelect container (1-{len(containers) + 1}): ").strip()

            if not choice:
                continue

            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(containers):
                    selected = containers[choice_num - 1].name
                    print(f"\n✓ Selected: {selected}\n")
                    return selected
                if choice_num == len(containers) + 1:
                    print(f"\n✓ Creating new: {default_name}\n")
                    return default_name
                print(f"Please enter a number between 1 and {len(containers) + 1}")
            except ValueError:
                print("Please enter a valid number")

        except KeyboardInterrupt:
            print("\n\nCancelled by user")
            raise


def resolve_container_name(
    context: Optional[NameResolutionContext] = None,
    cli_arg: Optional[str] = None,
    env_var: Optional[str] = None,
    current_dir: Optional[Path] = None,
    auto_mode: Optional[bool] = None,
) -> str:
    """Resolve container name using priority hierarchy.

    Priority: CLI argument > ENV variable > Interactive/Auto selection > Default

    Args:
        context: Pre-built context object (if provided, other args ignored)
        cli_arg: Container name from CLI (--use-memory-db)
        env_var: Container name from environment (NEO4J_CONTAINER_NAME)
        current_dir: Current working directory
        auto_mode: Whether in auto mode

    Returns:
        Resolved container name

    Raises:
        KeyboardInterrupt: If user cancels interactive selection
    """
    # Build context if not provided
    if context is None:
        if current_dir is None:
            current_dir = Path.cwd()
        if auto_mode is None:
            auto_mode = os.getenv("AMPLIHACK_AUTO_MODE", "0") == "1"

        # Check for CLI arg from environment (set by launch_command)
        if cli_arg is None:
            cli_arg = os.getenv("NEO4J_CONTAINER_NAME_CLI")

        context = NameResolutionContext(
            cli_arg=cli_arg,
            env_var=env_var,
            current_dir=current_dir,
            auto_mode=auto_mode,
        )

    # Priority 1: CLI argument
    if context.cli_arg:
        logger.info("Using container from CLI: %s", context.cli_arg)
        return context.cli_arg

    # Priority 2: Environment variable
    if context.env_var:
        logger.info("Using container from ENV: %s", context.env_var)
        return context.env_var

    # Priority 3: Auto mode or Interactive selection
    default_name = get_default_container_name(context.current_dir)

    if context.auto_mode:
        # Auto mode: Use default without prompting
        logger.info("Auto mode: Using default container: %s", default_name)
        return default_name

    # Interactive mode: Show menu
    try:
        containers = discover_amplihack_containers()
        return select_container_interactive(containers, default_name)
    except KeyboardInterrupt:
        # User cancelled - re-raise to allow caller to handle
        raise
    except Exception as e:
        # On error, fall back to default
        logger.warning("Container selection failed: %s, using default", e)
        return default_name


def get_container_status(container_name: str) -> Tuple[bool, str]:
    """Check if a container exists and is running.

    Args:
        container_name: Name of the container to check

    Returns:
        Tuple of (exists, status_string)

    Example:
        >>> exists, status = get_container_status("amplihack-myproject")
        >>> if exists and "Up" in status:
        ...     print("Container is running")
    """
    try:
        import subprocess

        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return False, "Docker error"

        status = result.stdout.strip()
        if not status:
            return False, "Not found"

        return True, status

    except Exception as e:
        logger.debug("Failed to get container status: %s", e)
        return False, str(e)
