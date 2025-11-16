"""MCP configuration management for Serena integration.

This module handles reading, writing, and modifying Claude Desktop's
MCP server configuration to add/remove the Serena server.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .detector import SerenaDetector
from .errors import ConfigurationError


@dataclass
class SerenaConfig:
    """Serena MCP server configuration.

    Attributes:
        name: Server name (always "serena")
        command: Command to execute (always "uvx")
        args: Command arguments for launching Serena
        env: Environment variables (empty dict by default)
    """

    name: str = "serena"
    command: str = "uvx"
    args: list[str] = None
    env: Dict[str, str] = None

    def __post_init__(self):
        if self.args is None:
            self.args = [
                "--from",
                "git+https://github.com/oraios/serena",
                "serena",
            ]
        if self.env is None:
            self.env = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for JSON serialization.

        Returns:
            Dictionary with command, args, and env keys
        """
        return {
            "command": self.command,
            "args": self.args,
            "env": self.env,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SerenaConfig":
        """Create SerenaConfig from dictionary.

        Args:
            data: Dictionary with command, args, and env keys

        Returns:
            SerenaConfig instance
        """
        return cls(
            name="serena",
            command=data.get("command", "uvx"),
            args=data.get("args", []),
            env=data.get("env", {}),
        )


class SerenaConfigurator:
    """Manages Serena MCP server configuration."""

    def __init__(self, detector: Optional[SerenaDetector] = None):
        """Initialize configurator.

        Args:
            detector: SerenaDetector instance (creates new one if not provided)
        """
        self.detector = detector or SerenaDetector()

    def is_configured(self) -> bool:
        """Check if Serena is already configured in MCP servers.

        Returns:
            True if Serena is present in mcpServers configuration

        Raises:
            ConfigurationError: If config file exists but cannot be read
        """
        config_path = self.detector.get_mcp_config_path()
        if not config_path or not config_path.exists():
            return False

        try:
            config = self._read_config(config_path)
            mcp_servers = config.get("mcpServers", {})
            return "serena" in mcp_servers
        except Exception as e:
            raise ConfigurationError(
                f"Failed to read configuration file: {e}",
                "Ensure the file is valid JSON and you have read permissions.",
            )

    def add_to_mcp_servers(self) -> bool:
        """Add Serena configuration to MCP servers.

        Returns:
            True if configuration was added, False if already present

        Raises:
            ConfigurationError: If configuration cannot be written
        """
        config_path = self.detector.get_mcp_config_path()
        if not config_path:
            raise ConfigurationError(
                "Cannot determine MCP configuration path",
                "Ensure Claude Desktop is installed on your system.",
            )

        # Read existing config or create new one
        if config_path.exists():
            try:
                config = self._read_config(config_path)
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to read existing configuration: {e}",
                    "Check that the file is valid JSON.",
                )
        else:
            config = {}

        # Check if already configured
        mcp_servers = config.setdefault("mcpServers", {})
        if "serena" in mcp_servers:
            return False

        # Add Serena configuration
        serena_config = SerenaConfig()
        mcp_servers["serena"] = serena_config.to_dict()

        # Write updated configuration
        try:
            self._write_config(config_path, config)
            return True
        except Exception as e:
            raise ConfigurationError(
                f"Failed to write configuration: {e}",
                "Ensure you have write permissions and Claude Desktop is not running.",
            )

    def remove_from_mcp_servers(self) -> bool:
        """Remove Serena configuration from MCP servers.

        Returns:
            True if configuration was removed, False if not present

        Raises:
            ConfigurationError: If configuration cannot be written
        """
        config_path = self.detector.get_mcp_config_path()
        if not config_path or not config_path.exists():
            return False

        try:
            config = self._read_config(config_path)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to read configuration: {e}",
                "Check that the file is valid JSON.",
            )

        mcp_servers = config.get("mcpServers", {})
        if "serena" not in mcp_servers:
            return False

        # Remove Serena configuration
        del mcp_servers["serena"]

        # Write updated configuration
        try:
            self._write_config(config_path, config)
            return True
        except Exception as e:
            raise ConfigurationError(
                f"Failed to write configuration: {e}",
                "Ensure you have write permissions and Claude Desktop is not running.",
            )

    def get_current_config(self) -> Optional[SerenaConfig]:
        """Get the current Serena configuration if it exists.

        Returns:
            SerenaConfig if configured, None otherwise

        Raises:
            ConfigurationError: If config file exists but cannot be read
        """
        config_path = self.detector.get_mcp_config_path()
        if not config_path or not config_path.exists():
            return None

        try:
            config = self._read_config(config_path)
            mcp_servers = config.get("mcpServers", {})
            serena_data = mcp_servers.get("serena")
            if serena_data:
                return SerenaConfig.from_dict(serena_data)
            return None
        except Exception as e:
            raise ConfigurationError(
                f"Failed to read configuration: {e}",
                "Ensure the file is valid JSON and you have read permissions.",
            )

    def export_to_claude_desktop(self, output_path: Path) -> bool:
        """Export Serena configuration snippet for manual setup.

        Args:
            output_path: Path where to write the configuration snippet

        Returns:
            True if export was successful

        Raises:
            ConfigurationError: If export fails
        """
        serena_config = SerenaConfig()
        export_data = {
            "mcpServers": {
                "serena": serena_config.to_dict(),
            }
        }

        try:
            self._write_config(output_path, export_data)
            return True
        except Exception as e:
            raise ConfigurationError(
                f"Failed to export configuration: {e}",
                "Ensure you have write permissions to the target directory.",
            )

    def _read_config(self, config_path: Path) -> Dict[str, Any]:
        """Read and parse MCP configuration file.

        Args:
            config_path: Path to configuration file

        Returns:
            Parsed configuration dictionary

        Raises:
            Various exceptions on read/parse errors
        """
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)

    def _write_config(self, config_path: Path, config: Dict[str, Any]) -> None:
        """Write MCP configuration file.

        Args:
            config_path: Path to configuration file
            config: Configuration dictionary to write

        Raises:
            Various exceptions on write errors
        """
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write with pretty formatting
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.write("\n")  # Add trailing newline
