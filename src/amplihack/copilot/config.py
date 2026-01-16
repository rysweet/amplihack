"""Configuration management for Copilot CLI integration.

Provides unified configuration between Claude Code and Copilot CLI.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CopilotConfig:
    """Configuration for Copilot CLI integration."""

    # Agent sync settings
    auto_sync_agents: str = "ask"  # "always", "never", "ask"
    sync_on_startup: bool = True

    # Output formatting
    use_color: bool = True
    use_emoji: bool = True
    verbose: bool = False

    # Behavior settings
    allow_all_tools: bool = True
    add_root_dir: bool = True
    max_turns: int = 10

    # Paths
    agents_source: Path = field(default_factory=lambda: Path(".claude/agents"))
    agents_target: Path = field(default_factory=lambda: Path(".github/agents"))
    hooks_dir: Path = field(default_factory=lambda: Path(".github/hooks"))

    @classmethod
    def from_file(cls, config_path: Path) -> "CopilotConfig":
        """Load configuration from file.

        Args:
            config_path: Path to configuration file (JSON)

        Returns:
            Configuration instance
        """
        if not config_path.exists():
            return cls()

        try:
            with open(config_path) as f:
                data = json.load(f)

            # Convert path strings to Path objects
            if "agents_source" in data:
                data["agents_source"] = Path(data["agents_source"])
            if "agents_target" in data:
                data["agents_target"] = Path(data["agents_target"])
            if "hooks_dir" in data:
                data["hooks_dir"] = Path(data["hooks_dir"])

            return cls(**data)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            return cls()

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Configuration as dictionary
        """
        data = {
            "auto_sync_agents": self.auto_sync_agents,
            "sync_on_startup": self.sync_on_startup,
            "use_color": self.use_color,
            "use_emoji": self.use_emoji,
            "verbose": self.verbose,
            "allow_all_tools": self.allow_all_tools,
            "add_root_dir": self.add_root_dir,
            "max_turns": self.max_turns,
            "agents_source": str(self.agents_source),
            "agents_target": str(self.agents_target),
            "hooks_dir": str(self.hooks_dir),
        }
        return data

    def save(self, config_path: Path) -> None:
        """Save configuration to file.

        Args:
            config_path: Path to save configuration
        """
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def merge_with_amplihack_config(self, amplihack_config: dict[str, Any]) -> None:
        """Merge with amplihack configuration.

        Args:
            amplihack_config: Configuration from .claude/config.json
        """
        # Copy relevant amplihack settings
        if "copilot_auto_sync_agents" in amplihack_config:
            self.auto_sync_agents = amplihack_config["copilot_auto_sync_agents"]

        if "copilot_sync_on_startup" in amplihack_config:
            self.sync_on_startup = amplihack_config["copilot_sync_on_startup"]

        if "verbose" in amplihack_config:
            self.verbose = amplihack_config["verbose"]


def load_config(config_path: Path | None = None) -> CopilotConfig:
    """Load Copilot configuration with fallbacks.

    Tries to load from:
    1. Specified config_path
    2. .github/hooks/amplihack-hooks.json
    3. .claude/config.json (amplihack settings)
    4. Default configuration

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration instance
    """
    config = CopilotConfig()

    # Try specified path first
    if config_path and config_path.exists():
        config = CopilotConfig.from_file(config_path)

    # Try .github/hooks/amplihack-hooks.json
    github_config = Path(".github/hooks/amplihack-hooks.json")
    if github_config.exists():
        try:
            with open(github_config) as f:
                data = json.load(f)
            if "auto_sync_agents" in data:
                config.auto_sync_agents = data["auto_sync_agents"]
            if "sync_on_startup" in data:
                config.sync_on_startup = data["sync_on_startup"]
        except (json.JSONDecodeError, TypeError):
            pass

    # Try .claude/config.json (amplihack settings)
    amplihack_config = Path(".claude/config.json")
    if amplihack_config.exists():
        try:
            with open(amplihack_config) as f:
                data = json.load(f)
            config.merge_with_amplihack_config(data)
        except (json.JSONDecodeError, TypeError):
            pass

    return config


def save_preference(key: str, value: Any, config_path: Path | None = None) -> None:
    """Save a single preference value.

    Args:
        key: Configuration key
        value: Configuration value
        config_path: Path to configuration file (defaults to .github/hooks/amplihack-hooks.json)
    """
    if config_path is None:
        config_path = Path(".github/hooks/amplihack-hooks.json")

    # Load existing config
    config = load_config(config_path)

    # Update value
    if hasattr(config, key):
        setattr(config, key, value)
        config.save(config_path)
    else:
        raise ValueError(f"Unknown configuration key: {key}")


__all__ = ["CopilotConfig", "load_config", "save_preference"]
