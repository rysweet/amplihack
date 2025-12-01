"""
Tests for request/response dataclasses.

Tests the immutable dataclasses used for request and response modeling.

Coverage areas:
- Dataclass creation and immutability
- Field validation
- Type hints verification
- Default values
- Serialization/deserialization
"""

from dataclasses import FrozenInstanceError

import pytest


class TestRequestModel:
    """Test Request dataclass."""

    def test_request_creation(self) -> None:
        """Test creating Request with all fields."""
        from amplihack.api_client.models import Request

        request = Request(
            method="GET",
            url="https://api.example.com/users",
            headers={"Accept": "application/json"},
            params={"page": 1},
            body=None,
            timeout=30,
        )

        assert request.method == "GET"
        assert request.url == "https://api.example.com/users"
        assert request.headers == {"Accept": "application/json"}
        assert request.params == {"page": 1}
        assert request.body is None
        assert request.timeout == 30

    def test_request_with_defaults(self) -> None:
        """Test Request uses default values."""
        from amplihack.api_client.models import Request

        request = Request(method="GET", url="https://api.example.com/users")

        assert request.headers == {}
        assert request.params == {}
        assert request.body is None
        assert request.timeout == 30  # Default

    def test_request_immutability(self) -> None:
        """Test Request is immutable."""
        from amplihack.api_client.models import Request

        request = Request(method="GET", url="https://api.example.com/users")

        with pytest.raises(FrozenInstanceError):
            request.method = "POST"  # type: ignore

    def test_request_with_json_body(self) -> None:
        """Test Request with JSON body."""
        from amplihack.api_client.models import Request

        body = {"name": "Alice", "email": "alice@example.com"}
        request = Request(method="POST", url="https://api.example.com/users", body=body)

        assert request.body == body

    def test_request_type_hints(self) -> None:
        """Test Request has proper type hints."""
        import inspect

        from amplihack.api_client.models import Request

        sig = inspect.signature(Request.__init__)
        assert sig.parameters["method"].annotation is str
        assert sig.parameters["url"].annotation is str


class TestResponseModel:
    """Test Response dataclass."""

    def test_response_creation(self) -> None:
        """Test creating Response with all fields."""
        from amplihack.api_client.models import Response

        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body='{"id": 123, "name": "Alice"}',
            request=None,
            elapsed=0.123,
        )

        assert response.status_code == 200
        assert response.headers == {"Content-Type": "application/json"}
        assert response.body == '{"id": 123, "name": "Alice"}'
        assert response.elapsed == 0.123

    def test_response_immutability(self) -> None:
        """Test Response is immutable."""
        from amplihack.api_client.models import Response

        response = Response(status_code=200, headers={}, body="test")

        with pytest.raises(FrozenInstanceError):
            response.status_code = 404  # type: ignore

    def test_response_ok_property(self) -> None:
        """Test Response.ok property for success status."""
        from amplihack.api_client.models import Response

        success_response = Response(status_code=200, headers={}, body="")
        assert success_response.ok is True

        error_response = Response(status_code=500, headers={}, body="")
        assert error_response.ok is False

    def test_response_json_method(self) -> None:
        """Test Response.json() parses JSON body."""
        import json

        from amplihack.api_client.models import Response

        body = json.dumps({"id": 123, "name": "Alice"})
        response = Response(status_code=200, headers={}, body=body)

        data = response.json()
        assert data["id"] == 123
        assert data["name"] == "Alice"

    def test_response_text_property(self) -> None:
        """Test Response.text returns body as string."""
        from amplihack.api_client.models import Response

        response = Response(status_code=200, headers={}, body="Hello, World!")

        assert response.text == "Hello, World!"

    def test_response_with_request(self) -> None:
        """Test Response preserves original request."""
        from amplihack.api_client.models import Request, Response

        request = Request(method="GET", url="https://api.example.com/users")
        response = Response(status_code=200, headers={}, body="", request=request)

        assert response.request == request
        assert response.request.url == "https://api.example.com/users"


class TestClientConfig:
    """Test ClientConfig dataclass."""

    def test_client_config_creation(self) -> None:
        """Test creating ClientConfig with all fields."""
        from amplihack.api_client.models import ClientConfig

        config = ClientConfig(
            base_url="https://api.example.com",
            timeout=30,
            connect_timeout=10,
            max_retries=3,
            retry_backoff_factor=0.5,
            rate_limit_per_second=10,
            verify_ssl=True,
        )

        assert config.base_url == "https://api.example.com"
        assert config.timeout == 30
        assert config.connect_timeout == 10
        assert config.max_retries == 3
        assert config.retry_backoff_factor == 0.5
        assert config.rate_limit_per_second == 10
        assert config.verify_ssl is True

    def test_client_config_defaults(self) -> None:
        """Test ClientConfig default values."""
        from amplihack.api_client.models import ClientConfig

        config = ClientConfig(base_url="https://api.example.com")

        assert config.timeout == 30
        assert config.connect_timeout == 10
        assert config.max_retries == 3
        assert config.retry_backoff_factor == 0.5
        assert config.rate_limit_per_second is None
        assert config.rate_limit_per_minute is None
        assert config.verify_ssl is True
        assert config.allow_redirects is True
        assert config.max_redirects == 5

    def test_client_config_retry_statuses_default(self) -> None:
        """Test ClientConfig default retry statuses."""
        from amplihack.api_client.models import ClientConfig

        config = ClientConfig(base_url="https://api.example.com")

        assert config.retry_statuses == [429, 500, 502, 503, 504]

    def test_client_config_validation(self) -> None:
        """Test ClientConfig validates invalid values."""
        from amplihack.api_client.models import ClientConfig

        # Negative timeout should raise error
        with pytest.raises(ValueError):
            ClientConfig(base_url="https://api.example.com", timeout=-1)

        # Negative max_retries should raise error
        with pytest.raises(ValueError):
            ClientConfig(base_url="https://api.example.com", max_retries=-1)


