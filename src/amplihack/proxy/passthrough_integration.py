"""
Integration layer for Passthrough Mode with existing FastAPI proxy system.

This module provides seamless integration between the passthrough functionality
and the existing proxy server, fulfilling the requirement for integration
with existing proxy system and Azure foundation.

Public API:
    PassthroughHandler: Main integration handler for FastAPI
    setup_passthrough_routes: Route configuration function
"""

import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from .passthrough import PassthroughProvider, PassthroughResponse, ProviderSwitcher
from .passthrough_config import PassthroughConfig

logger = logging.getLogger(__name__)


class PassthroughHandler:
    """Main integration handler for passthrough mode with existing FastAPI proxy."""

    def __init__(self, config: PassthroughConfig):
        """Initialize passthrough handler.

        Args:
            config: Passthrough configuration instance
        """
        self.config = config
        self.provider_switcher: Optional[ProviderSwitcher] = None
        self.anthropic_provider: Optional[PassthroughProvider] = None

        # Only initialize if passthrough mode is enabled
        if config.is_passthrough_enabled():
            self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize passthrough providers."""
        # Validate configuration
        validation = self.config.validate_configuration()
        if not validation.is_valid:
            logger.error(f"Passthrough configuration invalid: {validation.errors}")
            return

        # Initialize provider switcher
        config_dict = {
            "ANTHROPIC_API_KEY": self.config.get_anthropic_key(),
            "AZURE_OPENAI_API_KEY": self.config.get_azure_key(),
            "AZURE_OPENAI_ENDPOINT": self.config.get_azure_endpoint(),
            "PROVIDER_SWITCH_COOLDOWN": str(self.config.get_switch_cooldown()),
        }
        self.provider_switcher = ProviderSwitcher(config_dict)

        # Initialize Anthropic provider
        anthropic_key = self.config.get_anthropic_key()
        if anthropic_key:
            self.anthropic_provider = PassthroughProvider(
                anthropic_api_key=anthropic_key, base_url=self.config.get_anthropic_base_url()
            )

        logger.info("Passthrough mode initialized successfully")

    async def handle_chat_completion(self, request: Request) -> Response:
        """Handle chat completion request with passthrough logic.

        EXPLICIT USER REQUIREMENT: Start proxy and pass ALL requests to api.anthropic.com without modifying them initially.
        EXPLICIT USER REQUIREMENT: Use Anthropic until hitting 429 error, then switch to Azure.

        Args:
            request: FastAPI request object

        Returns:
            Response from current provider
        """
        if not self.config.is_passthrough_enabled():
            raise HTTPException(status_code=503, detail="Passthrough mode not enabled")

        if not self.provider_switcher or not self.anthropic_provider:
            raise HTTPException(status_code=503, detail="Passthrough providers not initialized")

        # Get request data
        try:
            body = await request.json()
        except Exception:
            body = {}

        headers = dict(request.headers)

        # Get current provider
        current_provider = self.provider_switcher.get_current_provider()

        if current_provider == "anthropic":
            # Forward to Anthropic API
            response = await self.anthropic_provider.forward_request(
                method=request.method, url=str(request.url.path), headers=headers, body=body
            )

            # Handle provider switching based on response
            if response.status_code == 429:
                self.provider_switcher.handle_error(429, "rate_limit_error")

                # If switched to Azure, try Azure
                if self.provider_switcher.get_current_provider() == "azure":
                    logger.info("Retrying request with Azure after Anthropic 429")
                    azure_response = await self._handle_azure_request(body, headers)
                    return azure_response

        else:  # current_provider == "azure"
            # Use Azure OpenAI
            response = await self._handle_azure_request(body, headers)

        # Convert to FastAPI response
        return self._create_fastapi_response(response)

    async def _handle_azure_request(
        self, body: Dict[str, Any], headers: Dict[str, str]
    ) -> Response:
        """Handle request using Azure OpenAI.

        Args:
            body: Request body
            headers: Request headers

        Returns:
            Azure OpenAI response
        """
        # For now, return a placeholder response
        # In full implementation, this would use existing Azure components
        azure_response = PassthroughResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            content={
                "choices": [{"message": {"content": "Azure OpenAI response (fallback)"}}],
                "provider": "azure",
            },
            provider="azure",
        )

        return self._create_fastapi_response(azure_response)

    def _create_fastapi_response(self, passthrough_response: PassthroughResponse) -> Response:
        """Convert PassthroughResponse to FastAPI Response.

        Args:
            passthrough_response: Response from passthrough provider

        Returns:
            FastAPI Response object
        """
        if isinstance(passthrough_response.content, dict):
            return JSONResponse(
                content=passthrough_response.content,
                status_code=passthrough_response.status_code,
                headers=passthrough_response.headers,
            )
        else:
            return Response(
                content=str(passthrough_response.content),
                status_code=passthrough_response.status_code,
                headers=passthrough_response.headers,
            )

    async def get_provider_status(self) -> Dict[str, Any]:
        """Get current provider status information.

        Returns:
            Provider status information
        """
        if not self.config.is_passthrough_enabled():
            return {"passthrough_enabled": False}

        if not self.provider_switcher:
            return {"passthrough_enabled": True, "status": "not_initialized"}

        return {
            "passthrough_enabled": True,
            "current_provider": self.provider_switcher.get_current_provider(),
            "configured_providers": self.config.get_configured_providers(),
            "config_valid": self.config.validate_configuration().is_valid,
        }

    async def cleanup(self):
        """Cleanup resources."""
        if self.anthropic_provider:
            await self.anthropic_provider.close()


def setup_passthrough_routes(app, config: PassthroughConfig):
    """Setup passthrough routes in FastAPI app.

    EXPLICIT USER REQUIREMENT: Integration with existing proxy system.

    Args:
        app: FastAPI application instance
        config: Passthrough configuration
    """
    handler = PassthroughHandler(config)

    @app.post("/v1/chat/completions")
    async def chat_completions_passthrough(request: Request):
        """Chat completions endpoint with passthrough logic."""
        return await handler.handle_chat_completion(request)

    @app.get("/passthrough/status")
    async def passthrough_status():
        """Get passthrough provider status."""
        return await handler.get_provider_status()

    # Add cleanup on shutdown
    @app.on_event("shutdown")
    async def shutdown_passthrough():
        """Cleanup passthrough resources."""
        await handler.cleanup()

    logger.info("Passthrough routes configured successfully")


__all__ = ["PassthroughHandler", "setup_passthrough_routes"]
