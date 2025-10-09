"""Real-time log streaming service for Azure OpenAI proxy integration."""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Set
from weakref import WeakSet

if TYPE_CHECKING:
    from fastapi import FastAPI, Response  # type: ignore[import-untyped]
    from fastapi.responses import StreamingResponse  # type: ignore[import-untyped]
else:
    try:
        from fastapi import FastAPI, Response  # type: ignore[import-untyped,import-not-found]
        from fastapi.responses import (
            StreamingResponse,  # type: ignore[import-untyped,import-not-found]
        )
    except ImportError:
        FastAPI = Response = StreamingResponse = None


class LogStreamer(logging.Handler):
    """Unified log streaming handler with SSE broadcasting."""

    def __init__(self):
        """Initialize the log streamer."""
        super().__init__()
        self._clients: Set[asyncio.Queue] = set()
        self._weak_clients = WeakSet()
        self._credential_pattern = re.compile(
            r'(?i)(?:api[_-]?key|token|password|authorization)["\s:=]*["\s]*([a-zA-Z0-9\-_+/=!@#$%^&*()]{8,})|sk-[a-zA-Z0-9]{48}|Bearer\s+[a-zA-Z0-9\-_+/=]{20,}'
        )

    def add_client(self) -> Optional[asyncio.Queue]:
        """Add SSE client. Returns queue or None if limit reached."""
        if len(self._clients) >= 10:  # Hard limit
            return None
        queue = asyncio.Queue(maxsize=100)  # Hard limit
        self._clients.add(queue)
        self._weak_clients.add(queue)
        return queue

    def remove_client(self, queue: asyncio.Queue) -> None:
        """Remove SSE client."""
        self._clients.discard(queue)
        self._weak_clients.discard(queue)

    def get_client_count(self) -> int:
        """Get connected client count."""
        return len(self._clients)

    def _sanitize(self, message: str) -> tuple[str, bool]:
        """Remove credentials from log message."""
        if self._credential_pattern.search(message):
            return self._credential_pattern.sub("<REDACTED>", message), True
        return message, False

    def emit(self, record: logging.LogRecord) -> None:
        """Handle log record by streaming to SSE clients."""
        if not self._clients:
            return

        try:
            message = self.format(record)
            sanitized_message, was_sanitized = self._sanitize(message)

            event_data = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": sanitized_message,
                "sanitized": was_sanitized,
            }

            sse_data = f"data: {json.dumps(event_data)}\n\n"

            # Broadcast to all clients
            for queue in list(self._clients):
                try:
                    queue.put_nowait(sse_data)
                except asyncio.QueueFull:
                    self.remove_client(queue)

            # Create task if event loop is running
            try:
                asyncio.get_running_loop()
                # Event loop is running, events will be processed
            except RuntimeError:
                # No event loop, can't stream
                pass

        except Exception:
            # Silently ignore logging errors to prevent cascading failures
            pass


class LogStreamingService:
    """Main log streaming service."""

    def __init__(self, port: int):
        """Initialize service on localhost for security."""
        self.port = port
        self.streamer = LogStreamer()
        self.server_task: Optional[asyncio.Task] = None
        self.running = False

    def _create_app(self) -> FastAPI:
        """Create FastAPI app with SSE endpoint."""
        app = FastAPI()

        @app.get("/stream/logs")
        async def stream_logs() -> StreamingResponse:
            """SSE endpoint for log streaming."""
            queue = self.streamer.add_client()
            if not queue:
                return Response("Max clients reached", status_code=503)

            async def events():
                try:
                    # Send connection event
                    yield f"data: {json.dumps({'type': 'connected'})}\n\n"

                    while True:
                        try:
                            data = await asyncio.wait_for(queue.get(), timeout=30.0)
                            yield data
                        except asyncio.TimeoutError:
                            yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
                finally:
                    self.streamer.remove_client(queue)

            return StreamingResponse(
                events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
            )

        @app.get("/health")
        async def health():
            return {"clients": self.streamer.get_client_count()}

        return app

    def _setup_logging(self) -> None:
        """Setup logging integration."""
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.streamer.setFormatter(formatter)
        self.streamer.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(self.streamer)

    async def start(self) -> bool:
        """Start the log streaming service."""
        if self.running:
            return True

        try:
            app = self._create_app()
            self._setup_logging()

            try:
                import uvicorn  # type: ignore[import-untyped,import-not-found]
            except ImportError:
                print("uvicorn not available - log streaming disabled")
                return False

            config = uvicorn.Config(
                app=app, host="127.0.0.1", port=self.port, log_level="error", access_log=False
            )

            server = uvicorn.Server(config)
            self.server_task = asyncio.create_task(server.serve())
            await asyncio.sleep(0.5)

            self.running = True
            print(f"Log streaming: http://127.0.0.1:{self.port}/stream/logs")
            return True

        except Exception as e:
            print(f"Log streaming failed: {e}")
            return False

    async def stop(self) -> None:
        """Stop the service."""
        if not self.running:
            return

        try:
            logging.getLogger().removeHandler(self.streamer)
            if self.server_task:
                self.server_task.cancel()
                try:
                    await self.server_task
                except asyncio.CancelledError:
                    pass
            self.running = False
        except Exception:
            pass

    def is_running(self) -> bool:
        """Check if service is running."""
        if not self.running or not self.server_task:
            return False
        return not self.server_task.done()
