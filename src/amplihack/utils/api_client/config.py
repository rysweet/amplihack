"""Configuration for REST API client.

Philosophy:
- Frozen dataclass for immutable configuration
- Sensible defaults with validation
- Environment variable support for deployment flexibility

Public API:
    APIClientConfig: Main configuration dataclass
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .exceptions import ConfigurationError


@dataclass(frozen=True)
class APIClientConfig:
    """Immutable configuration for APIClient.

    All configuration values are validated at construction time.
    Use from_env() to load configuration from environment variables.

    Attributes:
        base_url: Base URL for API requests (required).
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        backoff_base: Base delay for exponential backoff in seconds.
        backoff_max: Maximum delay between retries in seconds.
        backoff_jitter: Jitter factor (0.0-1.0) to randomize delays.
        verify_ssl: Whether to verify SSL certificates.
        ca_bundle: Path to CA bundle file (overrides verify_ssl).
        default_headers: Headers to include in all requests.

    Example:
        >>> config = APIClientConfig(
        ...     base_url="https://api.example.com",
        ...     timeout=60.0,
        ...     max_retries=5,
        ... )
        >>> config.base_url
        'https://api.example.com'
    """

    base_url: str
    timeout: float = 30.0
    max_retries: int = 3
    backoff_base: float = 0.5
    backoff_max: float = 60.0
    backoff_jitter: float = 0.25
    verify_ssl: bool = True
    ca_bundle: str | None = None
    default_headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration values after initialization."""
        # Validate base_url
        if not self.base_url:
            raise ConfigurationError("base_url is required", field="base_url")

        parsed = urlparse(self.base_url)
        if not parsed.scheme or not parsed.netloc:
            raise ConfigurationError(f"Invalid URL format: {self.base_url}", field="base_url")
        if parsed.scheme not in ("http", "https"):
            raise ConfigurationError(
                f"URL scheme must be http or https, got: {parsed.scheme}",
                field="base_url",
            )

        # Validate timeout
        if self.timeout <= 0:
            raise ConfigurationError(
                f"timeout must be positive, got: {self.timeout}", field="timeout"
            )

        # Validate max_retries
        if self.max_retries < 0:
            raise ConfigurationError(
                f"max_retries must be non-negative, got: {self.max_retries}",
                field="max_retries",
            )

        # Validate backoff_base
        if self.backoff_base <= 0:
            raise ConfigurationError(
                f"backoff_base must be positive, got: {self.backoff_base}",
                field="backoff_base",
            )

        # Validate backoff_max
        if self.backoff_max <= 0:
            raise ConfigurationError(
                f"backoff_max must be positive, got: {self.backoff_max}",
                field="backoff_max",
            )
        if self.backoff_max < self.backoff_base:
            raise ConfigurationError(
                f"backoff_max ({self.backoff_max}) must be >= backoff_base ({self.backoff_base})",
                field="backoff_max",
            )

        # Validate backoff_jitter
        if not 0.0 <= self.backoff_jitter <= 1.0:
            raise ConfigurationError(
                f"backoff_jitter must be between 0.0 and 1.0, got: {self.backoff_jitter}",
                field="backoff_jitter",
            )

    @classmethod
    def from_env(
        cls,
        prefix: str = "API_CLIENT",
        base_url: str | None = None,
    ) -> APIClientConfig:
        """Create configuration from environment variables.

        Environment variables are named {prefix}_{FIELD} in uppercase.

        Args:
            prefix: Prefix for environment variable names.
            base_url: Override for base_url (falls back to {prefix}_BASE_URL).

        Returns:
            APIClientConfig with values from environment.

        Example:
            >>> # With API_CLIENT_BASE_URL=https://api.example.com
            >>> # and API_CLIENT_TIMEOUT=60
            >>> config = APIClientConfig.from_env()
            >>> config.base_url
            'https://api.example.com'
            >>> config.timeout
            60.0
        """
        env_base_url = base_url or os.environ.get(f"{prefix}_BASE_URL", "")
        if not env_base_url:
            raise ConfigurationError(
                f"Missing required environment variable: {prefix}_BASE_URL or base_url argument",
                field="base_url",
            )

        def get_float(name: str, default: float) -> float:
            value = os.environ.get(f"{prefix}_{name}")
            if value is None:
                return default
            try:
                return float(value)
            except ValueError:
                raise ConfigurationError(
                    f"Invalid float value for {prefix}_{name}: {value}",
                    field=name.lower(),
                )

        def get_int(name: str, default: int) -> int:
            value = os.environ.get(f"{prefix}_{name}")
            if value is None:
                return default
            try:
                return int(value)
            except ValueError:
                raise ConfigurationError(
                    f"Invalid integer value for {prefix}_{name}: {value}",
                    field=name.lower(),
                )

        def get_bool(name: str, default: bool) -> bool:
            value = os.environ.get(f"{prefix}_{name}")
            if value is None:
                return default
            return value.lower() in ("true", "1", "yes")

        def get_optional_str(name: str) -> str | None:
            return os.environ.get(f"{prefix}_{name}") or None

        return cls(
            base_url=env_base_url,
            timeout=get_float("TIMEOUT", 30.0),
            max_retries=get_int("MAX_RETRIES", 3),
            backoff_base=get_float("BACKOFF_BASE", 0.5),
            backoff_max=get_float("BACKOFF_MAX", 60.0),
            backoff_jitter=get_float("BACKOFF_JITTER", 0.25),
            verify_ssl=get_bool("VERIFY_SSL", True),
            ca_bundle=get_optional_str("CA_BUNDLE"),
        )


__all__ = ["APIClientConfig"]
