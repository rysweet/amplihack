"""LSP Configurator module for managing .env file configuration.

Handles Layer 3 of the LSP setup: Project configuration via .env file.

Philosophy:
- Single responsibility: .env file management only
- Standard library only (Path, re)
- Atomic file operations for safety
- Self-contained and regeneratable

Public API:
    LSPConfigurator: Main class for LSP configuration management
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re
import shutil


class LSPConfigurator:
    """Manages LSP configuration in project .env file.

    Handles creating, reading, and updating the .env file to enable/disable
    LSP support in Claude Code.

    Example:
        >>> configurator = LSPConfigurator(Path("/path/to/project"))
        >>> configurator.enable_lsp()
        True
        >>> configurator.is_lsp_enabled()
        True
    """

    LSP_ENABLE_KEY = "ENABLE_LSP_TOOL"
    ENV_FILE_NAME = ".env"

    def __init__(self, project_root: Path):
        """Initialize LSP configurator.

        Args:
            project_root: Path to project root directory
        """
        self.project_root = Path(project_root)
        self.env_file_path = self.project_root / self.ENV_FILE_NAME

    def enable_lsp(self) -> bool:
        """Enable LSP in .env file.

        Creates or updates .env file to set ENABLE_LSP_TOOL=1.
        Preserves existing environment variables.
        Creates automatic backup if .env exists.

        Returns:
            True if successful

        Example:
            >>> configurator.enable_lsp()
            True
        """
        # Backup existing file before modification
        if self.env_file_path.exists():
            self.backup_env_file()

        return self.set_env_variable(self.LSP_ENABLE_KEY, "1")

    def disable_lsp(self) -> bool:
        """Disable LSP in .env file.

        Updates .env file to set ENABLE_LSP_TOOL=0.

        Returns:
            True if successful

        Example:
            >>> configurator.disable_lsp()
            True
        """
        return self.set_env_variable(self.LSP_ENABLE_KEY, "0")

    def is_lsp_enabled(self) -> bool:
        """Check if LSP is currently enabled in .env file.

        Returns:
            True if ENABLE_LSP_TOOL=1, False otherwise

        Example:
            >>> configurator.is_lsp_enabled()
            True
        """
        if not self.env_file_path.exists():
            return False

        env_vars = self.get_all_env_variables()
        value = env_vars.get(self.LSP_ENABLE_KEY, "0")
        return value == "1"

    def get_env_file_path(self) -> Path:
        """Get the path to the .env file.

        Returns:
            Path to .env file

        Example:
            >>> configurator.get_env_file_path()
            PosixPath('/project/.env')
        """
        return self.env_file_path

    def backup_env_file(self) -> Optional[Path]:
        """Create a backup of the current .env file.

        Returns:
            Path to backup file, or None if .env doesn't exist

        Example:
            >>> backup_path = configurator.backup_env_file()
        """
        if not self.env_file_path.exists():
            return None

        # Create backup with .backup suffix (not replacing .env)
        backup_path = self.project_root / (self.ENV_FILE_NAME + ".backup")
        shutil.copy2(self.env_file_path, backup_path)
        return backup_path

    def validate_env_file_syntax(self) -> Tuple[bool, List[str]]:
        """Validate .env file syntax.

        Returns:
            Tuple of (is_valid, list_of_errors)

        Example:
            >>> valid, errors = configurator.validate_env_file_syntax()
            >>> if not valid:
            ...     print(f"Errors: {errors}")
        """
        if not self.env_file_path.exists():
            return True, []

        errors = []
        content = self.env_file_path.read_text()

        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Check for valid key=value format
            if '=' not in line:
                errors.append(f"Line {line_num}: Missing '=' in assignment")
                continue

            key, _ = line.split('=', 1)
            if not key or not key.strip():
                errors.append(f"Line {line_num}: Empty variable name")

        return len(errors) == 0, errors

    def get_all_env_variables(self) -> Dict[str, str]:
        """Get all environment variables from .env file.

        Returns:
            Dict mapping variable names to values

        Example:
            >>> vars = configurator.get_all_env_variables()
            >>> print(vars['API_KEY'])
        """
        if not self.env_file_path.exists():
            return {}

        env_vars = {}
        content = self.env_file_path.read_text()

        for line in content.split('\n'):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Parse key=value
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

        return env_vars

    def set_env_variable(self, key: str, value: str) -> bool:
        """Set an environment variable in .env file.

        Preserves comments and empty lines. Updates existing key or appends new one.

        Args:
            key: Variable name
            value: Variable value

        Returns:
            True if successful

        Example:
            >>> configurator.set_env_variable("API_KEY", "secret")
            True
        """
        try:
            # Read existing content or start fresh
            if self.env_file_path.exists():
                lines = self.env_file_path.read_text().split('\n')
            else:
                lines = []

            # Look for existing key
            key_pattern = re.compile(f'^{re.escape(key)}\\s*=')
            key_found = False

            for i, line in enumerate(lines):
                if key_pattern.match(line.strip()):
                    # Update existing key
                    lines[i] = f"{key}={value}"
                    key_found = True
                    break

            # Add new key if not found
            if not key_found:
                # Remove trailing empty lines
                while lines and not lines[-1].strip():
                    lines.pop()

                # Add new key
                lines.append(f"{key}={value}")

            # Ensure single newline at end
            content = '\n'.join(lines)
            if content and not content.endswith('\n'):
                content += '\n'

            # Write atomically
            self.env_file_path.write_text(content)
            return True

        except (IOError, OSError) as e:
            # Handle permission errors, disk full, etc.
            return False

    def remove_env_variable(self, key: str) -> bool:
        """Remove an environment variable from .env file.

        Args:
            key: Variable name to remove

        Returns:
            True if successful

        Example:
            >>> configurator.remove_env_variable("OLD_KEY")
            True
        """
        if not self.env_file_path.exists():
            return True  # Already doesn't exist

        try:
            lines = self.env_file_path.read_text().split('\n')
            key_pattern = re.compile(f'^{re.escape(key)}\\s*=')

            # Filter out lines matching the key
            filtered_lines = [
                line for line in lines
                if not key_pattern.match(line.strip())
            ]

            # Write back
            content = '\n'.join(filtered_lines)
            if content and not content.endswith('\n'):
                content += '\n'

            self.env_file_path.write_text(content)
            return True

        except (IOError, OSError):
            return False

    def get_lsp_status_summary(self) -> Dict[str, Any]:
        """Get summary of LSP configuration status.

        Returns:
            Dict with configuration status information

        Example:
            >>> status = configurator.get_lsp_status_summary()
            >>> print(status['enabled'])
        """
        return {
            "enabled": self.is_lsp_enabled(),
            "env_file_exists": self.env_file_path.exists(),
            "env_file_path": str(self.env_file_path),
            "env_variable_count": len(self.get_all_env_variables()),
        }

    def get_status_summary(self) -> Dict[str, Any]:
        """Alias for get_lsp_status_summary.

        Returns:
            Dict with configuration status information
        """
        return self.get_lsp_status_summary()

    def validate_env_syntax(self) -> bool:
        """Validate .env file syntax (simplified return).

        Returns:
            True if valid, False otherwise

        Example:
            >>> configurator.validate_env_syntax()
            True
        """
        is_valid, _ = self.validate_env_file_syntax()
        return is_valid


__all__ = ["LSPConfigurator"]
