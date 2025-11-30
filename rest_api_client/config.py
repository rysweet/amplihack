"""Configuration dataclasses for the REST API client.

Provides structured configuration options for client behavior.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        max_delay: Maximum delay between retries in seconds (default: 60.0)
        exponential_base: Base for exponential backoff calculation (default: 2)
        jitter: Random jitter range in seconds (default: 0.1)
        retry_on_status_codes: Status codes that trigger retry (default: 429, 503, 504)
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: int = 2
    jitter: float = 0.1
    retry_on_status_codes: set = field(default_factory=lambda: {429, 503, 504})

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if self.max_delay <= 0:
            raise ValueError("max_delay must be positive")
        if self.exponential_base < 1:
            raise ValueError("exponential_base must be at least 1")
        if self.jitter < 0:
            raise ValueError("jitter must be non-negative")


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting.

    Attributes:
        max_tokens: Maximum tokens in the bucket (default: 10)
        refill_rate: Tokens added per second (default: 1.0)
        initial_tokens: Initial tokens in bucket (default: max_tokens)
        respect_retry_after: Honor Retry-After headers (default: True)
    """

    max_tokens: int = 10
    refill_rate: float = 1.0
    initial_tokens: int | None = None
    respect_retry_after: bool = True

    def __post_init__(self) -> None:
        """Set defaults and validate after initialization."""
        if self.initial_tokens is None:
            self.initial_tokens = self.max_tokens

        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if self.refill_rate <= 0:
            raise ValueError("refill_rate must be positive")
        if self.initial_tokens < 0:
            raise ValueError("initial_tokens must be non-negative")
        if self.initial_tokens > self.max_tokens:
            raise ValueError("initial_tokens cannot exceed max_tokens")


@dataclass
class ClientConfig:
    """Main configuration for the API client.

    Attributes:
        base_url: Base URL for all API requests
        timeout: Default timeout in seconds (default: 30.0)
        headers: Default headers for all requests
        verify_ssl: Whether to verify SSL certificates (default: True)
        retry_config: Retry behavior configuration
        rate_limit_config: Rate limiting configuration
        enable_logging: Whether to enable request logging (default: True)
        log_level: Logging level (default: "INFO")
    """

    base_url: str
    timeout: float = 30.0
    headers: dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    rate_limit_config: RateLimitConfig = field(default_factory=RateLimitConfig)
    enable_logging: bool = True
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        """Validate and normalize configuration."""
        if not self.base_url:
            raise ValueError("base_url is required")

        # Ensure base_url doesn't end with /
        self.base_url = self.base_url.rstrip("/")

        if self.timeout <= 0:
            raise ValueError("timeout must be positive")

        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_log_levels:
            raise ValueError(f"Invalid log_level: {self.log_level}")
        self.log_level = self.log_level.upper()

    def with_defaults(self, **kwargs: Any) -> "ClientConfig":
        """Create a new config with updated values.

        Args:
            **kwargs: Values to override

        Returns:
            New ClientConfig instance with updated values
        """
        # Get current values as dict
        config_dict = {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "headers": self.headers.copy(),
            "verify_ssl": self.verify_ssl,
            "retry_config": self.retry_config,
            "rate_limit_config": self.rate_limit_config,
            "enable_logging": self.enable_logging,
            "log_level": self.log_level,
        }

        # Update with provided values
        config_dict.update(kwargs)

        return ClientConfig(**config_dict)
