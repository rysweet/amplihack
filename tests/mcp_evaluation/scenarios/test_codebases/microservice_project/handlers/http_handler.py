"""HTTP request handler implementation."""

from typing import Any, Dict
from .base_handler import Handler
from ..services.user_service import UserService
from ..utils.logger import get_logger


logger = get_logger(__name__)


class HTTPHandler(Handler):
    """Handler for HTTP requests.

    Processes HTTP requests and delegates to appropriate services.
    """

    def __init__(self, user_service: UserService):
        """Initialize HTTP handler.

        Args:
            user_service: User service for user operations
        """
        self.user_service = user_service

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle HTTP request.

        Args:
            request: HTTP request data

        Returns:
            HTTP response data
        """
        if not self.validate_request(request):
            return {"error": "Invalid request", "status": 400}

        method = request.get("method", "GET")
        path = request.get("path", "/")

        logger.info(f"Handling {method} request to {path}")

        if path.startswith("/users"):
            return self._handle_user_request(request)
        elif path == "/health":
            return {"status": "ok", "code": 200}
        else:
            return {"error": "Not found", "status": 404}

    def validate_request(self, request: Dict[str, Any]) -> bool:
        """Validate HTTP request.

        Args:
            request: Request to validate

        Returns:
            True if valid
        """
        return "method" in request and "path" in request

    def _handle_user_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user-related requests.

        Args:
            request: HTTP request

        Returns:
            User operation response
        """
        method = request["method"]
        user_id = request.get("params", {}).get("user_id")

        if method == "GET" and user_id:
            user = self.user_service.get_user(user_id)
            if user:
                return {"user": user, "status": 200}
            return {"error": "User not found", "status": 404}

        return {"error": "Method not allowed", "status": 405}
