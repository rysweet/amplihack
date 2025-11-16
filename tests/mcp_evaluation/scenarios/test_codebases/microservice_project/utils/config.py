"""Configuration management."""

from typing import Any, Dict
import os


class Config:
    """Application configuration.

    Loads configuration from environment variables and provides defaults.
    """

    def __init__(self):
        """Initialize configuration."""
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///app.db")
        self.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Configuration as dict
        """
        return {
            "debug": self.debug,
            "host": self.host,
            "port": self.port,
            "database_url": self.database_url,
            "secret_key": "***" if not self.debug else self.secret_key,
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return getattr(self, key, default)
