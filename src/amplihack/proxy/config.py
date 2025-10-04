"""Proxy configuration parsing and validation."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from .azure_detector import AzureEndpointDetector
from .azure_models import AzureModelMapper


class ProxyConfig:
    """Manages proxy configuration from .env files."""

    # Compile regex patterns once at class level for performance
    _API_VERSION_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    _API_KEY_REGEX = re.compile(r"[a-zA-Z0-9\-_]{20,}")
    _DEPLOYMENT_NAME_REGEX = re.compile(r"^[a-zA-Z0-9\-_]{1,64}$")

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize proxy configuration.

        Args:
            config_path: Path to .env configuration file.
        """
        self.config_path = config_path
        self.config: Dict[str, str] = {}
        self.validation_errors: List[str] = []

        if config_path and config_path.exists():
            self._load_config()

        # Load from environment variables (they take precedence)
        self._load_environment_variables()

        # Initialize Azure components
        self._azure_detector = AzureEndpointDetector()
        self._azure_mapper = AzureModelMapper(self.config)

    def _load_config(self) -> None:
        """Load configuration from .env file."""
        if not self.config_path or not self.config_path.exists():
            return

        # Read entire file at once for better I/O performance
        with open(self.config_path, "r") as f:
            content = f.read()

        # Process lines more efficiently
        for line in content.splitlines():
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            # Parse key=value pairs more efficiently
            eq_index = line.find("=")
            if eq_index > 0:  # Must have key and equals sign
                key = line[:eq_index].strip()
                value = line[eq_index + 1 :].strip()
                # Remove quotes more efficiently
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                self.config[key] = value

        # Reinitialize Azure mapper after loading config
        self._azure_mapper = AzureModelMapper(self.config)

    def _load_environment_variables(self) -> None:
        """Load environment variables that override file configuration."""
        # Define variables that can be loaded from environment
        env_vars = [
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "ANTHROPIC_API_KEY",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_BASE_URL",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_API_VERSION",
            "PROXY_TYPE",
            "PROXY_MODE",
            "PORT",
        ]

        # Add Azure deployment variables
        deployment_vars = [
            "AZURE_GPT4_DEPLOYMENT",
            "AZURE_GPT4_MINI_DEPLOYMENT",
            "AZURE_GPT4_TURBO_DEPLOYMENT",
            "AZURE_GPT35_DEPLOYMENT",
            "AZURE_BIG_MODEL_DEPLOYMENT",
            "AZURE_SMALL_MODEL_DEPLOYMENT",
        ]
        env_vars.extend(deployment_vars)

        # Override with environment variables
        for var in env_vars:
            env_value = os.environ.get(var)
            if env_value:
                self.config[var] = env_value

    def validate(self) -> bool:
        """Validate required configuration values.

        Returns:
            True if configuration is valid, False otherwise.
        """
        if self.is_azure_endpoint():
            return self.validate_azure_config()
        else:
            # For standard OpenAI proxy configuration
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
        # Create a copy and sanitize sensitive values if needed for debugging
        return self.config.copy()

    def to_sanitized_dict(self) -> Dict[str, str]:
        """Convert configuration to sanitized dictionary safe for logging.

        Returns:
            Dictionary with sensitive values sanitized.
        """
        sanitized = {}
        sensitive_keys = {"AZURE_OPENAI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"}

        for key, value in self.config.items():
            if key in sensitive_keys:
                sanitized[key] = self._sanitize_for_logging(value)
            else:
                sanitized[key] = value

        return sanitized

    def save_to(self, target_path: Path) -> None:
        """Save configuration to a new .env file.

        Args:
            target_path: Path where to save the configuration.
        """
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w") as f:
            for key, value in self.config.items():
                f.write(f"{key}={value}\n")

    def is_azure_endpoint(self) -> bool:
        """Check if configuration uses Azure OpenAI endpoint.

        Returns:
            True if Azure endpoint detected, False otherwise.
        """
        base_url = self.config.get("AZURE_OPENAI_BASE_URL") or self.config.get(
            "AZURE_OPENAI_ENDPOINT"
        )
        return self._azure_detector.is_azure_endpoint(base_url, self.config)

    def get_endpoint_type(self) -> str:
        """Get endpoint type (azure or openai).

        Returns:
            "azure" or "openai"
        """
        base_url = self.config.get("AZURE_OPENAI_BASE_URL") or self.config.get(
            "AZURE_OPENAI_ENDPOINT"
        )
        return self._azure_detector.get_endpoint_type(base_url, self.config)

    def validate_azure_config(self) -> bool:
        """Validate Azure-specific configuration.

        Returns:
            True if Azure configuration is valid, False otherwise.
        """
        self.validation_errors.clear()

        # Check required Azure fields
        api_key = self.config.get("AZURE_OPENAI_API_KEY", "").strip()
        if not api_key:
            if "AZURE_OPENAI_API_KEY" in self.config and self.config["AZURE_OPENAI_API_KEY"] == "":
                error_msg = "Azure API key cannot be empty"
            else:
                error_msg = "Missing required Azure configuration: AZURE_OPENAI_API_KEY"
            self.validation_errors.append(error_msg)
            print(error_msg)
        elif not self._validate_api_key_format(api_key):
            error_msg = "Invalid Azure API key format"
            self.validation_errors.append(error_msg)
            print(error_msg)

        # Check for endpoint - at least one should be provided
        endpoint = self.config.get("AZURE_OPENAI_ENDPOINT") or self.config.get(
            "AZURE_OPENAI_BASE_URL"
        )
        if not endpoint:
            error_msg = "Missing required Azure endpoint configuration: AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_BASE_URL"
            self.validation_errors.append(error_msg)
            print(error_msg)
        elif not self.validate_azure_endpoint_format():
            # Don't expose the actual endpoint URL in error messages for security
            error_msg = "Invalid Azure endpoint URL format"
            self.validation_errors.append(error_msg)
            print(error_msg)
        elif not self._enforce_https_endpoint(endpoint):
            error_msg = "Azure endpoint must use HTTPS for security"
            self.validation_errors.append(error_msg)
            print(error_msg)

        # Validate API version format if provided
        if not self.validate_azure_api_version():
            api_version = self.config.get("AZURE_OPENAI_API_VERSION")
            if api_version:  # Only report error if version is provided
                # Don't expose the actual version in error messages for security
                error_msg = "Invalid Azure API version format"
                self.validation_errors.append(error_msg)
                print(error_msg)

        # Validate deployment names if provided
        if not self.validate_azure_deployments():
            error_msg = "Invalid Azure deployment name format"
            self.validation_errors.append(error_msg)
            print(error_msg)

        return len(self.validation_errors) == 0

    def get_azure_deployment(self, model_name: str) -> Optional[str]:
        """Get Azure deployment name for OpenAI model.

        Args:
            model_name: OpenAI model name

        Returns:
            Azure deployment name if mapping exists, None otherwise.
        """
        return self._azure_mapper.get_azure_deployment(model_name)

    def get_azure_endpoint(self) -> Optional[str]:
        """Get Azure endpoint URL.

        Returns:
            Azure endpoint URL if configured, None otherwise.
        """
        return self.config.get("AZURE_OPENAI_ENDPOINT") or self.config.get("AZURE_OPENAI_BASE_URL")

    def get_azure_api_version(self) -> Optional[str]:
        """Get Azure API version.

        Returns:
            Azure API version if configured, None otherwise.
        """
        return self.config.get("AZURE_OPENAI_API_VERSION")

    def validate_azure_endpoint_format(self) -> bool:
        """Validate Azure endpoint URL format.

        Returns:
            True if valid Azure endpoint format, False otherwise.
        """
        endpoint = self.get_azure_endpoint()
        if not endpoint:
            return True  # No endpoint to validate

        return self._azure_detector.validate_azure_endpoint(endpoint)

    def validate_azure_api_version(self) -> bool:
        """Validate Azure API version format.

        Returns:
            True if valid API version format, False otherwise.
        """
        api_version = self.get_azure_api_version()
        if not api_version:
            return True  # No version to validate

        return self._validate_api_version_format(api_version)

    def validate_azure_deployments(self) -> bool:
        """Validate Azure deployment configuration.

        Returns:
            True if deployment configurations are valid, False otherwise.
        """
        # Check if any deployment mappings are configured
        deployment_keys = [
            k for k in self.config.keys() if k.startswith("AZURE_") and k.endswith("_DEPLOYMENT")
        ]

        # If no deployments configured, that's still valid
        if not deployment_keys:
            return True

        # Validate each deployment name (non-empty and secure format)
        for key in deployment_keys:
            value = self.config.get(key, "").strip()
            if not value:
                return False
            if not self._validate_deployment_name(value):
                return False

        return True

    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors from last validation.

        Returns:
            List of validation error messages.
        """
        return self.validation_errors.copy()

    def _validate_api_version_format(self, api_version: str) -> bool:
        """Validate Azure API version format.

        Args:
            api_version: API version string

        Returns:
            True if valid format, False otherwise.
        """
        # Azure API versions follow YYYY-MM-DD format
        # Use cached compiled regex for better performance
        return bool(self._API_VERSION_REGEX.match(api_version))

    def _validate_api_key_format(self, api_key: str) -> bool:
        """Validate Azure API key format.

        Args:
            api_key: API key string

        Returns:
            True if valid format, False otherwise.
        """
        if not api_key:
            return False

        # Allow test keys for development/testing
        if api_key.startswith(("test-", "sk-test-", "dummy-")):
            return len(api_key) >= 8

        # Basic format validation - at least 20 chars, alphanumeric with dashes/underscores
        return bool(self._API_KEY_REGEX.match(api_key))

    def _validate_deployment_name(self, deployment_name: str) -> bool:
        """Validate Azure deployment name format.

        Args:
            deployment_name: Deployment name string

        Returns:
            True if valid format, False otherwise.
        """
        # Deployment names should be 1-64 chars, alphanumeric with dashes/underscores
        return bool(self._DEPLOYMENT_NAME_REGEX.match(deployment_name))

    def _enforce_https_endpoint(self, endpoint: str) -> bool:
        """Enforce HTTPS for Azure endpoints.

        Args:
            endpoint: Endpoint URL

        Returns:
            True if HTTPS, False otherwise.
        """
        try:
            parsed = urlparse(endpoint)
            return parsed.scheme == "https"
        except Exception:
            return False

    def _sanitize_for_logging(self, value: str) -> str:
        """Sanitize sensitive values for safe logging.

        Args:
            value: Value to sanitize

        Returns:
            Sanitized value safe for logging.
        """
        if not value:
            return "<empty>"
        if len(value) <= 8:
            return "<redacted>"
        return value[:4] + "..." + value[-4:]
