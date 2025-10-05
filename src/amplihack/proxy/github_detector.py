"""GitHub Copilot endpoint detection and validation."""

import re
from typing import Dict, Optional
from urllib.parse import urlparse


class GitHubEndpointDetector:
    """Detects and validates GitHub Copilot API endpoints."""

    # GitHub Copilot API endpoints
    GITHUB_COPILOT_ENDPOINTS = {
        "https://api.github.com/copilot",
        "https://copilot-proxy.githubusercontent.com",
    }

    # Compile regex patterns once at class level for performance
    _GITHUB_API_REGEX = re.compile(r"^https://api\.github\.com/copilot")
    _GITHUB_COPILOT_REGEX = re.compile(r"^https://copilot-proxy\.githubusercontent\.com")

    def is_github_endpoint(self, endpoint: Optional[str], config: Dict[str, str]) -> bool:
        """Check if endpoint is a GitHub Copilot API endpoint.

        Args:
            endpoint: Endpoint URL to check
            config: Configuration dictionary

        Returns:
            True if GitHub Copilot endpoint detected, False otherwise.
        """
        if not endpoint:
            # Check for GitHub configuration indicators
            return self._has_github_config_indicators(config)

        return self._validate_github_endpoint_format(endpoint)

    def get_endpoint_type(self, endpoint: Optional[str], config: Dict[str, str]) -> str:
        """Get endpoint type (github_copilot or openai).

        Args:
            endpoint: Endpoint URL to check
            config: Configuration dictionary

        Returns:
            "github_copilot" or "openai"
        """
        if self.is_github_endpoint(endpoint, config):
            return "github_copilot"
        return "openai"

    def validate_github_endpoint(self, endpoint: str) -> bool:
        """Validate GitHub Copilot endpoint URL format.

        Args:
            endpoint: Endpoint URL to validate

        Returns:
            True if valid GitHub endpoint format, False otherwise.
        """
        return self._validate_github_endpoint_format(endpoint)

    def _has_github_config_indicators(self, config: Dict[str, str]) -> bool:
        """Check for GitHub configuration indicators.

        Args:
            config: Configuration dictionary

        Returns:
            True if GitHub indicators found, False otherwise.
        """
        # Check for GitHub-specific configuration keys
        github_indicators = [
            "GITHUB_TOKEN",
            "GITHUB_COPILOT_ENABLED",
            "GITHUB_COPILOT_MODEL",
        ]

        for indicator in github_indicators:
            if config.get(indicator):
                return True

        # Check for explicit proxy type setting
        proxy_type = config.get("PROXY_TYPE", "").lower()
        return proxy_type in ("github", "github_copilot", "copilot")

    def _validate_github_endpoint_format(self, endpoint: str) -> bool:
        """Validate GitHub endpoint URL format.

        Args:
            endpoint: Endpoint URL

        Returns:
            True if valid GitHub format, False otherwise.
        """
        if not endpoint:
            return False

        try:
            parsed = urlparse(endpoint)

            # Must be HTTPS
            if parsed.scheme != "https":
                return False

            # Check against known GitHub Copilot endpoints
            endpoint_lower = endpoint.lower().rstrip("/")

            return bool(
                self._GITHUB_API_REGEX.match(endpoint_lower)
                or self._GITHUB_COPILOT_REGEX.match(endpoint_lower)
                or endpoint_lower in {ep.lower() for ep in self.GITHUB_COPILOT_ENDPOINTS}
            )

        except Exception:
            return False

    def get_canonical_endpoint(self, endpoint: Optional[str]) -> str:
        """Get canonical GitHub Copilot endpoint.

        Args:
            endpoint: Original endpoint or None

        Returns:
            Canonical GitHub Copilot API endpoint.
        """
        if endpoint and self.validate_github_endpoint(endpoint):
            return endpoint

        # Default to primary GitHub Copilot API
        return "https://api.github.com/copilot"

    def supports_streaming(self, endpoint: str) -> bool:
        """Check if endpoint supports streaming responses.

        Args:
            endpoint: GitHub endpoint URL

        Returns:
            True if streaming is supported, False otherwise.
        """
        # GitHub Copilot API supports streaming
        return self.validate_github_endpoint(endpoint)

    def get_rate_limit_info(self, endpoint: str) -> Dict[str, int]:
        """Get rate limit information for GitHub endpoint.

        Args:
            endpoint: GitHub endpoint URL

        Returns:
            Dictionary with rate limit information.
        """
        if not self.validate_github_endpoint(endpoint):
            return {}

        # GitHub Copilot rate limits (these may vary)
        return {
            "requests_per_minute": 60,
            "requests_per_hour": 5000,
            "tokens_per_minute": 50000,
        }
