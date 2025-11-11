"""Unified Neo4j startup dialog - consolidates container selection and credential management.

This module replaces the two-stage dialog system with a single, cohesive interface that:
1. Shows all existing containers with their status and credentials
2. Indicates .env sync status for each container
3. Allows user to select container or create new one
4. Automatically handles credential synchronization based on selection

Design Philosophy:
- One dialog, one decision
- All information visible upfront
- Minimal user interaction required
- Clear feedback on what will happen
"""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ContainerOption:
    """Represents a container option in the unified dialog.

    Attributes:
        name: Container name
        status: Running status ("Up", "Exited", etc.)
        ports: List of port mappings
        username: Detected username (None if not detected)
        password: Detected password (None if not detected)
        env_sync_status: Status of .env sync ("match", "different", "missing", "no_container_creds")
        is_running: Whether container is currently running
    """
    name: str
    status: str
    ports: List[str]
    username: Optional[str]
    password: Optional[str]
    env_sync_status: str
    is_running: bool


def detect_container_options(default_name: str) -> List[ContainerOption]:
    """Detect all existing containers and build options list.

    Args:
        default_name: Default name for new container

    Returns:
        List of ContainerOption objects (existing + create new option)
    """
    from .container_selection import discover_amplihack_containers
    from ...neo4j.detector import Neo4jContainerDetector
    from ...neo4j.credential_sync import CredentialSync

    options = []

    # Discover existing containers
    containers = discover_amplihack_containers()

    # Build credential sync checker
    credential_sync = CredentialSync()

    # Detect credentials for each container
    detector = Neo4jContainerDetector()

    for container in containers:
        # Extract credentials
        username = None
        password = None
        try:
            detected = detector.detect_container(container.name)
            if detected:
                username = detected.username
                password = detected.password
        except Exception as e:
            logger.debug("Could not detect credentials for %s: %s", container.name, e)

        # Check env sync status
        env_sync_status = _check_env_sync_status(credential_sync, username, password)

        is_running = "Up" in container.status

        options.append(ContainerOption(
            name=container.name,
            status=container.status,
            ports=container.ports,
            username=username,
            password=password,
            env_sync_status=env_sync_status,
            is_running=is_running,
        ))

    return options


def _check_env_sync_status(
    credential_sync,
    container_username: Optional[str],
    container_password: Optional[str],
) -> str:
    """Check sync status between container credentials and .env.

    Args:
        credential_sync: CredentialSync instance
        container_username: Username from container
        container_password: Password from container

    Returns:
        Status string: "match", "different", "missing", "no_container_creds"
    """
    if not container_username or not container_password:
        return "no_container_creds"

    env_username, env_password = credential_sync.get_existing_credentials()

    if env_username is None or env_password is None:
        return "missing"

    if env_username == container_username and env_password == container_password:
        return "match"

    return "different"


def _format_env_sync_status(status: str) -> str:
    """Format env sync status for display.

    Args:
        status: Status string from _check_env_sync_status

    Returns:
        Formatted status string with icon
    """
    status_map = {
        "match": "Credentials match ✓",
        "different": "Different credentials ⚠",
        "missing": "No .env credentials",
        "no_container_creds": "Could not detect credentials",
    }
    return status_map.get(status, "Unknown")


def _format_ports(ports: List[str]) -> str:
    """Format port list for display."""
    if not ports:
        return "no ports"
    return ", ".join(ports)


