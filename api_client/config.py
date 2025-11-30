"""Configuration for the API client."""

import os
import urllib.parse
from dataclasses import dataclass


@dataclass
class ClientConfig:
    """Configuration settings for APIClient.

    Attributes:
        base_url: The base URL for the API (required)
        timeout: Request timeout in seconds (default: 30.0)
        max_retries: Maximum number of retries for failed requests (default: 3)
        api_key: Optional API key for Bearer authentication (can be env var reference)
        api_key_env: Optional environment variable name to read API key from
    """

    base_url: str
    timeout: float = 30.0
    max_retries: int = 3
    api_key: str | None = None
    api_key_env: str | None = None
    disable_ssrf_protection: bool = False  # For testing only

    def __post_init__(self):
        """Validate and normalize configuration."""
        # Normalize the base_url by removing trailing slash
        if self.base_url.endswith("/"):
            self.base_url = self.base_url.rstrip("/")

        # Validate base_url is a valid URL
        parsed = urllib.parse.urlparse(self.base_url)
        if not parsed.scheme:
            raise ValueError("Invalid base_url: missing scheme (http/https)")
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"Invalid base_url scheme: {parsed.scheme}. Only http and https are allowed."
            )
        if not parsed.netloc:
            raise ValueError("Invalid base_url: missing hostname")

        # Validate timeout
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}")

        # Validate max_retries
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be non-negative, got {self.max_retries}")

        # Load API key from environment if specified
        if self.api_key_env and not self.api_key:
            self.api_key = os.environ.get(self.api_key_env)
            if not self.api_key:
                # Don't raise error, just leave it None (key might be optional)
                pass

    def get_masked_api_key(self) -> str | None:
        """Get a masked version of the API key for logging/errors.

        Returns:
            Masked API key like 'sk-...abc123' or None if no key
        """
        if not self.api_key:
            return None

        if len(self.api_key) <= 8:
            # Very short key, just show first 2 chars
            return f"{self.api_key[:2]}..."
        # Show first 3 and last 3 characters
        return f"{self.api_key[:3]}...{self.api_key[-3:]}"
