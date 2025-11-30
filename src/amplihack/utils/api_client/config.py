"""
Configuration dataclasses for retry and rate limiting.

Philosophy:
- Immutable configurations (frozen=True)
- Sensible defaults
- Security bounds enforced
- Standard library only
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry logic with exponential backoff.

    This configuration controls how the client retries failed requests.
    The retry logic uses exponential backoff to avoid overwhelming
    servers with rapid retries.

    Attributes:
        max_retries: Maximum number of retry attempts (0-10)
        base_delay: Initial delay in seconds before first retry (0.1-60.0)
        max_delay: Maximum delay between retries in seconds (1.0-300.0)
        exponential_base: Multiplier for exponential backoff (1.0-3.0, where 1.0=linear)
        retry_on_status: List of HTTP status codes to retry on (default: [500, 502, 503, 504])

    Example:
        >>> config = RetryConfig(
        ...     max_retries=3,
        ...     base_delay=1.0,
        ...     max_delay=60.0,
        ...     exponential_base=2.0,
        ...     retry_on_status=[500, 502, 503, 504]
        ... )
        >>> # Delays will be: 1s, 2s, 4s

    Default Configuration:
        - max_retries: 3
        - base_delay: 1.0 seconds
        - max_delay: 60.0 seconds
        - exponential_base: 2.0
        - retry_on_status: [500, 502, 503, 504]
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    retry_on_status: list[int] | None = None

    def __post_init__(self):
        """Set defaults and validate configuration values.

        Raises:
            ValueError: If any configuration value is outside allowed range
        """
        # Set default retry_on_status using object.__setattr__ since frozen=True
        if self.retry_on_status is None:
            object.__setattr__(self, "retry_on_status", [500, 502, 503, 504])

        # Validate max_retries
        if not 0 <= self.max_retries <= 10:
            raise ValueError(f"max_retries must be between 0 and 10, got {self.max_retries}")

        # Validate base_delay
        if not 0.1 <= self.base_delay <= 60.0:
            raise ValueError(
                f"base_delay must be between 0.1 and 60.0 seconds, got {self.base_delay}"
            )

        # Validate max_delay
        if not 1.0 <= self.max_delay <= 300.0:
            raise ValueError(
                f"max_delay must be between 1.0 and 300.0 seconds, got {self.max_delay}"
            )

        # Validate exponential_base
        # Allow 1.0 for linear backoff, 1.5-3.0 for exponential
        if not 1.0 <= self.exponential_base <= 3.0:
            raise ValueError(
                f"exponential_base must be between 1.0 and 3.0, got {self.exponential_base}"
            )

        # Validate that max_delay >= base_delay
        if self.max_delay < self.base_delay:
            raise ValueError(
                f"max_delay ({self.max_delay}) must be >= base_delay ({self.base_delay})"
            )


@dataclass(frozen=True)
class RateLimitConfig:
    """Configuration for rate limit handling.

    This configuration controls how the client handles API rate limits
    (HTTP 429 responses). It enforces maximum wait times to prevent
    indefinite blocking.

    Attributes:
        max_wait_time: Maximum time to wait for rate limit in seconds (1-600)
        respect_retry_after: Whether to use Retry-After header from response
        default_backoff: Default wait time when Retry-After not provided (1-600)

    Example:
        >>> config = RateLimitConfig(
        ...     max_wait_time=300.0,  # Wait up to 5 minutes
        ...     respect_retry_after=True,
        ...     default_backoff=60.0  # Wait 1 minute by default
        ... )

    Default Configuration:
        - max_wait_time: 300.0 seconds (5 minutes)
        - respect_retry_after: True
        - default_backoff: 60.0 seconds (1 minute)
    """

    max_wait_time: float = 300.0
    respect_retry_after: bool = True
    default_backoff: float = 60.0

    def __post_init__(self):
        """Validate configuration values are within safe bounds.

        Raises:
            ValueError: If max_wait_time or default_backoff is outside allowed range
        """
        # Validate max_wait_time
        if not 1.0 <= self.max_wait_time <= 600.0:
            raise ValueError(
                f"max_wait_time must be between 1.0 and 600.0 seconds, got {self.max_wait_time}"
            )

        # Validate default_backoff
        if not 1.0 <= self.default_backoff <= 600.0:
            raise ValueError(
                f"default_backoff must be between 1.0 and 600.0 seconds, got {self.default_backoff}"
            )


__all__ = [
    "RetryConfig",
    "RateLimitConfig",
]
