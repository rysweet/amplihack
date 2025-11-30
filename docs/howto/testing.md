# How to Test with Mock Servers

Learn how to test your API client code using mock servers and testing utilities.

## Why Mock API Calls?

Mock API calls to:

- Test without external dependencies
- Control test data precisely
- Test error conditions
- Run tests quickly and reliably
- Test in CI/CD environments

## Basic Mocking with unittest.mock

### Mocking Responses

```python
import unittest
from unittest.mock import Mock, patch
from rest_api_client import APIClient
from rest_api_client.models import Response

class TestAPIClient(unittest.TestCase):
    def setUp(self):
        self.client = APIClient(base_url="https://api.example.com")

    def test_successful_get_request(self):
        """Test successful GET request."""
        # Create a mock response
        mock_response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            data={"id": 1, "name": "Test User"}
        )

        # Mock the request method
        with patch.object(self.client, 'request', return_value=mock_response):
            response = self.client.get("/users/1")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["name"], "Test User")

    def test_error_handling(self):
        """Test error response handling."""
        from rest_api_client.exceptions import ServerError

        # Mock a server error
        with patch.object(self.client, 'request') as mock_request:
            mock_request.side_effect = ServerError("Internal Server Error", status_code=500)

            with self.assertRaises(ServerError) as context:
                self.client.get("/users/1")

            self.assertEqual(context.exception.status_code, 500)
```

### Mocking the Session

```python
import requests_mock
from rest_api_client import APIClient

def test_with_requests_mock():
    """Test using requests-mock library."""
    client = APIClient(base_url="https://api.example.com")

    with requests_mock.Mocker() as m:
        # Mock the endpoint
        m.get("https://api.example.com/users/1", json={"id": 1, "name": "Alice"})

        # Make the request
        response = client.get("/users/1")

        assert response.data["name"] == "Alice"
        assert m.called
        assert m.call_count == 1
```

## Using pytest Fixtures

### Client Fixture

```python
import pytest
from unittest.mock import Mock, patch
from rest_api_client import APIClient
from rest_api_client.models import Response

@pytest.fixture
def api_client():
    """Create a test API client."""
    return APIClient(base_url="https://api.example.com")

@pytest.fixture
def mock_response():
    """Create a mock response factory."""
    def _make_response(status_code=200, data=None, headers=None):
        return Response(
            status_code=status_code,
            headers=headers or {},
            data=data or {}
        )
    return _make_response

def test_get_request(api_client, mock_response):
    """Test GET request with fixtures."""
    expected_response = mock_response(data={"test": "data"})

    with patch.object(api_client, 'request', return_value=expected_response):
        response = api_client.get("/test")
        assert response.data == {"test": "data"}
```

### Parametrized Tests

```python
import pytest
from rest_api_client.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    RateLimitError,
    ServerError
)

@pytest.mark.parametrize("status_code,exception_class", [
    (400, ValidationError),
    (401, AuthenticationError),
    (403, AuthorizationError),
    (429, RateLimitError),
    (500, ServerError),
])
def test_error_handling(api_client, status_code, exception_class):
    """Test different error responses."""
    with patch.object(api_client, 'request') as mock_request:
        mock_request.side_effect = exception_class("Test error", status_code=status_code)

        with pytest.raises(exception_class) as exc_info:
            api_client.get("/test")

        assert exc_info.value.status_code == status_code
```

## Creating a Mock Server

### Using Flask for Testing

```python
import threading
from flask import Flask, jsonify, request
from werkzeug.serving import make_server
from rest_api_client import APIClient

class MockAPIServer:
    """Mock API server for testing."""

    def __init__(self, port=5555):
        self.port = port
        self.app = Flask(__name__)
        self.server = None
        self.thread = None
        self._setup_routes()

    def _setup_routes(self):
        """Set up mock API routes."""
        @self.app.route('/users/<int:user_id>')
        def get_user(user_id):
            return jsonify({
                "id": user_id,
                "name": f"User {user_id}",
                "email": f"user{user_id}@example.com"
            })

        @self.app.route('/users', methods=['POST'])
        def create_user():
            data = request.json
            return jsonify({
                "id": 123,
                "name": data.get("name"),
                "email": data.get("email")
            }), 201

        @self.app.route('/error')
        def error_endpoint():
            return jsonify({"error": "Something went wrong"}), 500

    def start(self):
        """Start the mock server."""
        self.server = make_server('127.0.0.1', self.port, self.app)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """Stop the mock server."""
        if self.server:
            self.server.shutdown()

# Usage in tests
import pytest

@pytest.fixture(scope="session")
def mock_server():
    """Create and start mock server for tests."""
    server = MockAPIServer()
    server.start()
    yield server
    server.stop()

def test_with_mock_server(mock_server):
    """Test against mock server."""
    client = APIClient(base_url=f"http://127.0.0.1:{mock_server.port}")

    # Test GET request
    response = client.get("/users/1")
    assert response.data["name"] == "User 1"

    # Test POST request
    response = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})
    assert response.status_code == 201
    assert response.data["name"] == "Alice"

    # Test error handling
    with pytest.raises(Exception):
        client.get("/error")
```

