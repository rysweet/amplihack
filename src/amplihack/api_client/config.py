"""Configuration for REST API client.

Philosophy: Sensible defaults, easy to override, validated on creation.
"""

from dataclasses import dataclass, field


@dataclass
class RestApiConfig:
    """Configuration for REST API client.

    Args:
        base_url: Base URL for API (must include http:// or https://)
        timeout: Request timeout in seconds (default: 30.0)
        max_retries: Maximum retry attempts (default: 3)
        retry_backoff: Base backoff time in seconds (default: 1.0)
        verify_ssl: Verify SSL certificates (default: True)
        headers: Default headers to include in all requests

    Raises:
        ValidationError: If configuration is invalid
    """

    base_url: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_backoff: float = 1.0
    verify_ssl: bool = True
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration after initialization."""
        from .exceptions import ValidationError

        if not self.base_url.startswith(("http://", "https://")):
            raise ValidationError("base_url must start with http:// or https://")

        if self.timeout <= 0:
            raise ValidationError("timeout must be positive")

        if self.max_retries < 0:
            raise ValidationError("max_retries must be non-negative")

        if self.retry_backoff < 0:
            raise ValidationError("retry_backoff must be non-negative")


__all__ = ["RestApiConfig"]
