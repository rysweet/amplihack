"""Integration tests for REST API client."""

import threading
import time
from unittest.mock import patch

import pytest

# These imports will fail initially (TDD)
from rest_api_client import APIClient
from rest_api_client.config import APIConfig
from rest_api_client.exceptions import (
    RateLimitError,
    ServerError,
)


class TestClientWithRetryIntegration:
    """Test APIClient with retry mechanism integration."""

    def test_client_retries_with_backoff(self, mock_response, mock_session):
        """Test that client integrates retry with exponential backoff."""
        config = APIConfig(
            base_url="https://api.example.com", max_retries=3, retry_delay=0.1, max_retry_delay=1.0
        )
        client = APIClient(config=config)

        # Fail 2 times, succeed on 3rd
        mock_session.get.side_effect = [
            mock_response(503, json_data={"error": "Unavailable"}),
            mock_response(502, json_data={"error": "Bad gateway"}),
            mock_response(200, json_data={"data": "success"}),
        ]

        with patch.object(client, "_session", mock_session):
            response = client.get("/resource")

        assert response.status_code == 200
        assert response.json["data"] == "success"
        assert mock_session.get.call_count == 3

    def test_client_retry_exhaustion(self, mock_response, mock_session):
        """Test retry exhaustion raises final error."""
        config = APIConfig(base_url="https://api.example.com", max_retries=2, retry_delay=0.01)
        client = APIClient(config=config)

        # Always fail
        mock_session.get.return_value = mock_response(500, json_data={"error": "Server error"})

        with patch.object(client, "_session", mock_session):
            with pytest.raises(ServerError) as exc_info:
                client.get("/resource")

        assert exc_info.value.status_code == 500
        # Initial attempt + 2 retries = 3 calls
        assert mock_session.get.call_count == 3


class TestClientWithRateLimitingIntegration:
    """Test APIClient with rate limiting integration."""

    def test_client_respects_rate_limits(self, mock_response, mock_session, mock_time):
        """Test client respects configured rate limits."""
        config = APIConfig(
            base_url="https://api.example.com",
            rate_limit_calls=3,
            rate_limit_period=1,  # 3 calls per second
        )
        client = APIClient(config=config)

        mock_session.get.return_value = mock_response(200, json_data={})

        with patch.object(client, "_session", mock_session):
            start_time = time.time()

            # Make 5 rapid calls
            for _ in range(5):
                client.get("/resource")

            # Should have taken some time due to rate limiting
            # With 3 calls/sec, 5 calls should take > 1 second

        assert mock_session.get.call_count == 5

    def test_client_handles_429_with_retry_after(self, mock_response, mock_session):
        """Test client handles 429 with Retry-After header."""
        config = APIConfig(base_url="https://api.example.com", max_retries=2)
        client = APIClient(config=config)

        # First call gets rate limited, second succeeds
        mock_session.get.side_effect = [
            mock_response(
                429, json_data={"error": "Too many requests"}, headers={"Retry-After": "2"}
            ),
            mock_response(200, json_data={"data": "success"}),
        ]

        with patch.object(client, "_session", mock_session):
            response = client.get("/resource")

        assert response.status_code == 200
        assert mock_session.get.call_count == 2

    def test_adaptive_rate_limiting(self, mock_response, mock_session):
        """Test adaptive rate limiting adjusts to 429 responses."""
        config = APIConfig(base_url="https://api.example.com", use_adaptive_rate_limiting=True)
        client = APIClient(config=config)

        # Simulate rate limit, then success
        responses = [
            mock_response(200, json_data={"page": 1}),
            mock_response(200, json_data={"page": 2}),
            mock_response(429, headers={"Retry-After": "1"}),
            mock_response(200, json_data={"page": 3}),
            mock_response(200, json_data={"page": 4}),
        ]
        mock_session.get.side_effect = responses

        with patch.object(client, "_session", mock_session):
            # Should adapt after 429
            results = []
            for i in range(4):
                try:
                    response = client.get(f"/page/{i + 1}")
                    results.append(response.json)
                except RateLimitError:
                    # Wait and retry
                    time.sleep(1)
                    response = client.get(f"/page/{i + 1}")
                    results.append(response.json)

        assert len(results) == 4


class TestClientErrorRecovery:
    """Test error recovery scenarios."""

    def test_recover_from_connection_error(self, mock_response, mock_session):
        """Test recovery from connection errors."""
        import requests

        config = APIConfig(base_url="https://api.example.com", max_retries=3, retry_delay=0.01)
        client = APIClient(config=config)

        # Connection error, then success
        mock_session.get.side_effect = [
            requests.ConnectionError("Connection failed"),
            mock_response(200, json_data={"data": "recovered"}),
        ]

        with patch.object(client, "_session", mock_session):
            response = client.get("/resource")

        assert response.status_code == 200
        assert response.json["data"] == "recovered"

    def test_circuit_breaker_pattern(self, mock_response, mock_session):
        """Test circuit breaker pattern for failing services."""
        config = APIConfig(
            base_url="https://api.example.com",
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=5,
        )
        client = APIClient(config=config)

        # Multiple failures should trigger circuit breaker
        mock_session.get.return_value = mock_response(500, json_data={"error": "Server error"})

        with patch.object(client, "_session", mock_session):
            # First 3 failures
            for _ in range(3):
                with pytest.raises(ServerError):
                    client.get("/resource")

            # Circuit should be open now
            with pytest.raises(APIClientError, match="Circuit breaker open"):
                client.get("/resource")

            # Should not make actual request when circuit is open
            assert mock_session.get.call_count == 3


