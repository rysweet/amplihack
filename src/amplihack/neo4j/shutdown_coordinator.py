"""Neo4j shutdown coordination on session exit.

Coordinates graceful Neo4j shutdown: checks connections, prompts user, executes stop.
"""

import logging
import sys
import threading
from typing import Optional

from amplihack.memory.neo4j.lifecycle import Neo4jContainerManager

from .connection_tracker import Neo4jConnectionTracker

logger = logging.getLogger(__name__)


class Neo4jShutdownCoordinator:
    """Coordinate Neo4j shutdown on session exit.

    Handles the complete shutdown flow:
    1. Check if shutdown should be prompted
    2. Prompt user with timeout
    3. Execute shutdown if approved
    """

    def __init__(
        self,
        connection_tracker: Neo4jConnectionTracker,
        container_manager: Neo4jContainerManager,
        auto_mode: bool = False,
    ):
        """Initialize shutdown coordinator.

        Args:
            connection_tracker: Connection tracker for checking active connections
            container_manager: Container manager for executing shutdown
            auto_mode: If True, skip prompts (auto mode)
        """
        self.connection_tracker = connection_tracker
        self.container_manager = container_manager
        self.auto_mode = auto_mode

    def should_prompt_shutdown(self) -> bool:
        """Determine if we should prompt user for shutdown.

        Returns:
            bool: True if should prompt, False otherwise

        Decision logic:
            - Auto mode: False (skip in auto mode)
            - Not last connection: False (don't prompt if others connected)
            - Last connection: True (prompt user)
        """
        # Check auto mode first
        if self.auto_mode:
            logger.debug("Auto mode enabled - skipping shutdown prompt")
            return False

        # Check if last connection
        if not self.connection_tracker.is_last_connection():
            logger.debug("Not last connection - skipping shutdown prompt")
            return False

        logger.debug("Last connection detected - should prompt for shutdown")
        return True

    def prompt_user_shutdown(self) -> bool:
        """Prompt user to shutdown Neo4j database.

        Displays prompt with 10-second timeout.
        Default is 'N' (no shutdown).

        Returns:
            bool: True if user accepts shutdown, False otherwise
        """
        # Use threading to implement timeout
        user_input: list[Optional[str]] = [None]  # Mutable container for thread communication

        def get_input():
            try:
                response = input("Neo4j database is running. Shutdown now? (y/N): ")
                user_input[0] = response.strip().lower()
            except (EOFError, KeyboardInterrupt):
                user_input[0] = "n"

        # Start input thread
        input_thread = threading.Thread(target=get_input, daemon=True)
        input_thread.start()

        # Wait for timeout
        input_thread.join(timeout=10.0)

        # Check if input was received
        if input_thread.is_alive():
            # Timeout - default to 'N'
            logger.info("Prompt timeout - defaulting to no shutdown")
            print("\n(timeout - defaulting to no shutdown)", file=sys.stderr)
            return False

        # Check user response
        response = user_input[0]
        if response in ("y", "yes"):
            logger.info("User accepted shutdown")
            return True

        logger.info("User declined shutdown (response: %s)", response)
        return False

    def execute_shutdown(self) -> bool:
        """Execute Neo4j container shutdown.

        Returns:
            bool: True if shutdown succeeded, False otherwise
        """
        logger.info("Executing Neo4j shutdown")

        try:
            success = self.container_manager.stop()

            if success:
                logger.info("Neo4j shutdown successful")
                print("Neo4j database stopped successfully", file=sys.stderr)
            else:
                logger.warning("Neo4j shutdown failed")
                print("Failed to stop Neo4j database", file=sys.stderr)

            return success

        except Exception as e:
            logger.error("Error during Neo4j shutdown: %s", e)
            print(f"Error stopping Neo4j: {e}", file=sys.stderr)
            return False

    def handle_session_exit(self) -> None:
        """Main entry point for session exit handling.

        Coordinates the complete shutdown flow with fail-safe behavior.
        Never raises exceptions - always fails safe.
        """
        try:
            logger.debug("Neo4j session exit handler started")

            # Check if we should prompt
            if not self.should_prompt_shutdown():
                logger.debug("Skipping Neo4j shutdown prompt")
                return

            # Prompt user
            if not self.prompt_user_shutdown():
                logger.debug("User declined shutdown")
                return

            # Execute shutdown
            self.execute_shutdown()

            logger.debug("Neo4j session exit handler completed")

        except Exception as e:
            logger.error("Error in Neo4j session exit handler: %s", e)
