"""
Enhanced .env configuration for passthrough mode.

This module provides comprehensive configuration management for Passthrough Mode
with Anthropic→Azure fallback, supporting multi-provider configuration.

Public API:
    PassthroughConfig: Main configuration management class
    ValidationResult: Configuration validation results
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]


class PassthroughConfig:
    """Enhanced .env configuration for passthrough mode with multi-provider support."""

    # API key validation patterns
    _ANTHROPIC_KEY_PATTERN = re.compile(r"^sk-ant-[a-zA-Z0-9]{20,}$")
    _AZURE_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9]{20,}$")

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize passthrough configuration.

        Args:
            config_path: Path to .env configuration file.
        """
        self.config_path = config_path
        self.config: Dict[str, str] = {}

        if config_path and config_path.exists():
            self._load_config()

        # Load from environment variables (they take precedence)
        self._load_environment_variables()

    def _load_config(self) -> None:
        """Load configuration from .env file."""
        if not self.config_path or not self.config_path.exists():
            return

        with open(self.config_path, "r") as f:
            content = f.read()

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            eq_index = line.find("=")
            if eq_index > 0:
                key = line[:eq_index].strip()
                value = line[eq_index + 1 :].strip()

                # Remove quotes
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                self.config[key] = value

    def _load_environment_variables(self) -> None:
        """Load environment variables that override file configuration."""
        env_vars = [
            "PASSTHROUGH_MODE",
            "ANTHROPIC_API_KEY",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_ENDPOINT",
            "PROVIDER_SWITCH_COOLDOWN",
            "PASSTHROUGH_LOG_LEVEL",
            "ANTHROPIC_BASE_URL",
            "AZURE_OPENAI_API_VERSION",
        ]

        for var in env_vars:
            value = os.environ.get(var)
            if value:
                self.config[var] = value

    def is_passthrough_enabled(self) -> bool:
        """Check if passthrough mode is enabled."""
        return self.config.get("PASSTHROUGH_MODE", "false").lower() == "true"

    def get_anthropic_key(self) -> Optional[str]:
        """Get Anthropic API key."""
        return self.config.get("ANTHROPIC_API_KEY")

    def get_azure_key(self) -> Optional[str]:
        """Get Azure OpenAI API key."""
        return self.config.get("AZURE_OPENAI_API_KEY")

    def get_azure_endpoint(self) -> Optional[str]:
        """Get Azure OpenAI endpoint URL."""
        return self.config.get("AZURE_OPENAI_ENDPOINT")

    def get_anthropic_base_url(self) -> str:
        """Get Anthropic base URL (defaults to api.anthropic.com)."""
        return self.config.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

    def get_azure_api_version(self) -> str:
        """Get Azure OpenAI API version."""
        return self.config.get("AZURE_OPENAI_API_VERSION", "2024-02-01")

    def get_switch_cooldown(self) -> int:
        """Get provider switch cooldown in seconds."""
        return int(self.config.get("PROVIDER_SWITCH_COOLDOWN", "300"))

    def get_log_level(self) -> str:
        """Get passthrough logging level."""
        return self.config.get("PASSTHROUGH_LOG_LEVEL", "INFO")

    def get_configured_providers(self) -> List[str]:
        """Get list of configured providers."""
        providers = []

        if self.get_anthropic_key():
            providers.append("anthropic")

        if self.get_azure_key() and self.get_azure_endpoint():
            providers.append("azure")

        return providers

    def validate_configuration(self) -> ValidationResult:
        """Validate passthrough mode configuration."""
        errors = []
        warnings = []

        # Check if passthrough mode is enabled
        if not self.is_passthrough_enabled():
            warnings.append("Passthrough mode is not enabled")
            return ValidationResult(True, errors, warnings)

        # Validate Anthropic configuration
        anthropic_key = self.get_anthropic_key()
        if not anthropic_key:
            errors.append("ANTHROPIC_API_KEY is required for passthrough mode")
        elif not self._ANTHROPIC_KEY_PATTERN.match(anthropic_key):
            errors.append("ANTHROPIC_API_KEY format is invalid (should start with 'sk-ant-')")

        # Validate Azure configuration (required for fallback)
        azure_key = self.get_azure_key()
        azure_endpoint = self.get_azure_endpoint()

        if not azure_key:
            errors.append("AZURE_OPENAI_API_KEY is required for Azure fallback")
        elif not self._AZURE_KEY_PATTERN.match(azure_key):
            errors.append("AZURE_OPENAI_API_KEY format is invalid")

        if not azure_endpoint:
            errors.append("AZURE_OPENAI_ENDPOINT is required for Azure fallback")
        elif azure_endpoint:
            # Validate endpoint URL format
            try:
                parsed = urlparse(azure_endpoint)
                if not parsed.scheme or not parsed.netloc:
                    errors.append("AZURE_OPENAI_ENDPOINT must be a valid URL")
                elif not parsed.netloc.endswith(".openai.azure.com"):
                    warnings.append("AZURE_OPENAI_ENDPOINT should end with '.openai.azure.com'")
            except Exception:
                errors.append("AZURE_OPENAI_ENDPOINT is not a valid URL")

        # Validate Anthropic base URL
        anthropic_base = self.get_anthropic_base_url()
        try:
            parsed = urlparse(anthropic_base)
            if not parsed.scheme or not parsed.netloc:
                errors.append("ANTHROPIC_BASE_URL must be a valid URL")
        except Exception:
            errors.append("ANTHROPIC_BASE_URL is not a valid URL")

        # Validate cooldown setting
        try:
            cooldown = self.get_switch_cooldown()
            if cooldown < 0:
                errors.append("PROVIDER_SWITCH_COOLDOWN must be non-negative")
            elif cooldown < 60:
                warnings.append(
                    "PROVIDER_SWITCH_COOLDOWN less than 60 seconds may cause rapid switching"
                )
        except (ValueError, TypeError):
            errors.append("PROVIDER_SWITCH_COOLDOWN must be a valid number")

        return ValidationResult(len(errors) == 0, errors, warnings)

    def get_provider_config(self, provider: str) -> Dict[str, str]:
        """Get configuration for specific provider."""
        if provider == "anthropic":
            return {
                "api_key": self.get_anthropic_key() or "",
                "base_url": self.get_anthropic_base_url(),
                "provider": "anthropic",
            }
        elif provider == "azure":
            return {
                "api_key": self.get_azure_key() or "",
                "base_url": self.get_azure_endpoint() or "",
                "api_version": self.get_azure_api_version(),
                "provider": "azure",
            }
        else:
            raise ValueError(f"Unknown provider: {provider}")


__all__ = ["PassthroughConfig", "ValidationResult"]