class TestClientAuthentication:
    """Test authentication integration."""

    def test_api_key_authentication(self, mock_response, mock_session):
        """Test API key authentication."""
        client = APIClient(base_url="https://api.example.com", api_key="test-key-123")

        mock_session.get.return_value = mock_response(200, json_data={})

        with patch.object(client, "_session", mock_session):
            client.get("/protected")

        # Check Authorization header was included
        call_kwargs = mock_session.get.call_args.kwargs
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-key-123"

    def test_custom_auth_header(self, mock_response, mock_session):
        """Test custom authentication header."""
        config = APIConfig(base_url="https://api.example.com", headers={"X-API-Key": "custom-key"})
        client = APIClient(config=config)

        mock_session.get.return_value = mock_response(200, json_data={})

        with patch.object(client, "_session", mock_session):
            client.get("/resource")

        call_kwargs = mock_session.get.call_args.kwargs
        assert call_kwargs["headers"]["X-API-Key"] == "custom-key"

    def test_auth_refresh_on_401(self, mock_response, mock_session):
        """Test automatic auth refresh on 401."""
        client = APIClient(
            base_url="https://api.example.com", api_key="old-key", auto_refresh_auth=True
        )

        # Mock refresh function
        def refresh_auth():
            client.api_key = "new-key"
            client.headers["Authorization"] = "Bearer new-key"

        client.refresh_auth = refresh_auth

        # First call fails with 401, second succeeds
        mock_session.get.side_effect = [
            mock_response(401, json_data={"error": "Invalid token"}),
            mock_response(200, json_data={"data": "success"}),
        ]

        with patch.object(client, "_session", mock_session):
            response = client.get("/protected")

        assert response.status_code == 200
        assert mock_session.get.call_count == 2


class TestConcurrentRequests:
    """Test concurrent request handling."""

    def test_thread_safe_rate_limiting(self, mock_response, mock_session):
        """Test rate limiting is thread-safe."""
        config = APIConfig(
            base_url="https://api.example.com", rate_limit_calls=5, rate_limit_period=1
        )
        client = APIClient(config=config)

        mock_session.get.return_value = mock_response(200, json_data={})
        results = []
        errors = []

        def make_request(i):
            try:
                with patch.object(client, "_session", mock_session):
                    response = client.get(f"/resource/{i}")
                    results.append(response.status_code)
            except Exception as e:
                errors.append(e)

        # Start 10 threads making requests
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All requests should succeed (rate limiting delays, not blocks)
        assert len(results) == 10
        assert len(errors) == 0

    def test_connection_pooling(self, mock_response):
        """Test connection pooling for concurrent requests."""
        config = APIConfig(
            base_url="https://api.example.com", max_connections=5, max_connections_per_host=2
        )
        client = APIClient(config=config)

        # Verify session has proper adapter configuration
        assert client._session is not None
        # Check that pooling is configured
        adapter = client._session.get_adapter("https://")
        assert adapter.poolmanager is not None


class TestClientPagination:
    """Test pagination support."""

    def test_paginate_through_results(self, mock_response, mock_session):
        """Test paginating through API results."""
        client = APIClient(base_url="https://api.example.com")

        # Mock paginated responses
        responses = [
            mock_response(200, json_data={"data": [{"id": 1}, {"id": 2}], "next_page": 2}),
            mock_response(200, json_data={"data": [{"id": 3}, {"id": 4}], "next_page": 3}),
            mock_response(200, json_data={"data": [{"id": 5}], "next_page": None}),
        ]
        mock_session.get.side_effect = responses

        with patch.object(client, "_session", mock_session):
            all_data = []
            page = 1

            while page:
                response = client.get("/items", params={"page": page})
                all_data.extend(response.json["data"])
                page = response.json.get("next_page")

        assert len(all_data) == 5
        assert all_data[0]["id"] == 1
        assert all_data[4]["id"] == 5

    def test_paginate_generator(self, mock_response, mock_session):
        """Test pagination using generator."""
        client = APIClient(base_url="https://api.example.com")

        responses = [
            mock_response(200, json_data={"items": [1, 2], "has_more": True}),
            mock_response(200, json_data={"items": [3, 4], "has_more": True}),
            mock_response(200, json_data={"items": [5], "has_more": False}),
        ]
        mock_session.get.side_effect = responses

        with patch.object(client, "_session", mock_session):
            # Use paginate helper
            all_items = list(client.paginate("/items"))

        assert all_items == [1, 2, 3, 4, 5]