def display_unified_dialog(options: List[ContainerOption], default_name: str) -> Optional[ContainerOption]:
    """Display unified container selection and credential dialog.

    Args:
        options: List of existing container options
        default_name: Default name for new container

    Returns:
        Selected ContainerOption, or None if user cancelled

    Raises:
        KeyboardInterrupt: If user cancels (Ctrl+C)
    """
    print("\n" + "=" * 70, file=sys.stderr)
    print("Neo4j Container Setup", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    if not options:
        print(f"\nNo existing containers found.", file=sys.stderr)
        print(f"Creating new container: {default_name}", file=sys.stderr)
        # Return a "create new" option
        return ContainerOption(
            name=default_name,
            status="new",
            ports=[],
            username=None,
            password=None,
            env_sync_status="missing",
            is_running=False,
        )

    print("\nExisting containers:", file=sys.stderr)
    for i, option in enumerate(options, 1):
        status_icon = "✓" if option.is_running else "○"
        print(f"  {i}. {status_icon} {option.name} ({option.status})", file=sys.stderr)
        print(f"     Ports: {_format_ports(option.ports)}", file=sys.stderr)

        if option.username:
            print(f"     Credentials: {option.username} / [detected]", file=sys.stderr)
            print(f"     .env status: {_format_env_sync_status(option.env_sync_status)}", file=sys.stderr)
        else:
            print(f"     Credentials: Could not detect", file=sys.stderr)
        print(file=sys.stderr)

    # Add "create new" option
    print(f"  {len(options) + 1}. Create new container: {default_name}", file=sys.stderr)

    # Get user choice
    while True:
        try:
            choice = input(f"\nSelect option (1-{len(options) + 1}): ").strip()

            if not choice:
                continue

            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(options):
                    selected = options[choice_num - 1]
                    print(f"\n✓ Selected: {selected.name}", file=sys.stderr)
                    return selected
                elif choice_num == len(options) + 1:
                    print(f"\n✓ Creating new: {default_name}", file=sys.stderr)
                    # Return a "create new" option
                    return ContainerOption(
                        name=default_name,
                        status="new",
                        ports=[],
                        username=None,
                        password=None,
                        env_sync_status="missing",
                        is_running=False,
                    )
                else:
                    print(f"Please enter a number between 1 and {len(options) + 1}", file=sys.stderr)
            except ValueError:
                print("Please enter a valid number", file=sys.stderr)

        except KeyboardInterrupt:
            print("\n\nCancelled by user", file=sys.stderr)
            raise


def handle_credential_sync(selected: ContainerOption) -> bool:
    """Handle credential synchronization after container selection.

    Args:
        selected: Selected container option

    Returns:
        True if credentials are ready, False if user needs to handle manually
    """
    from ...neo4j.credential_sync import CredentialSync, SyncChoice
    from ...neo4j.detector import Neo4jContainer

    credential_sync = CredentialSync()

    # If creating new container, ensure .env has password
    if selected.status == "new":
        if not credential_sync.has_credentials():
            print("\n⚠  No .env credentials found. Auto-setup will create them.", file=sys.stderr)
        return True

    # If credentials match, nothing to do
    if selected.env_sync_status == "match":
        print("\n✓ .env credentials already match container. Ready to proceed!", file=sys.stderr)
        return True

    # If no container credentials detected, user must handle manually
    if selected.env_sync_status == "no_container_creds":
        print("\n⚠  Could not detect container credentials. Please configure .env manually.", file=sys.stderr)
        return False

    # Credentials differ or missing - offer to sync
    if selected.env_sync_status in ["different", "missing"]:
        print(f"\n.env status: {_format_env_sync_status(selected.env_sync_status)}", file=sys.stderr)
        print(f"Container credentials: {selected.username} / [password detected]", file=sys.stderr)

        response = input("\nSync container credentials to .env? (y/n): ").strip().lower()

        if response == "y":
            # Create a Neo4jContainer object for sync
            container = Neo4jContainer(
                container_id="",  # Not needed for credential sync
                name=selected.name,
                image="",  # Not needed for credential sync
                status=selected.status,
                ports={},  # Not needed for credential sync
                username=selected.username,
                password=selected.password,
            )

            success = credential_sync.sync_credentials(container, SyncChoice.USE_CONTAINER)

            if success:
                print("✓ Credentials synchronized to .env", file=sys.stderr)
                return True
            else:
                print("✗ Failed to sync credentials. Please configure .env manually.", file=sys.stderr)
                return False
        else:
            print("\nℹ Using existing .env credentials (if any)", file=sys.stderr)
            return True

    return True


def unified_container_and_credential_dialog(
    default_name: Optional[str] = None,
    auto_mode: bool = False,
) -> Optional[str]:
    """Main entry point for unified container selection and credential dialog.

    This replaces the separate container selection and credential sync dialogs
    with a single, unified interface.

    Args:
        default_name: Default name for new container (auto-detected if None)
        auto_mode: If True, skip interactive dialog and use defaults

    Returns:
        Selected container name, or None if cancelled

    Raises:
        KeyboardInterrupt: If user cancels dialog
    """
    from .container_selection import get_default_container_name

    if default_name is None:
        default_name = get_default_container_name()

    # In auto mode, just use the default
    if auto_mode:
        logger.info("Auto mode: Using default container: %s", default_name)
        return default_name

    try:
        # Detect available options
        options = detect_container_options(default_name)

        # Display unified dialog and get selection
        selected = display_unified_dialog(options, default_name)

        if not selected:
            return None

        # Handle credential synchronization
        handle_credential_sync(selected)

        return selected.name

    except KeyboardInterrupt:
        raise
    except Exception as e:
        logger.warning("Unified dialog failed: %s, using default", e)
        return default_name


if __name__ == "__main__":
    # Test the unified dialog
    try:
        container_name = unified_container_and_credential_dialog()
        if container_name:
            print(f"\n✓ Selected container: {container_name}")
        else:
            print("\n✗ Cancelled")
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted")
