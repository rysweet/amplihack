"""Security utilities for API client.

Philosophy: Block dangerous patterns, enforce safe defaults.
"""

import ipaddress
from urllib.parse import urlparse


class SecurityValidator:
    """Validates requests for security issues (SSRF, SSL, etc)."""

    # Private IP ranges to block for SSRF protection
    BLOCKED_CIDRS: set[str] = {
        "127.0.0.0/8",  # Loopback
        "10.0.0.0/8",  # Private Class A
        "172.16.0.0/12",  # Private Class B
        "192.168.0.0/16",  # Private Class C
        "169.254.0.0/16",  # Link-local
    }

    @classmethod
    def validate_url(cls, url: str, allow_private: bool = False) -> None:
        """Validate URL for security issues.

        Args:
            url: URL to validate
            allow_private: If True, allow private IPs (for testing)

        Raises:
            SecurityError: If URL fails security checks
        """
        from .exceptions import SecurityError

        parsed = urlparse(url)

        # Enforce HTTPS in production
        if not allow_private and parsed.scheme != "https":
            raise SecurityError(f"HTTPS required in production, got: {parsed.scheme}")

        # Block private IPs (SSRF protection)
        if not allow_private and parsed.hostname:
            try:
                ip = ipaddress.ip_address(parsed.hostname)
                for cidr in cls.BLOCKED_CIDRS:
                    if ip in ipaddress.ip_network(cidr):
                        raise SecurityError(
                            f"Private IP blocked for SSRF protection: {parsed.hostname}"
                        )
            except ValueError:
                # Not an IP address, allow (DNS resolution happens later)
                pass

    @classmethod
    def sanitize_headers(cls, headers: dict) -> dict:
        """Sanitize headers for logging (redact sensitive values).

        Args:
            headers: Headers dictionary

        Returns:
            Sanitized headers with redacted sensitive values
        """
        sensitive_keys = {"authorization", "api-key", "api_key", "token", "password"}
        sanitized = {}

        for key, value in headers.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value

        return sanitized


__all__ = ["SecurityValidator"]
