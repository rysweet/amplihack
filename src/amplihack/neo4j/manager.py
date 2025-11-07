"""Neo4j container management and orchestration for amplihack.

This module orchestrates the complete Neo4j container detection and credential sync workflow.
It provides the main entry point for the launcher integration.
"""

import sys
from pathlib import Path
from typing import List, Optional

from .credential_sync import CredentialSync, SyncChoice
from .detector import Neo4jContainer, Neo4jContainerDetector


class Neo4jManager:
    """Orchestrates Neo4j container detection and credential synchronization.

    This manager:
    1. Detects existing amplihack Neo4j containers
    2. Extracts credentials from running containers
    3. Presents user with 4 clear choices
    4. Auto-syncs credentials based on user selection
    5. Handles all edge cases gracefully
    6. Never crashes the launcher
    """

    def __init__(self, env_file: Optional[Path] = None, interactive: bool = True):
        """Initialize Neo4j manager.

        Args:
            env_file: Path to .env file (defaults to .env in current directory)
            interactive: Whether to prompt user for choices (False for testing)
        """
        self.detector = Neo4jContainerDetector()
        self.credential_sync = CredentialSync(env_file)
        self.interactive = interactive

    def check_and_sync(self) -> bool:
        """Main entry point for Neo4j detection and credential sync.

        This method:
        1. Checks if Docker is available
        2. Detects running Neo4j containers
        3. Prompts user for credential sync choice
        4. Synchronizes credentials
        5. Reports results

        Returns:
            True if check completed successfully (even if no action taken)
        """
        try:
            # Check Docker availability (fail gracefully if not available)
            if not self.detector.is_docker_available():
                return True  # Not an error, just Docker not available

            # Detect running Neo4j containers
            containers = self.detector.get_running_containers()

            if not containers:
                # No containers found, nothing to do
                return True

            # Check if credentials already exist and match
            if len(containers) == 1:
                container = containers[0]
                if not self.credential_sync.needs_sync(container):
                    # Credentials already in sync
                    return True

            # Present options and sync
            return self._handle_credential_sync(containers)

        except Exception:
            # Graceful degradation - never crash launcher
            return True

    def _handle_credential_sync(self, containers: List[Neo4jContainer]) -> bool:
        """Handle credential synchronization workflow.

        Args:
            containers: List of detected containers

        Returns:
            True if sync completed successfully
        """
        # Select container (use first if only one, otherwise prompt)
        container = containers[0] if len(containers) == 1 else self._select_container(containers)
        if not container:
            return True  # User cancelled

        # Check if container has credentials
        if not container.username or not container.password:
            if self.interactive:
                print(
                    "Warning: Could not extract credentials from container. "
                    "Please configure credentials manually.",
                    file=sys.stderr
                )
            return True

        # Present choices to user
        choice = self._get_user_choice(container)

        # Handle manual credential input
        manual_username = None
        manual_password = None
        if choice == SyncChoice.MANUAL:
            manual_username, manual_password = self._get_manual_credentials()
            if not manual_username or not manual_password:
                return True  # User cancelled

        # Sync credentials
        success = self.credential_sync.sync_credentials(
            container,
            choice,
            manual_username,
            manual_password
        )

        if success and self.interactive:
            messages = {
                SyncChoice.USE_CONTAINER: "Neo4j credentials synchronized from container.",
                SyncChoice.MANUAL: "Neo4j credentials updated manually.",
                SyncChoice.KEEP_ENV: "Keeping existing Neo4j credentials.",
            }
            if choice in messages:
                print(messages[choice])

        return success

    def _select_container(self, containers: List[Neo4jContainer]) -> Optional[Neo4jContainer]:
        """Prompt user to select a container from multiple options.

        Args:
            containers: List of containers to choose from

        Returns:
            Selected container, or None if cancelled
        """
        if not self.interactive:
            return containers[0]  # Default to first in non-interactive mode

        print("\nMultiple Neo4j containers detected:")
        for i, container in enumerate(containers, 1):
            print(f"{i}. {container.name} ({container.status})")

        while True:
            try:
                choice = input(f"\nSelect container (1-{len(containers)}) or 'q' to skip: ").strip()

                if choice.lower() == 'q':
                    return None

                idx = int(choice) - 1
                if 0 <= idx < len(containers):
                    return containers[idx]

                print(f"Invalid choice. Please enter 1-{len(containers)} or 'q'.")

            except (ValueError, KeyboardInterrupt):
                return None

    def _get_user_choice(self, container: Neo4jContainer) -> SyncChoice:
        """Present user with credential sync choices.

        Args:
            container: Container with detected credentials

        Returns:
            User's choice
        """
        if not self.interactive:
            # In non-interactive mode, use container credentials if they exist
            if container.username and container.password:
                return SyncChoice.USE_CONTAINER
            return SyncChoice.SKIP

        # Check existing credentials
        has_existing = self.credential_sync.has_credentials()

        print("\nNeo4j container detected with credentials.")
        print(f"Container: {container.name}")
        print(f"Username: {container.username}")

        if has_existing:
            env_username, _ = self.credential_sync.get_existing_credentials()
            print(f"\nExisting .env credentials found (username: {env_username})")

        print("\nCredential sync options:")
        print("1. Use credentials from container")
        print("2. Keep existing .env credentials")
        print("3. Enter credentials manually")
        print("4. Skip (don't sync)")

        while True:
            try:
                choice = input("\nSelect option (1-4): ").strip()

                if choice == "1":
                    return SyncChoice.USE_CONTAINER
                elif choice == "2":
                    if has_existing:
                        return SyncChoice.KEEP_ENV
                    print("No existing credentials found. Please choose another option.")
                elif choice == "3":
                    return SyncChoice.MANUAL
                elif choice == "4":
                    return SyncChoice.SKIP
                else:
                    print("Invalid choice. Please enter 1-4.")

            except (KeyboardInterrupt, EOFError):
                return SyncChoice.SKIP

    def _get_manual_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """Prompt user for manual credential entry.

        Returns:
            Tuple of (username, password), or (None, None) if cancelled
        """
        try:
            import getpass

            print("\nEnter Neo4j credentials:")
            username = input("Username: ").strip()

            if not username:
                print("Username cannot be empty.")
                return None, None

            password = getpass.getpass("Password: ")

            if not password:
                print("Password cannot be empty.")
                return None, None

            # Validate
            is_valid, error = self.credential_sync.validate_credentials(username, password)
            if not is_valid:
                print(f"Invalid credentials: {error}")
                return None, None

            return username, password

        except (KeyboardInterrupt, EOFError):
            return None, None

