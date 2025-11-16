"""Neo4j shutdown coordination on session exit.

Coordinates graceful Neo4j shutdown: checks connections, prompts user, executes stop.
"""

import logging
import re
import sys
import threading
from pathlib import Path
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
        self._preference = self._load_preference()

    def _validate_preferences_path(self, path: Path) -> Path:
        """Validate preferences path to prevent traversal attacks.

        Args:
            path: Path to validate

        Returns:
            Path: Validated absolute path

        Raises:
            ValueError: If path validation fails
        """
        try:
            # Resolve to absolute path
            resolved = path.resolve()

            # Ensure path ends with expected file
            if resolved.name != "USER_PREFERENCES.md":
                raise ValueError(f"Invalid preferences file: {resolved.name}")

            # Ensure path contains .claude/context
            path_str = str(resolved)
            if ".claude/context" not in path_str:
                raise ValueError(f"Preferences path must contain .claude/context: {resolved}")

            return resolved
        except Exception as e:
            logger.warning("Path validation failed: %s", e)
            raise

    def _load_preference(self) -> str:
        """Load neo4j_auto_shutdown preference from USER_PREFERENCES.md.

        Returns:
            str: 'always', 'never', or 'ask' (default)
        """
        # Try project-local preferences first
        prefs_file = Path.cwd() / ".claude" / "context" / "USER_PREFERENCES.md"
        logger.debug("Checking for preference file: %s", prefs_file)

        if not prefs_file.exists():
            # Fall back to home directory
            prefs_file = Path.home() / ".claude" / "context" / "USER_PREFERENCES.md"
            logger.debug("Project preferences not found, trying home directory: %s", prefs_file)

        if not prefs_file.exists():
            logger.debug(
                "No USER_PREFERENCES.md found in project or home directory. "
                "Using default preference: ask"
            )
            return 'ask'  # Default

        try:
            logger.debug("Reading preferences from: %s", prefs_file)
            # Validate path before reading
            prefs_file = self._validate_preferences_path(prefs_file)
            content = prefs_file.read_text()

            # Parse preference - try "**Current setting:**" format first, then simple format
            match = re.search(r'\*\*Current setting:\*\*\s+(\w+)', content, re.IGNORECASE)
            if not match:
                # Fall back to simple format: "neo4j_auto_shutdown: value"
                match = re.search(r'neo4j_auto_shutdown[:\s]+(\w+)', content, re.IGNORECASE)

            if match:
                value = match.group(1).lower()
                if value in ['always', 'never', 'ask']:
                    logger.info("Loaded neo4j_auto_shutdown preference: %s (from %s)", value, prefs_file.name)
                    logger.debug("Preference file path: %s", prefs_file)
                    return value
                logger.warning(
                    "Invalid neo4j_auto_shutdown value '%s' in %s. "
                    "Must be 'always', 'never', or 'ask'. Using default: ask",
                    value,
                    prefs_file
                )
            else:
                logger.debug(
                    "neo4j_auto_shutdown preference not found in %s. Using default: ask",
                    prefs_file
                )

        except Exception as e:
            logger.warning(
                "Error reading neo4j_auto_shutdown preference from %s: %s. Using default: ask",
                prefs_file,
                e
            )

        return 'ask'  # Default

    def _save_preference(self, value: str) -> None:
        """Save neo4j_auto_shutdown preference to USER_PREFERENCES.md.

        Args:
            value: Preference value ('always', 'never', or 'ask')
        """
        # Try project-local preferences first
        prefs_file = Path.cwd() / ".claude" / "context" / "USER_PREFERENCES.md"

        if not prefs_file.exists():
            logger.warning(
                "Cannot save neo4j_auto_shutdown preference: USER_PREFERENCES.md not found at %s. "
                "Create the file or use /amplihack:customize to manage preferences.",
                prefs_file
            )
            print(
                f"\nNote: Cannot save preference - USER_PREFERENCES.md not found.\n"
                f"Expected location: {prefs_file}\n"
                f"Create the file or use /amplihack:customize to manage preferences.",
                file=sys.stderr
            )
            return

        try:
            # Validate path before reading/writing
            prefs_file = self._validate_preferences_path(prefs_file)
            logger.debug("Saving neo4j_auto_shutdown preference to: %s", prefs_file)
            content = prefs_file.read_text()

            # Check if preference already exists
            if re.search(r'neo4j_auto_shutdown', content, re.IGNORECASE):
                # Update existing preference
                content = re.sub(
                    r'(\*\*Current setting:\*\*\s+)\w+',
                    f'\\1{value}',
                    content,
                    flags=re.IGNORECASE
                )
                prefs_file.write_text(content)
                self._preference = value  # Update in-memory cache
                logger.info("Updated neo4j_auto_shutdown preference to: %s (saved to %s)", value, prefs_file.name)
            else:
                # This shouldn't happen if docs are up to date, but handle it
                logger.warning(
                    "neo4j_auto_shutdown section not found in USER_PREFERENCES.md at %s. "
                    "Cannot save preference. File may need to be updated with the preference section.",
                    prefs_file
                )
                print(
                    f"\nNote: Cannot save preference - neo4j_auto_shutdown section not found in USER_PREFERENCES.md.\n"
                    f"File location: {prefs_file}\n"
                    f"Add the neo4j_auto_shutdown section or use /amplihack:customize to manage preferences.",
                    file=sys.stderr
                )
                return

        except Exception as e:
            logger.warning(
                "Error saving neo4j_auto_shutdown preference to %s: %s (%s)",
                prefs_file,
                e,
                type(e).__name__
            )
            print(
                f"\nNote: Error saving preference: {e}\n"
                f"File location: {prefs_file}",
                file=sys.stderr
            )

    def should_prompt_shutdown(self) -> bool:
        """Determine if we should prompt user for shutdown.

        Returns:
            bool: True if should prompt, False otherwise

        Decision logic:
            - Auto mode: False (skip in auto mode)
            - Preference 'never': False (never prompt)
            - Not last connection: False (don't prompt if others connected)
            - Preference 'always' or 'ask' + Last connection: True (prompt user)
        """
        logger.debug("Evaluating whether to prompt for Neo4j shutdown")

        # Check auto mode first
        if self.auto_mode:
            logger.info("Auto mode enabled - skipping Neo4j shutdown prompt (auto mode bypasses all prompts)")
            return False

        # Check preference
        if self._preference == 'never':
            logger.info("neo4j_auto_shutdown=never - skipping shutdown prompt (user preference)")
            return False

        # Check if last connection
        is_last = self.connection_tracker.is_last_connection()
        if not is_last:
            logger.info("Multiple Neo4j connections detected - skipping shutdown prompt (safe default)")
            logger.debug("Decision: Not prompting because other connections exist")
            return False

        logger.info(
            "Last Neo4j connection detected with preference=%s - will prompt user for shutdown",
            self._preference
        )
        logger.debug("Decision: Prompting for shutdown (last connection + preference allows it)")
        return True

    def prompt_user_shutdown(self) -> bool:
        """Prompt user to shutdown Neo4j database.

        Displays prompt with 10-second timeout.
        Supports preference saving with 'always' and 'never' options.

        Returns:
            bool: True if user accepts shutdown, False otherwise
        """
        logger.debug("Prompting user for Neo4j shutdown decision")

        # If preference is 'always', auto-shutdown without prompt
        if self._preference == 'always':
            logger.info("neo4j_auto_shutdown=always - proceeding with shutdown (no prompt needed)")
            return True

        # Use threading to implement timeout
        user_input: list[Optional[str]] = [None]  # Mutable container for thread communication

        def get_input():
            try:
                response = input("Neo4j database is running. Shutdown now? (y/n/Always/Never): ")
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
            logger.info("User prompt timed out after 10 seconds - defaulting to no shutdown (safe default)")
            print(
                "\n(timeout after 10 seconds - defaulting to no shutdown)\n"
                "Tip: Set preference with 'always' or 'never' to avoid future prompts",
                file=sys.stderr
            )
            return False

        # Check user response
        response = user_input[0]
        logger.debug("User response received: %s", response)

        # Handle preference-saving responses
        if response in ('a', 'always'):
            logger.info("User selected 'always' - saving preference for future sessions and proceeding with shutdown")
            self._save_preference('always')
            return True
        if response in ('v', 'never'):
            logger.info("User selected 'never' - saving preference for future sessions and skipping shutdown")
            self._save_preference('never')
            return False
        if response in ("y", "yes"):
            logger.info("User accepted shutdown (one-time, preference not saved)")
            return True
        logger.info("User declined shutdown (response: %s)", response)
        logger.debug("Treating response as 'no' - skipping shutdown")
        return False

    def execute_shutdown(self) -> bool:
        """Execute Neo4j container shutdown.

        Returns:
            bool: True if shutdown succeeded, False otherwise
        """
        logger.info("Executing Neo4j container shutdown")
        logger.debug("Calling container manager stop method")

        try:
            success = self.container_manager.stop()

            if success:
                logger.info("Neo4j shutdown completed successfully")
                print("Neo4j database stopped successfully", file=sys.stderr)
            else:
                logger.warning("Neo4j shutdown failed - container manager returned False")
                print("Failed to stop Neo4j database", file=sys.stderr)

            return success

        except Exception as e:
            logger.error("Exception during Neo4j shutdown (%s): %s", type(e).__name__, e)
            print(f"Error stopping Neo4j: {e}", file=sys.stderr)
            return False

    def handle_session_exit(self) -> None:
        """Main entry point for session exit handling.

        Coordinates the complete shutdown flow with fail-safe behavior.
        Never raises exceptions - always fails safe.
        """
        try:
            logger.info("Neo4j session exit handler started")
            logger.debug("Beginning shutdown coordination flow")

            # Check if we should prompt
            if not self.should_prompt_shutdown():
                logger.info("Shutdown prompt skipped - no action taken")
                logger.debug("Neo4j session exit handler completed (no shutdown)")
                return

            # Prompt user
            if not self.prompt_user_shutdown():
                logger.info("User declined shutdown - leaving Neo4j running")
                logger.debug("Neo4j session exit handler completed (user declined)")
                return

            # Execute shutdown
            shutdown_success = self.execute_shutdown()

            if shutdown_success:
                logger.info("Neo4j session exit handler completed successfully (shutdown executed)")
            else:
                logger.warning("Neo4j session exit handler completed with errors (shutdown failed)")

            logger.debug("Neo4j session exit handler finished")

        except Exception as e:
            logger.error("Unexpected error in Neo4j session exit handler (%s): %s", type(e).__name__, e)
            logger.debug("Failing safe - not shutting down Neo4j due to error")
