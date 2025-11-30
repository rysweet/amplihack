# REST API Client - Testing Guide

Complete guide to testing code that uses the REST API Client, including unit tests, integration tests, and end-to-end tests.

## Table of Contents

- [Testing Strategy](#testing-strategy)
- [Unit Testing](#unit-testing)
- [Integration Testing](#integration-testing)
- [End-to-End Testing](#end-to-end-testing)
- [Testing Utilities](#testing-utilities)
- [Test Fixtures](#test-fixtures)
- [Performance Testing](#performance-testing)
- [Best Practices](#best-practices)

## Testing Strategy

### Testing Pyramid

Follow the testing pyramid for comprehensive coverage:

```
         /\
        /E2E\      10% - End-to-end tests
       /------\
      /  INT   \   30% - Integration tests
     /----------\
    /   UNIT     \ 60% - Unit tests
   /--------------\
```

- **Unit Tests (60%)**: Test individual components in isolation
- **Integration Tests (30%)**: Test component interactions
- **E2E Tests (10%)**: Test complete workflows

## Unit Testing

### Basic Mocking

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from rest_api_client import APIClient, Response

class TestUserService:
    """Unit tests for UserService."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock API client."""
        client = Mock(spec=APIClient)
        return client

    def test_get_user(self, mock_client):
        """Test getting a user."""
        # Arrange
        mock_response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            data={"id": 123, "name": "John Doe"},
            elapsed_time=0.1
        )
        mock_client.get.return_value = mock_response

        # Act
        service = UserService(mock_client)
        user = service.get_user(123)

        # Assert
        assert user["id"] == 123
        assert user["name"] == "John Doe"
        mock_client.get.assert_called_once_with("/users/123")
```

### Testing Error Handling

```python
from rest_api_client import (
    APIClient,
    AuthenticationError,
    NotFoundError,
    RateLimitError
)

class TestErrorHandling:
    """Test error handling scenarios."""

    def test_handle_authentication_error(self, mock_client):
        """Test handling of authentication errors."""
        # Arrange
        mock_client.get.side_effect = AuthenticationError(
            message="Invalid token",
            status_code=401,
            response=None
        )

        # Act & Assert
        service = UserService(mock_client)
        with pytest.raises(AuthenticationError) as exc_info:
            service.get_user(123)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value)

    def test_handle_not_found(self, mock_client):
        """Test handling of 404 errors."""
        # Arrange
        mock_client.get.side_effect = NotFoundError(
            message="User not found",
            status_code=404,
            response=None
        )

        # Act
        service = UserService(mock_client)
        user = service.get_user_or_none(123)

        # Assert
        assert user is None
        mock_client.get.assert_called_once()

    def test_rate_limit_retry(self, mock_client):
        """Test rate limit retry logic."""
        # First call raises RateLimitError
        # Second call succeeds
        mock_client.get.side_effect = [
            RateLimitError(
                message="Rate limit exceeded",
                status_code=429,
                retry_after=1,
                response=None
            ),
            Response(
                status_code=200,
                headers={},
                data={"id": 123},
                elapsed_time=0.1
            )
        ]

        # Act
        service = UserService(mock_client)
        with patch("time.sleep"):  # Don't actually sleep in tests
            user = service.get_user_with_retry(123)

        # Assert
        assert user["id"] == 123
        assert mock_client.get.call_count == 2
```

### Mocking with patch

```python
class TestWithPatch:
    """Test using patch decorator."""

    @patch("my_module.APIClient")
    def test_service_initialization(self, mock_api_client_class):
        """Test service initialization."""
        # Arrange
        mock_instance = Mock()
        mock_api_client_class.return_value = mock_instance

        # Act
        service = UserService(base_url="https://api.example.com")

        # Assert
        mock_api_client_class.assert_called_once_with(
            base_url="https://api.example.com"
        )
        assert service.client == mock_instance

    @patch.object(APIClient, "get")
    def test_direct_method_patch(self, mock_get):
        """Test patching specific methods."""
        # Arrange
        mock_get.return_value = Response(
            status_code=200,
            headers={},
            data={"status": "ok"},
            elapsed_time=0.1
        )

        # Act
        client = APIClient(base_url="https://api.example.com")
        response = client.get("/status")

        # Assert
        assert response.data["status"] == "ok"
        mock_get.assert_called_once_with("/status")
```

## Integration Testing

### Using MockServer

```python
import pytest
from rest_api_client import APIClient, MockServer

class TestIntegration:
    """Integration tests with MockServer."""

    @pytest.fixture
    def mock_server(self):
        """Create and start mock server."""
        server = MockServer(port=8080)
        server.start()
        yield server
        server.stop()

    def test_full_crud_workflow(self, mock_server):
        """Test complete CRUD workflow."""
        # Configure mock responses
        mock_server.add_response(
            method="POST",
            path="/users",
            status=201,
            json={"id": 1, "name": "John Doe"}
        )
        mock_server.add_response(
            method="GET",
            path="/users/1",
            status=200,
            json={"id": 1, "name": "John Doe"}
        )
        mock_server.add_response(
            method="PUT",
            path="/users/1",
            status=200,
            json={"id": 1, "name": "Jane Doe"}
        )
        mock_server.add_response(
            method="DELETE",
            path="/users/1",
            status=204
        )

        # Create client
        client = APIClient(base_url=f"http://localhost:{mock_server.port}")

        # Test CREATE
        create_response = client.post("/users", json={"name": "John Doe"})
        assert create_response.status_code == 201
        user_id = create_response.data["id"]

        # Test READ
        get_response = client.get(f"/users/{user_id}")
        assert get_response.status_code == 200
        assert get_response.data["name"] == "John Doe"

        # Test UPDATE
        update_response = client.put(
            f"/users/{user_id}",
            json={"name": "Jane Doe"}
        )
        assert update_response.status_code == 200
        assert update_response.data["name"] == "Jane Doe"

        # Test DELETE
        delete_response = client.delete(f"/users/{user_id}")
        assert delete_response.status_code == 204

        # Verify request counts
        assert mock_server.request_count("/users") == 1
        assert mock_server.request_count(f"/users/{user_id}") == 3
```

### Testing Retry Logic

```python
def test_retry_on_server_error(mock_server):
    """Test that client retries on server errors."""
    # Configure server to fail twice then succeed
    mock_server.add_response_sequence(
        method="GET",
        path="/flaky",
        responses=[
            {"status": 500, "json": {"error": "Internal Server Error"}},
            {"status": 503, "json": {"error": "Service Unavailable"}},
            {"status": 200, "json": {"data": "success"}}
        ]
    )

    client = APIClient(
        base_url=f"http://localhost:{mock_server.port}",
        max_retries=3,
        retry_config=RetryConfig(initial_delay=0.1)  # Fast retry for tests
    )

    # Should succeed after retries
    response = client.get("/flaky")
    assert response.status_code == 200
    assert response.data["data"] == "success"

    # Verify all three attempts were made
    assert mock_server.request_count("/flaky") == 3
```

### Testing Rate Limiting

```python
def test_rate_limit_handling(mock_server):
    """Test rate limit handling."""
    # Configure rate limit response
    mock_server.add_response(
        method="GET",
        path="/limited",
        status=429,
        headers={
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + 60),
            "Retry-After": "2"
        },
        json={"error": "Rate limit exceeded"}
    )

    # Add success response for retry
    mock_server.add_response(
        method="GET",
        path="/limited",
        status=200,
        json={"data": "success"}
    )

    client = APIClient(
        base_url=f"http://localhost:{mock_server.port}",
        rate_limit_config=RateLimitConfig(respect_retry_after=True)
    )

    # Should handle rate limit and retry
    with patch("time.sleep") as mock_sleep:
        response = client.get("/limited")

    assert response.status_code == 200
    mock_sleep.assert_called_with(2)  # Should wait for Retry-After
```

## End-to-End Testing

### Real API Testing

```python
import pytest
import os

@pytest.mark.e2e
@pytest.mark.skipif(
    not os.getenv("RUN_E2E_TESTS"),
    reason="E2E tests only run when RUN_E2E_TESTS is set"
)
class TestE2E:
    """End-to-end tests against real API."""

    @pytest.fixture
    def client(self):
        """Create client for real API."""
        return APIClient(
            base_url=os.getenv("TEST_API_URL", "https://jsonplaceholder.typicode.com"),
            timeout=30
        )

    def test_real_api_workflow(self, client):
        """Test against real API."""
        # GET request
        response = client.get("/posts/1")
        assert response.status_code == 200
        assert "userId" in response.data

        # POST request
        new_post = {
            "title": "Test Post",
            "body": "Test content",
            "userId": 1
        }
        response = client.post("/posts", json=new_post)
        assert response.status_code == 201
        assert response.data["title"] == "Test Post"

    @pytest.mark.slow
    def test_large_payload(self, client):
        """Test with large payloads."""
        large_data = {"items": [{"id": i} for i in range(1000)]}

        response = client.post("/posts", json=large_data)
        assert response.status_code in [200, 201]
```

## Testing Utilities

### Custom Test Fixtures

```python
import pytest
from typing import Generator, Dict, Any

@pytest.fixture
def api_client() -> APIClient:
    """Provide configured API client."""
    return APIClient(
        base_url="https://test-api.example.com",
        timeout=5,
        max_retries=1
    )

@pytest.fixture
def mock_responses() -> Generator[Dict[str, Any], None, None]:
    """Provide mock response factory."""
    def create_response(status=200, data=None, headers=None):
        return Response(
            status_code=status,
            headers=headers or {},
            data=data or {},
            elapsed_time=0.1
        )

    yield create_response

@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Provide authentication headers."""
    return {"Authorization": "Bearer test-token"}
```

### Test Data Builders

```python
class UserBuilder:
    """Builder for test user data."""

    def __init__(self):
        self.user = {
            "id": 1,
            "name": "Test User",
            "email": "test@example.com",
            "role": "user"
        }

    def with_id(self, user_id: int):
        """Set user ID."""
        self.user["id"] = user_id
        return self

    def with_name(self, name: str):
        """Set user name."""
        self.user["name"] = name
        return self

    def with_role(self, role: str):
        """Set user role."""
        self.user["role"] = role
        return self

    def build(self) -> Dict[str, Any]:
        """Build user data."""
        return self.user.copy()

# Usage
def test_admin_user():
    admin = UserBuilder().with_role("admin").build()
    assert admin["role"] == "admin"
```

### Response Assertions

```python
class ResponseAssertions:
    """Custom assertions for API responses."""

    @staticmethod
    def assert_success(response: Response):
        """Assert successful response."""
        assert 200 <= response.status_code < 300, \
            f"Expected success status, got {response.status_code}"

    @staticmethod
    def assert_json_structure(response: Response, expected_keys: list):
        """Assert JSON response has expected structure."""
        assert isinstance(response.data, dict), "Response data is not a dict"
        for key in expected_keys:
            assert key in response.data, f"Missing key: {key}"

    @staticmethod
    def assert_error_response(response: Response, expected_status: int):
        """Assert error response structure."""
        assert response.status_code == expected_status
        assert "error" in response.data or "message" in response.data

# Usage
def test_user_endpoint(client):
    response = client.get("/users/123")
    ResponseAssertions.assert_success(response)
    ResponseAssertions.assert_json_structure(
        response,
        ["id", "name", "email"]
    )
```

## Test Fixtures

### Shared Test Data

```python
# conftest.py
import pytest
import json
from pathlib import Path

@pytest.fixture(scope="session")
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent / "test_data"

@pytest.fixture
def sample_users(test_data_dir):
    """Load sample user data."""
    with open(test_data_dir / "users.json") as f:
        return json.load(f)

@pytest.fixture
def error_responses(test_data_dir):
    """Load sample error responses."""
    with open(test_data_dir / "errors.json") as f:
        return json.load(f)
```

### Database Fixtures

```python
@pytest.fixture
def test_database():
    """Provide test database connection."""
    # Setup
    db = create_test_database()
    populate_test_data(db)

    yield db

    # Teardown
    db.cleanup()

@pytest.fixture
def transactional_db(test_database):
    """Provide database with transaction rollback."""
    test_database.begin_transaction()

    yield test_database

    test_database.rollback()
```

## Performance Testing

### Response Time Testing

```python
import time

def test_response_time(client):
    """Test API response times."""
    max_response_time = 1.0  # 1 second max

    start = time.time()
    response = client.get("/health")
    duration = time.time() - start

    assert response.status_code == 200
    assert duration < max_response_time, \
        f"Response took {duration:.2f}s, max is {max_response_time}s"
    assert response.elapsed_time < max_response_time
```

### Load Testing

```python
import concurrent.futures
import statistics

def test_concurrent_requests(client):
    """Test handling of concurrent requests."""
    num_requests = 100
    max_workers = 10

    def make_request(i):
        start = time.time()
        response = client.get(f"/users/{i % 10 + 1}")
        return time.time() - start, response.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(make_request, i) for i in range(num_requests)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    durations = [r[0] for r in results]
    statuses = [r[1] for r in results]

    # Assert all requests succeeded
    assert all(status == 200 for status in statuses)

    # Check performance metrics
    avg_duration = statistics.mean(durations)
    p95_duration = statistics.quantiles(durations, n=20)[18]  # 95th percentile

    assert avg_duration < 1.0, f"Average response time {avg_duration:.2f}s exceeds 1s"
    assert p95_duration < 2.0, f"P95 response time {p95_duration:.2f}s exceeds 2s"
```

### Memory Testing

```python
import tracemalloc

def test_memory_usage(client):
    """Test memory usage during operations."""
    tracemalloc.start()

    # Perform operations
    for i in range(100):
        response = client.get(f"/users/{i % 10 + 1}")

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Convert to MB
    current_mb = current / 1024 / 1024
    peak_mb = peak / 1024 / 1024

    assert peak_mb < 50, f"Peak memory usage {peak_mb:.1f}MB exceeds 50MB"
```

## Best Practices

### 1. Test Organization

```python
# tests/
# ├── unit/
# │   ├── test_client.py
# │   ├── test_retry.py
# │   └── test_rate_limit.py
# ├── integration/
# │   ├── test_workflow.py
# │   └── test_error_handling.py
# ├── e2e/
# │   └── test_real_api.py
# └── conftest.py  # Shared fixtures
```

### 2. Test Naming

```python
# Good test names
def test_get_user_returns_user_data():
    pass

def test_authentication_error_raises_exception():
    pass

def test_retry_on_500_error_succeeds_on_third_attempt():
    pass

# Bad test names
def test_1():
    pass

def test_user():
    pass

def test_error():
    pass
```

### 3. Test Independence

```python
# Good - Independent tests
def test_create_user(client):
    user = client.post("/users", json={"name": "Test"})
    assert user.data["id"] is not None
    # Clean up
    client.delete(f"/users/{user.data['id']}")

# Bad - Dependent tests
def test_create():
    global user_id
    response = client.post("/users", json={"name": "Test"})
    user_id = response.data["id"]  # Don't do this!

def test_delete():
    client.delete(f"/users/{user_id}")  # Depends on test_create
```

### 4. Assertion Messages

```python
# Good - Clear assertion messages
assert response.status_code == 200, \
    f"Expected status 200, got {response.status_code}: {response.data}"

assert len(users) > 0, \
    f"Expected at least one user, got {len(users)}"

# Bad - No context
assert response.status_code == 200
assert len(users) > 0
```

### 5. Mock Scope

```python
# Good - Mock at boundaries
@patch("my_service.APIClient")
def test_service(mock_client):
    # Test service logic, not HTTP details
    pass

# Bad - Mock too deep
@patch("requests.Session.request")
def test_too_deep(mock_request):
    # Testing implementation details
    pass
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=rest_api_client --cov-report=html

# Run specific test types
pytest tests/unit/
pytest tests/integration/
pytest -m e2e  # Run end-to-end tests

# Run with verbose output
pytest -v

# Run specific test
pytest tests/unit/test_client.py::test_get_user

# Run tests in parallel
pytest -n 4

# Run with specific markers
pytest -m "not slow"
```

## Test Configuration

```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -ra
    --strict-markers
    --ignore=docs
markers =
    slow: marks tests as slow
    e2e: marks end-to-end tests
    integration: marks integration tests
    unit: marks unit tests
```
