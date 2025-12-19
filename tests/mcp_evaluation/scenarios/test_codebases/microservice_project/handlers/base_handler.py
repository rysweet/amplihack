"""Base handler interface for microservice requests.

This module defines the abstract Handler interface that all
request handlers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any


class Handler(ABC):
    """Abstract base class for request handlers.

    All handlers must implement the handle method to process requests.
    """

    @abstractmethod
    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle an incoming request.

        Args:
            request: Request data

        Returns:
            Response data
        """

    @abstractmethod
    def validate_request(self, request: dict[str, Any]) -> bool:
        """Validate request format and content.

        Args:
            request: Request to validate

        Returns:
            True if valid, False otherwise
        """
