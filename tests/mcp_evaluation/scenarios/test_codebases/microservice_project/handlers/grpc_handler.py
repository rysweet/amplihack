"""gRPC request handler implementation."""

from typing import Any, Dict

from ..services.auth_service import AuthService
from ..utils.logger import get_logger
from .base_handler import Handler

logger = get_logger(__name__)


class GRPCHandler(Handler):
    """Handler for gRPC requests.

    Processes gRPC requests and delegates to appropriate services.
    """

    def __init__(self, auth_service: AuthService):
        """Initialize gRPC handler.

        Args:
            auth_service: Authentication service
        """
        self.auth_service = auth_service

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle gRPC request.

        Args:
            request: gRPC request data

        Returns:
            gRPC response data
        """
        if not self.validate_request(request):
            return {"error": "Invalid request"}

        service = request.get("service")
        method = request.get("method")

        logger.info(f"Handling gRPC call: {service}.{method}")

        if service == "AuthService":
            return self._handle_auth_request(request)

        return {"error": "Service not found"}

    def validate_request(self, request: Dict[str, Any]) -> bool:
        """Validate gRPC request.

        Args:
            request: Request to validate

        Returns:
            True if valid
        """
        return "service" in request and "method" in request

    def _handle_auth_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle authentication requests.

        Args:
            request: gRPC request

        Returns:
            Authentication response
        """
        method = request["method"]
        payload = request.get("payload", {})

        if method == "authenticate":
            username = payload.get("username")
            password = payload.get("password")
            token = self.auth_service.authenticate(username, password)
            if token:
                return {"token": token}
            return {"error": "Authentication failed"}

        return {"error": "Method not supported"}