class TestRetryPolicy:
    """Test RetryPolicy dataclass."""

    def test_retry_policy_creation(self) -> None:
        """Test creating RetryPolicy."""
        from amplihack.api_client.models import RetryPolicy

        policy = RetryPolicy(
            max_attempts=3,
            backoff_factor=0.5,
            backoff_max=60,
            jitter=True,
            retry_on_statuses=[429, 500, 502, 503, 504],
            retry_on_exceptions=[ConnectionError, TimeoutError],
        )

        assert policy.max_attempts == 3
        assert policy.backoff_factor == 0.5
        assert policy.backoff_max == 60
        assert policy.jitter is True
        assert 429 in policy.retry_on_statuses
        assert ConnectionError in policy.retry_on_exceptions

    def test_retry_policy_defaults(self) -> None:
        """Test RetryPolicy default values."""
        from amplihack.api_client.models import RetryPolicy

        policy = RetryPolicy()

        assert policy.max_attempts == 3
        assert policy.backoff_factor == 0.5
        assert policy.backoff_max == 60
        assert policy.jitter is True
        assert policy.retry_on_statuses == [429, 500, 502, 503, 504]
        assert ConnectionError in policy.retry_on_exceptions
        assert TimeoutError in policy.retry_on_exceptions

    def test_retry_policy_calculate_backoff(self) -> None:
        """Test RetryPolicy calculates backoff time."""
        from amplihack.api_client.models import RetryPolicy

        policy = RetryPolicy(backoff_factor=1.0, backoff_max=60, jitter=False)

        # Exponential backoff: attempt 1 = 1s, attempt 2 = 2s, attempt 3 = 4s
        assert policy.calculate_backoff(1) == 1.0
        assert policy.calculate_backoff(2) == 2.0
        assert policy.calculate_backoff(3) == 4.0

    def test_retry_policy_backoff_max(self) -> None:
        """Test RetryPolicy respects maximum backoff."""
        from amplihack.api_client.models import RetryPolicy

        policy = RetryPolicy(backoff_factor=1.0, backoff_max=10, jitter=False)

        # Should cap at backoff_max
        assert policy.calculate_backoff(10) <= 10

    def test_retry_policy_with_jitter(self) -> None:
        """Test RetryPolicy adds jitter to backoff."""
        from amplihack.api_client.models import RetryPolicy

        policy = RetryPolicy(backoff_factor=1.0, jitter=True)

        backoff = policy.calculate_backoff(1)

        # With jitter, backoff should be in expected range
        assert backoff >= 0.5  # At least 50% of base
        assert backoff <= 1.5  # At most 150% of base


class TestRateLimiter:
    """Test RateLimiter dataclass/model."""

    def test_rate_limiter_creation(self) -> None:
        """Test creating RateLimiter."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=10, requests_per_minute=500)

        assert limiter.requests_per_second == 10
        assert limiter.requests_per_minute == 500

    def test_rate_limiter_allows_request(self) -> None:
        """Test RateLimiter.allows_request() checks rate limits."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=2)

        # First request should be allowed
        assert limiter.allows_request() is True

    def test_rate_limiter_wait_time(self) -> None:
        """Test RateLimiter calculates wait time."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=2)

        # After hitting limit, should return wait time
        wait = limiter.wait_time()
        assert wait >= 0


class TestAuthModels:
    """Test authentication-related models."""

    def test_bearer_auth_creation(self) -> None:
        """Test BearerAuth model."""
        from amplihack.api_client.models import BearerAuth

        auth = BearerAuth(token="test_token_123")
        assert auth.token == "test_token_123"

    def test_api_key_auth_creation(self) -> None:
        """Test APIKeyAuth model."""
        from amplihack.api_client.models import APIKeyAuth

        auth = APIKeyAuth(key="test_key_123", location="header", name="X-API-Key")
        assert auth.key == "test_key_123"
        assert auth.location == "header"
        assert auth.name == "X-API-Key"

    def test_api_key_auth_defaults(self) -> None:
        """Test APIKeyAuth default values."""
        from amplihack.api_client.models import APIKeyAuth

        auth = APIKeyAuth(key="test_key")
        assert auth.location == "header"
        assert auth.name == "X-API-Key"


class TestDataclassImmutability:
    """Test all dataclasses are properly frozen."""

    def test_all_models_are_frozen(self) -> None:
        """Test all dataclass models are immutable."""
        from amplihack.api_client.models import Request, Response

        request = Request(method="GET", url="https://api.example.com")
        response = Response(status_code=200, headers={}, body="")

        with pytest.raises(FrozenInstanceError):
            request.method = "POST"  # type: ignore

        with pytest.raises(FrozenInstanceError):
            response.status_code = 404  # type: ignore
