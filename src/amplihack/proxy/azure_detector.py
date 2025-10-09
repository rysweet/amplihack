"""Azure OpenAI endpoint detection and validation."""

import re
from typing import Dict, Optional
from urllib.parse import urlparse


class AzureEndpointDetector:
    """Detects and validates Azure OpenAI endpoints."""

    # Use __slots__ to reduce memory usage
    __slots__ = ("_azure_regex", "_cache_size", "_openai_regex", "_validation_cache")

    # Azure OpenAI endpoint patterns
    AZURE_PATTERNS = [
        r"https://.*\.openai\.azure\.com",
        r"https://.*\.openai\.azure\.us",
        r"https://.*\.openai\.azure\.cn",
    ]

    # OpenAI official patterns
    OPENAI_PATTERNS = [
        r"https://api\.openai\.com",
    ]

    def __init__(self):
        """Initialize Azure endpoint detector."""
        # Compile regex patterns once and cache them
        self._azure_regex = [re.compile(pattern) for pattern in self.AZURE_PATTERNS]
        self._openai_regex = [re.compile(pattern) for pattern in self.OPENAI_PATTERNS]

        # Cache for repeated validations - avoid regex on same URLs
        self._validation_cache = {}
        self._cache_size = 1000  # Limit cache size to prevent memory leaks

    def is_azure_endpoint(
        self, base_url: Optional[str] = None, config: Optional[Dict[str, str]] = None
    ) -> bool:
        """Check if endpoint is Azure OpenAI.

        Args:
            base_url: Base URL to check
            config: Configuration dictionary to check for Azure variables

        Returns:
            True if Azure endpoint detected, False otherwise
        """
        # Check explicit Azure configuration first
        if config and self._has_azure_config_vars(config):
            return True

        # Check URL patterns
        if base_url:
            return self._is_azure_url_pattern(base_url)

        return False

    def get_endpoint_type(
        self, base_url: Optional[str] = None, config: Optional[Dict[str, str]] = None
    ) -> str:
        """Get endpoint type (azure or openai).

        Args:
            base_url: Base URL to check
            config: Configuration dictionary

        Returns:
            "azure" or "openai"
        """
        if self.is_azure_endpoint(base_url, config):
            return "azure"
        return "openai"

    def validate_azure_endpoint(self, endpoint: str) -> bool:
        """Validate Azure endpoint URL format.

        Args:
            endpoint: Azure endpoint URL

        Returns:
            True if valid Azure endpoint format
        """
        if not endpoint:
            return False

        # Check cache first to avoid repeated regex operations
        if endpoint in self._validation_cache:
            return self._validation_cache[endpoint]

        # Must be HTTPS for security
        if not endpoint.startswith("https://"):
            result = False
        else:
            # Must match Azure patterns and pass additional security checks
            result = self._is_azure_url_pattern(endpoint) and self._validate_endpoint_security(
                endpoint
            )

        # Cache result (with size limit to prevent memory leaks)
        if len(self._validation_cache) >= self._cache_size:
            # Simple cache eviction - remove oldest entries (first 10% of cache)
            items_to_remove = list(self._validation_cache.keys())[: self._cache_size // 10]
            for key in items_to_remove:
                del self._validation_cache[key]

        self._validation_cache[endpoint] = result
        return result

    def extract_azure_resource_name(self, endpoint: str) -> Optional[str]:
        """Extract Azure resource name from endpoint URL.

        Args:
            endpoint: Azure endpoint URL

        Returns:
            Resource name if found, None otherwise
        """
        if not self.validate_azure_endpoint(endpoint):
            return None

        parsed = urlparse(endpoint)
        if parsed.hostname:
            # Extract from hostname like "myresource.openai.azure.com"
            parts = parsed.hostname.split(".")
            if len(parts) >= 4 and parts[-3:] == ["openai", "azure", "com"]:
                return parts[0]

        return None

    def _is_azure_url_pattern(self, url: str) -> bool:
        """Check if URL matches Azure patterns."""
        return any(regex.match(url) for regex in self._azure_regex)

    def _is_openai_url_pattern(self, url: str) -> bool:
        """Check if URL matches OpenAI patterns."""
        return any(regex.match(url) for regex in self._openai_regex)

    def _has_azure_config_vars(self, config: Dict[str, str]) -> bool:
        """Check if config has Azure-specific variables."""
        azure_vars = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_BASE_URL", "AZURE_OPENAI_API_KEY"]
        return any(var in config and config[var] for var in azure_vars)

    def _validate_endpoint_security(self, endpoint: str) -> bool:
        """Validate endpoint security requirements.

        Args:
            endpoint: Endpoint URL to validate

        Returns:
            True if endpoint meets security requirements.
        """
        try:
            parsed = urlparse(endpoint)

            # Must use HTTPS
            if parsed.scheme != "https":
                return False

            # Must have valid hostname
            if not parsed.hostname:
                return False

            # Hostname must not contain suspicious characters
            hostname = parsed.hostname.lower()
            if any(char in hostname for char in ["<", ">", '"', "'", "&"]):
                return False

            # Must be reasonable length
            if len(hostname) > 255 or len(endpoint) > 2048:
                return False

            # Additional Azure-specific security checks
            if "azure" in hostname:
                # Must be legitimate Azure domain
                valid_azure_domains = [
                    "openai.azure.com",
                    "openai.azure.us",
                    "openai.azure.cn",
                    "cognitive.microsoft.com",
                    "cognitiveservices.azure.com",
                ]

                if not any(hostname.endswith(domain) for domain in valid_azure_domains):
                    return False

            return True

        except Exception:
            return False