## Testing Retry Logic

### Mock Retry Behavior

```python
import time
from unittest.mock import Mock, patch
from rest_api_client import APIClient
from rest_api_client.config import RetryConfig
from rest_api_client.exceptions import ServerError

def test_retry_logic():
    """Test that client retries on failure."""
    retry_config = RetryConfig(
        max_attempts=3,
        initial_delay=0.1  # Short delay for testing
    )

    client = APIClient(
        base_url="https://api.example.com",
        retry_config=retry_config
    )

    # Mock request to fail twice, then succeed
    attempts = []
    def mock_request(*args, **kwargs):
        attempts.append(time.time())
        if len(attempts) < 3:
            raise ServerError("Server error", status_code=500)
        return Response(status_code=200, headers={}, data={"success": True})

    with patch.object(client, 'request', side_effect=mock_request):
        response = client.get("/test")

        assert response.data["success"] is True
        assert len(attempts) == 3  # Should have tried 3 times

        # Check that delays were applied
        if len(attempts) > 1:
            delay1 = attempts[1] - attempts[0]
            assert delay1 >= 0.1  # At least initial delay
```

### Test Exponential Backoff

```python
def test_exponential_backoff():
    """Test exponential backoff calculation."""
    from rest_api_client.config import RetryConfig

    config = RetryConfig(
        initial_delay=1.0,
        exponential_base=2.0,
        max_delay=60.0
    )

    # Test delay calculation
    assert config.calculate_delay(0) == 1.0   # 1 * 2^0 = 1
    assert config.calculate_delay(1) == 2.0   # 1 * 2^1 = 2
    assert config.calculate_delay(2) == 4.0   # 1 * 2^2 = 4
    assert config.calculate_delay(10) == 60.0  # Capped at max_delay
```

## Testing Rate Limiting

### Mock Rate Limiter

```python
import time
from unittest.mock import Mock, patch
from rest_api_client import APIClient
from rest_api_client.rate_limiter import RateLimiter

def test_rate_limiting():
    """Test that rate limiter throttles requests."""
    client = APIClient(
        base_url="https://api.example.com",
        rate_limit_calls=2,
        rate_limit_period=1  # 2 calls per second
    )

    # Track request times
    request_times = []

    def mock_request(*args, **kwargs):
        request_times.append(time.time())
        return Response(status_code=200, headers={}, data={})

    with patch.object(client, 'request', side_effect=mock_request):
        # Make 3 requests quickly
        for _ in range(3):
            client.get("/test")

        # First 2 should be immediate, 3rd should be delayed
        assert len(request_times) == 3

        # Check timing
        delay_between_2_and_3 = request_times[2] - request_times[1]
        assert delay_between_2_and_3 >= 0.5  # Should wait ~0.5s
```

## Testing Async Clients

### Async Test Setup

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from rest_api_client import AsyncAPIClient
from rest_api_client.models import Response

