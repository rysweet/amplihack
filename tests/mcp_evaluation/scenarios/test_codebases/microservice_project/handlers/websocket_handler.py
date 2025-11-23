"""WebSocket handler implementation."""

from typing import Any, Dict

from ..utils.logger import get_logger
from .base_handler import Handler

logger = get_logger(__name__)


class WebSocketHandler(Handler):
    """Handler for WebSocket connections.

    Manages WebSocket message handling and broadcasting.
    """

    def __init__(self):
        """Initialize WebSocket handler."""
        self.connections = []

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle WebSocket message.

        Args:
            request: WebSocket message data

        Returns:
            Response data
        """
        if not self.validate_request(request):
            return {"error": "Invalid message"}

        message_type = request.get("type")
        logger.info(f"Handling WebSocket message: {message_type}")

        if message_type == "connect":
            return self._handle_connect(request)
        if message_type == "disconnect":
            return self._handle_disconnect(request)
        if message_type == "message":
            return self._handle_message(request)

        return {"error": "Unknown message type"}

    def validate_request(self, request: Dict[str, Any]) -> bool:
        """Validate WebSocket message.

        Args:
            request: Message to validate

        Returns:
            True if valid
        """
        return "type" in request

    def _handle_connect(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle connection request."""
        conn_id = request.get("connection_id")
        self.connections.append(conn_id)
        return {"status": "connected", "connection_id": conn_id}

    def _handle_disconnect(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle disconnection request."""
        conn_id = request.get("connection_id")
        if conn_id in self.connections:
            self.connections.remove(conn_id)
        return {"status": "disconnected"}

    def _handle_message(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle regular message."""
        message = request.get("message", "")
        return {"status": "delivered", "message": message}
