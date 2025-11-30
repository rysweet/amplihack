"""Session management for the REST API client.

Handles HTTP session lifecycle and connection pooling.
"""

import asyncio
from contextlib import contextmanager
from typing import Any

import httpx

from .config import ClientConfig


class SessionManager:
    """Manages HTTP session lifecycle for the API client."""

    def __init__(self, config: ClientConfig) -> None:
        """Initialize the session manager.

        Args:
            config: Client configuration
        """
        self.config = config
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None

    def get_sync_client(self) -> httpx.Client:
        """Get or create a synchronous HTTP client.

        Returns:
            Configured httpx.Client instance
        """
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                base_url=self.config.base_url,
                headers=self.config.headers,
                timeout=httpx.Timeout(self.config.timeout),
                verify=self.config.verify_ssl,
                follow_redirects=True,
            )
        return self._sync_client

    def get_async_client(self) -> httpx.AsyncClient:
        """Get or create an asynchronous HTTP client.

        Returns:
            Configured httpx.AsyncClient instance
        """
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=self.config.headers,
                timeout=httpx.Timeout(self.config.timeout),
                verify=self.config.verify_ssl,
                follow_redirects=True,
            )
        return self._async_client

    def close_sync_client(self) -> None:
        """Close the synchronous HTTP client."""
        if self._sync_client is not None:
            self._sync_client.close()
            self._sync_client = None

    async def close_async_client(self) -> None:
        """Close the asynchronous HTTP client."""
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None

    def close(self) -> None:
        """Close all HTTP clients."""
        self.close_sync_client()
        if self._async_client is not None:
            # If there's an event loop, schedule the async close
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.close_async_client())
            except RuntimeError:
                # No running loop, create one to close the client
                asyncio.run(self.close_async_client())

    @contextmanager
    def sync_session(self) -> httpx.Client:
        """Context manager for synchronous HTTP sessions.

        Yields:
            Configured httpx.Client instance

        Example:
            with session_manager.sync_session() as client:
                response = client.get("/api/endpoint")
        """
        client = self.get_sync_client()
        try:
            yield client
        finally:
            # Don't close here - let the session manager handle lifecycle
            pass

    @contextmanager
    def temp_sync_session(self) -> httpx.Client:
        """Context manager for temporary synchronous HTTP sessions.

        Creates a new client that is closed after use.

        Yields:
            Configured httpx.Client instance
        """
        client = httpx.Client(
            base_url=self.config.base_url,
            headers=self.config.headers,
            timeout=httpx.Timeout(self.config.timeout),
            verify=self.config.verify_ssl,
            follow_redirects=True,
        )
        try:
            yield client
        finally:
            client.close()

    def update_headers(self, headers: dict[str, str]) -> None:
        """Update default headers for all sessions.

        Args:
            headers: Headers to add/update
        """
        self.config.headers.update(headers)

        # Update existing clients
        if self._sync_client:
            self._sync_client.headers.update(headers)
        if self._async_client:
            self._async_client.headers.update(headers)

    def set_header(self, key: str, value: str) -> None:
        """Set a specific header.

        Args:
            key: Header name
            value: Header value
        """
        self.config.headers[key] = value

        # Update existing clients
        if self._sync_client:
            self._sync_client.headers[key] = value
        if self._async_client:
            self._async_client.headers[key] = value

    def remove_header(self, key: str) -> None:
        """Remove a specific header.

        Args:
            key: Header name to remove
        """
        self.config.headers.pop(key, None)

        # Update existing clients
        if self._sync_client:
            self._sync_client.headers.pop(key, None)
        if self._async_client:
            self._async_client.headers.pop(key, None)

    def __enter__(self) -> "SessionManager":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and close sessions."""
        self.close()

    async def __aenter__(self) -> "SessionManager":
        """Async enter context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async exit context manager and close sessions."""
        await self.close_async_client()
        self.close_sync_client()


class SessionPool:
    """Pool of session managers for concurrent requests."""

    def __init__(self, config: ClientConfig, pool_size: int = 5) -> None:
        """Initialize the session pool.

        Args:
            config: Client configuration
            pool_size: Number of sessions in the pool
        """
        self.config = config
        self.pool_size = pool_size
        self._sessions: list[SessionManager] = []
        self._available: list[bool] = []
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Initialize the session pool."""
        for _ in range(self.pool_size):
            self._sessions.append(SessionManager(self.config))
            self._available.append(True)

    @contextmanager
    def acquire(self) -> SessionManager:
        """Acquire a session from the pool.

        Yields:
            Available SessionManager instance

        Raises:
            RuntimeError: If no sessions are available
        """
        # Find an available session
        session_index = -1
        for i, available in enumerate(self._available):
            if available:
                session_index = i
                break

        if session_index == -1:
            # No available sessions, create a temporary one
            temp_session = SessionManager(self.config)
            try:
                yield temp_session
            finally:
                temp_session.close()
        else:
            # Mark session as in use
            self._available[session_index] = False
            try:
                yield self._sessions[session_index]
            finally:
                # Mark session as available again
                self._available[session_index] = True

    def close_all(self) -> None:
        """Close all sessions in the pool."""
        for session in self._sessions:
            session.close()
        self._sessions.clear()
        self._available.clear()

    def __enter__(self) -> "SessionPool":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and close all sessions."""
        self.close_all()
