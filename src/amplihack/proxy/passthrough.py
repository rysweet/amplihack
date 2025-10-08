"""
Passthrough Mode implementation with Anthropic→Azure fallback.

This module implements transparent request forwarding to api.anthropic.com
with intelligent fallback to Azure OpenAI on 429 errors.

Public API:
    PassthroughProvider: Core passthrough functionality
    ProviderSwitcher: Intelligent provider switching logic
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

import httpx  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


@dataclass
class PassthroughResponse:
    """Response from passthrough provider."""

    status_code: int
    headers: Dict[str, str]
    content: Union[Dict[str, Any], str]
    provider: str
    error: Optional[str] = None


class PassthroughProvider:
    """Transparent request forwarding to api.anthropic.com with 429 error detection."""

    def __init__(self, anthropic_api_key: str, base_url: str = "https://api.anthropic.com"):
        """Initialize passthrough provider.

        Args:
            anthropic_api_key: Anthropic API key for authentication
            base_url: Base URL for Anthropic API (defaults to api.anthropic.com)
        """
        self.anthropic_api_key = anthropic_api_key
        self.base_url = base_url.rstrip("/")
        self.last_response_code: Optional[int] = None
        self.client = httpx.AsyncClient(timeout=60.0)

    async def forward_request(
        self, method: str, url: str, headers: Dict[str, str], body: Optional[Dict[str, Any]] = None
    ) -> PassthroughResponse:
        """Forward request to Anthropic API without modification.

        EXPLICIT USER REQUIREMENT: Pass ALL requests to api.anthropic.com without modifying them initially.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL path
            headers: Request headers
            body: Request body data

        Returns:
            PassthroughResponse with Anthropic API response
        """
        # Prepare headers for Anthropic API
        forwarded_headers = self._prepare_headers(headers)

        # Construct full URL
        full_url = f"{self.base_url}{url}"

        try:
            logger.info(f"Forwarding {method} request to Anthropic: {url}")

            # Forward request to Anthropic API
            response = await self.client.request(
                method=method, url=full_url, headers=forwarded_headers, json=body if body else None
            )

            self.last_response_code = response.status_code

            # Parse response content
            try:
                content = response.json()
            except Exception:
                content = response.text

            # Create response object
            passthrough_response = PassthroughResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                content=content,
                provider="anthropic",
            )

            # Log 429 errors for switching logic
            if response.status_code == 429:
                logger.warning("Anthropic API returned 429 (rate limit exceeded)")
                passthrough_response.error = "rate_limit_exceeded"

            return passthrough_response

        except httpx.TimeoutException:
            logger.error("Request to Anthropic API timed out")
            return PassthroughResponse(
                status_code=408,
                headers={},
                content={"error": "Request timeout"},
                provider="anthropic",
                error="timeout",
            )

        except httpx.RequestError as e:
            logger.error(f"Request to Anthropic API failed: {e}")
            return PassthroughResponse(
                status_code=502,
                headers={},
                content={"error": "Bad gateway"},
                provider="anthropic",
                error="connection_error",
            )

    def _prepare_headers(self, original_headers: Dict[str, str]) -> Dict[str, str]:
        """Prepare headers for Anthropic API request.

        Args:
            original_headers: Original request headers

        Returns:
            Headers prepared for Anthropic API
        """
        # Start with original headers (preserve everything)
        headers = original_headers.copy()

        # Set Anthropic API authentication
        headers["x-api-key"] = self.anthropic_api_key

        # Ensure content type for JSON requests
        if "content-type" not in headers:
            headers["content-type"] = "application/json"

        # Add Anthropic-specific headers
        headers["anthropic-version"] = "2023-06-01"

        return headers

    def last_error_was_429(self) -> bool:
        """Check if last response was a 429 rate limit error.

        Returns:
            True if last response was 429 error
        """
        return self.last_response_code == 429

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class ProviderSwitcher:
    """Intelligent provider switching based on error patterns."""

    def __init__(self, config: Dict[str, str], state_file: str = "provider_state.json"):
        """Initialize provider switcher.

        Args:
            config: Configuration dictionary with API keys and settings
            state_file: File to persist provider state
        """
        self.config = config
        self.state_file = Path(state_file)
        self.current_provider = "anthropic"  # Start with Anthropic
        self.last_switch_time = 0
        self.switch_cooldown = int(config.get("PROVIDER_SWITCH_COOLDOWN", "300"))

        # Load persisted state
        self._load_state()

    def get_current_provider(self) -> str:
        """Get currently active provider.

        Returns:
            Current provider name ("anthropic" or "azure")
        """
        return self.current_provider

    def handle_error(self, status_code: int, error_type: str) -> None:
        """Handle error and potentially switch providers.

        EXPLICIT USER REQUIREMENT: Use Anthropic until hitting 429 error, then switch to Azure.

        Args:
            status_code: HTTP status code from response
            error_type: Type of error encountered
        """
        current_time = time.time()

        # Check for 429 rate limit error
        if status_code == 429 and error_type == "rate_limit_error":
            # Switch to Azure if not already there and cooldown passed
            if (
                self.current_provider == "anthropic"
                and current_time - self.last_switch_time > self.switch_cooldown
            ):
                logger.info("Switching to Azure OpenAI due to Anthropic 429 error")
                self.current_provider = "azure"
                self.last_switch_time = current_time
                self._save_state()

        # Check for recovery (successful responses)
        elif status_code == 200 and self.current_provider == "azure":
            # Consider switching back to Anthropic after cooldown
            if current_time - self.last_switch_time > self.switch_cooldown:
                logger.info("Considering switch back to Anthropic (recovery detected)")
                # For now, stay on Azure for stability
                # Future enhancement: implement gradual recovery

    def _load_state(self) -> None:
        """Load provider state from file."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file) as f:
                state = json.load(f)
                self.current_provider = state.get("current_provider", "anthropic")
                self.last_switch_time = state.get("last_switch_time", 0)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("Could not load provider state, using defaults")

    def _save_state(self) -> None:
        """Save provider state to file."""
        state = {
            "current_provider": self.current_provider,
            "last_switch_time": self.last_switch_time,
        }

        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f)
        except Exception as e:
            logger.warning(f"Could not save provider state: {e}")

    def get_provider_config(self, provider: str) -> Dict[str, str]:
        """Get configuration for specified provider.

        Args:
            provider: Provider name ("anthropic" or "azure")

        Returns:
            Provider configuration dictionary
        """
        if provider == "anthropic":
            return {
                "api_key": self.config.get("ANTHROPIC_API_KEY", ""),
                "base_url": self.config.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
                "provider": "anthropic",
            }
        if provider == "azure":
            return {
                "api_key": self.config.get("AZURE_OPENAI_API_KEY", ""),
                "base_url": self.config.get("AZURE_OPENAI_ENDPOINT", ""),
                "api_version": self.config.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                "provider": "azure",
            }
        raise ValueError(f"Unknown provider: {provider}")


__all__ = ["PassthroughProvider", "ProviderSwitcher", "PassthroughResponse"]
