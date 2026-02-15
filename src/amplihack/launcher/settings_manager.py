"""Settings manager for Claude settings.json backup and restoration."""

import json
import select
import shutil
import sys
import time
from pathlib import Path


class SettingsManager:
    """Manages settings.json backup and restoration.

    This class handles:
    - Interactive prompting for settings modification permission
    - Creating timestamped backups of settings.json
    - Restoring settings from backup on exit
    - Managing session state for backup tracking

    Attributes:
        settings_path: Path to the settings.json file
        session_id: Unique identifier for the current session
        non_interactive: If True, skip user prompts (auto-approve)
        backup_path: Path to the current backup file (if created)
    """

    def __init__(self, settings_path: Path, session_id: str, non_interactive: bool = False):
        """Initialize SettingsManager.

        Args:
            settings_path: Path to settings.json file
            session_id: Unique identifier for the session
            non_interactive: If True, skip prompts and auto-approve
        """
        self.settings_path = settings_path
        self.session_id = session_id
        self.non_interactive = non_interactive
        self.backup_path: Path | None = None

        # Session state directory
        self.session_state_dir = Path.home() / ".claude" / "runtime" / "sessions"
        self.session_state_file = self.session_state_dir / f"{session_id}_backup.json"

    def prompt_user_for_modification(self, timeout: int = 30) -> bool:
        """Prompt user for permission to modify settings.json with auto-timeout.

        Shows the backup path and asks for confirmation with a 30-second timeout.
        Default answer is "Y" (pressing Enter or timeout accepts).

        Args:
            timeout: Seconds to wait before auto-approving (default: 30)

        Returns:
            True if user approves or timeout, False if declined
        """
        # Skip prompt if non-interactive mode
        if self.non_interactive:
            return True

        # Skip prompt if not in a TTY (can't get user input)
        if not sys.stdin.isatty():
            return True

        # Generate backup path for display
        timestamp = int(time.time())
        backup_path = self.settings_path.parent / f"{self.settings_path.name}.backup.{timestamp}"

        # Show prompt with timeout info
        prompt = (
            f"We need to edit your ~/.claude/settings.json - "
            f"we will make a backup at {backup_path} and we will restore it "
            f"when claude exits, OK [Y]|n (auto-accept in {timeout}s): "
        )

        print(prompt, end="", flush=True)

        try:
            # Wait for input with timeout using select
            # select.select only works on Unix-like systems with real file descriptors
            if sys.platform == "win32":
                # Windows doesn't support select on stdin, fall back to blocking input
                response = input().strip().lower()
                return response in ("", "y", "yes")

            # Unix: Use select for timeout
            ready, _, _ = select.select([sys.stdin], [], [], timeout)

            if ready:
                # User provided input within timeout
                response = sys.stdin.readline().strip().lower()
                return response in ("", "y", "yes")
            # Timeout - auto-approve
            print(f"\n✨ Auto-approved after {timeout}s timeout")
            return True

        except (EOFError, KeyboardInterrupt):
            # Handle Ctrl+C or EOF gracefully
            print("\nOperation cancelled by user")
            return False

    def create_backup(self) -> tuple[bool, Path | None]:
        """Create a timestamped backup of settings.json.

        Backup format: settings.json.backup.<timestamp>
        Also saves session state to track the backup.

        Returns:
            Tuple of (success, backup_path)
            - success: True if backup created, False otherwise
            - backup_path: Path to backup file if created, None otherwise
        """
        try:
            # Check if settings file exists
            if not self.settings_path.exists():
                return (False, None)

            # Generate timestamped backup path
            timestamp = int(time.time())
            backup_path = (
                self.settings_path.parent / f"{self.settings_path.name}.backup.{timestamp}"
            )

            # Create backup
            shutil.copy2(self.settings_path, backup_path)

            # Store backup path
            self.backup_path = backup_path

            # Save session state
            self.save_session_state()

            return (True, backup_path)

        except PermissionError as e:
            print(f"Permission error creating backup: {e}")
            return (False, None)
        except Exception as e:
            print(f"Error creating backup: {e}")
            return (False, None)

    def restore_backup(self) -> bool:
        """Restore settings.json from backup.

        Restores the settings file and cleans up the backup.

        Returns:
            True if restore successful, False otherwise
        """
        try:
            # Check if we have a backup path
            if not self.backup_path:
                # Try to load from session state
                if not self.load_session_state():
                    return False

                if not self.backup_path:
                    return False

            # Check if backup exists
            if not self.backup_path.exists():
                print(f"Backup file not found: {self.backup_path}")
                return False

            # Restore from backup
            shutil.copy2(self.backup_path, self.settings_path)

            # Remove backup file
            self.backup_path.unlink()

            # Cleanup session state
            self.cleanup_session_state()

            return True

        except PermissionError as e:
            print(f"Permission error restoring backup: {e}")
            return False
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False

    def save_session_state(self) -> bool:
        """Persist backup information to session state file.

        Saves backup path to JSON file for recovery.

        Returns:
            True if save successful, False otherwise
        """
        try:
            # Ensure session state directory exists
            self.session_state_dir.mkdir(parents=True, exist_ok=True)

            # Prepare state data
            state_data = {
                "session_id": self.session_id,
                "backup_path": str(self.backup_path) if self.backup_path else None,
                "settings_path": str(self.settings_path),
                "timestamp": int(time.time()),
            }

            # Write to session state file
            with open(self.session_state_file, "w") as f:
                json.dump(state_data, f, indent=2)

            return True

        except PermissionError as e:
            print(f"Permission error saving session state: {e}")
            return False
        except Exception as e:
            print(f"Error saving session state: {e}")
            return False

    def load_session_state(self) -> bool:
        """Load backup information from session state file.

        Recovers backup path from saved JSON file.

        Returns:
            True if load successful, False otherwise
        """
        try:
            # Check if session state file exists
            if not self.session_state_file.exists():
                return False

            # Read session state
            with open(self.session_state_file) as f:
                state_data = json.load(f)

            # Validate state data
            if not isinstance(state_data, dict):
                return False

            # Extract backup path
            backup_path_str = state_data.get("backup_path")
            if backup_path_str:
                self.backup_path = Path(backup_path_str)

            return True

        except json.JSONDecodeError as e:
            print(f"Invalid session state file: {e}")
            return False
        except Exception as e:
            print(f"Error loading session state: {e}")
            return False

    def cleanup_session_state(self) -> bool:
        """Remove session state file.

        Cleans up the session state file after successful restore.

        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            if self.session_state_file.exists():
                self.session_state_file.unlink()
            return True
        except Exception as e:
            print(f"Error cleaning up session state: {e}")
            return False