@pytest.mark.asyncio
async def test_async_get_request():
    """Test async GET request."""
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        mock_response = Response(
            status_code=200,
            headers={},
            data={"async": "data"}
        )

        # Mock the async request
        client.request = AsyncMock(return_value=mock_response)

        response = await client.get("/test")
        assert response.data["async"] == "data"

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test multiple concurrent requests."""
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        # Mock responses
        client.request = AsyncMock(side_effect=[
            Response(status_code=200, headers={}, data={"id": 1}),
            Response(status_code=200, headers={}, data={"id": 2}),
            Response(status_code=200, headers={}, data={"id": 3})
        ])

        # Make concurrent requests
        responses = await asyncio.gather(
            client.get("/test1"),
            client.get("/test2"),
            client.get("/test3")
        )

        assert len(responses) == 3
        assert responses[0].data["id"] == 1
```

## Integration Testing

### Testing with Real API (Sandbox)

```python
import os
import pytest
from rest_api_client import APIClient

@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("SANDBOX_API_KEY"),
    reason="No sandbox API key provided"
)
def test_real_api_integration():
    """Test against real sandbox API."""
    client = APIClient(
        base_url="https://sandbox.api.example.com",
        headers={"X-API-Key": os.environ["SANDBOX_API_KEY"]}
    )

    # Test real endpoints
    response = client.get("/test")
    assert response.status_code == 200

    # Clean up test data
    test_data = client.post("/test-data", json={"test": True})
    client.delete(f"/test-data/{test_data.data['id']}")
```

## Test Utilities

### Response Builder

```python
class ResponseBuilder:
    """Builder for creating test responses."""

    def __init__(self):
        self.status_code = 200
        self.headers = {}
        self.data = {}

    def with_status(self, status_code):
        self.status_code = status_code
        return self

    def with_header(self, key, value):
        self.headers[key] = value
        return self

    def with_data(self, data):
        self.data = data
        return self

    def build(self):
        from rest_api_client.models import Response
        return Response(
            status_code=self.status_code,
            headers=self.headers,
            data=self.data
        )

# Usage
response = (
    ResponseBuilder()
    .with_status(201)
    .with_header("Location", "/users/123")
    .with_data({"id": 123, "created": True})
    .build()
)
```

### API Call Recorder

```python
class APICallRecorder:
    """Record API calls for verification."""

    def __init__(self, client):
        self.client = client
        self.calls = []
        self._original_request = client.request

    def start_recording(self):
        """Start recording calls."""
        def record_and_call(*args, **kwargs):
            self.calls.append({
                "method": args[0] if args else kwargs.get("method"),
                "endpoint": args[1] if len(args) > 1 else kwargs.get("endpoint"),
                "kwargs": kwargs
            })
            return self._original_request(*args, **kwargs)

        self.client.request = record_and_call

    def stop_recording(self):
        """Stop recording and restore original."""
        self.client.request = self._original_request

    def get_calls(self, method=None, endpoint=None):
        """Get recorded calls, optionally filtered."""
        calls = self.calls
        if method:
            calls = [c for c in calls if c["method"] == method]
        if endpoint:
            calls = [c for c in calls if c["endpoint"] == endpoint]
        return calls

# Usage
client = APIClient(base_url="https://api.example.com")
recorder = APICallRecorder(client)

recorder.start_recording()
client.get("/users")
client.post("/users", json={"name": "Alice"})
recorder.stop_recording()

# Verify calls
assert len(recorder.get_calls("GET")) == 1
assert len(recorder.get_calls("POST")) == 1
```

## Coverage Testing

```python
# Run tests with coverage
# pip install pytest-cov

# Command line:
# pytest --cov=rest_api_client tests/

# In pytest.ini or setup.cfg:
# [tool:pytest]
# addopts = --cov=rest_api_client --cov-report=html

def test_all_http_methods():
    """Ensure all HTTP methods are tested."""
    client = APIClient(base_url="https://api.example.com")
    methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

    for method in methods:
        with patch.object(client, 'request') as mock_request:
            mock_request.return_value = Response(
                status_code=200,
                headers={},
                data={}
            )

            # Call the method
            getattr(client, method.lower())("/test")

            # Verify it was called
            mock_request.assert_called_once()
```

## Best Practices

1. **Mock at the right level**: Mock external dependencies, not your own code
2. **Test both success and failure**: Include error cases and edge conditions
3. **Use fixtures**: Share common test setup with pytest fixtures
4. **Keep tests fast**: Use mocks instead of real network calls
5. **Test in isolation**: Each test should be independent
6. **Use descriptive names**: Test names should describe what they test
7. **Assert specific values**: Don't just check that it doesn't crash

## Summary

Testing with mock servers enables:

- Fast, reliable tests
- Complete control over test conditions
- Testing of error scenarios
- CI/CD integration
- High test coverage

Use these patterns to ensure your API client code works correctly without depending on external services.
