"""Proxy configuration parsing and validation."""

from pathlib import Path
from typing import Dict, Optional


class ProxyConfig:
    """Manages proxy configuration from .env files."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize proxy configuration.

        Args:
            config_path: Path to .env configuration file.
        """
        self.config_path = config_path
        self.config: Dict[str, str] = {}
        if config_path and config_path.exists():
            self._load_config()

    def _load_config(self) -> None:
        """Load configuration from .env file."""
        if not self.config_path or not self.config_path.exists():
            return

        with open(self.config_path) as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                # Parse key=value pairs
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    # Strip quotes but preserve any inline comments
                    value = value.strip()
                    # Remove outer quotes if they exist
                    if value.startswith('"') and '"' in value[1:]:
                        # Find the closing quote
                        end_quote = value.index('"', 1)
                        value = value[1:end_quote]
                    elif value.startswith("'") and "'" in value[1:]:
                        # Find the closing quote
                        end_quote = value.index("'", 1)
                        value = value[1:end_quote]
                    else:
                        # No quotes, strip any trailing comments if present
                        if "#" in value:
                            value = value.split("#")[0].strip()
                        value = value.strip('"').strip("'")
                    self.config[key] = value

    def validate(self) -> bool:
        """Validate required configuration values.

        Returns:
            True if configuration is valid, False otherwise.
        """
        # For proxy configuration, we need the OpenAI/Azure credentials, not Anthropic
        # ANTHROPIC_API_KEY is optional - only needed if you want to validate clients
        required_keys = ["OPENAI_API_KEY"]  # The actual API key for the backend
        for key in required_keys:
            if key not in self.config or not self.config[key]:
                print(f"Missing required configuration: {key}")
                return False
        return True

    def get(self, key: str, default: str = "") -> str:
        """Get configuration value.

        Args:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        return self.config.get(key, default)

    def to_env_dict(self) -> Dict[str, str]:
        """Convert configuration to environment variables dictionary.

        Returns:
            Dictionary of environment variables.
        """
        return self.config.copy()

    def save_to(self, target_path: Path) -> None:
        """Save configuration to a new .env file.

        Args:
            target_path: Path where to save the configuration.
        """
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w") as f:
            # Write all configuration values, properly handling quotes
            for key, value in self.config.items():
                # Remove any extra quotes that may have been added during parsing
                value = value.strip('"').strip("'")
                # Check if value needs quotes (contains spaces or special chars)
                if " " in value or "\t" in value or "\n" in value or "#" in value:
                    f.write(f'{key}="{value}"\n')
                else:
                    f.write(f"{key}={value}\n")
        print(f"Wrote {len(self.config)} configuration values to {target_path}")
