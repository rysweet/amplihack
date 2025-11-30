# Testing Guide

Comprehensive guide for testing applications that use the REST API Client.

## Contents

- [Testing Strategy](#testing-strategy)
- [Unit Testing](#unit-testing)
- [Integration Testing](#integration-testing)
- [Mock Testing](#mock-testing)
- [Test Fixtures](#test-fixtures)
- [Testing Patterns](#testing-patterns)
- [Performance Testing](#performance-testing)
- [End-to-End Testing](#end-to-end-testing)
- [Continuous Integration](#continuous-integration)

## Testing Strategy

### Testing Pyramid

Follow the testing pyramid approach:

```
       /\
      /E2E\     10% - End-to-end tests
     /------\
    /  INT   \  30% - Integration tests
   /----------\
  /    UNIT    \ 60% - Unit tests
 /--------------\
```

### Test Organization

```
tests/
├── unit/              # Fast, isolated tests
│   ├── test_client.py
│   ├── test_response.py
│   └── test_retry.py
├── integration/       # Tests with real API calls
│   ├── test_github_api.py
│   └── test_weather_api.py
├── e2e/              # Complete workflow tests
│   └── test_full_workflow.py
├── fixtures/         # Test data and mocks
│   ├── responses.json
│   └── mock_server.py
└── conftest.py      # Shared pytest fixtures
```

## Unit Testing

### Basic Unit Tests

```python
# test_client.py
import unittest
from unittest.mock import Mock, patch
from api_client import RESTClient, Response

class TestRESTClient(unittest.TestCase):
    """Unit tests for REST API Client."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = RESTClient("https://api.example.com")

    def test_initialization(self):
        """Test client initialization."""
        assert self.client.base_url == "https://api.example.com"
        assert self.client.timeout == 30
        assert self.client.max_retries == 3
        assert self.client.rate_limit == 10

    def test_url_construction(self):
        """Test URL path joining."""
        url = self.client._build_url("/users/123")
        assert url == "https://api.example.com/users/123"

        # Test with trailing slash
        client = RESTClient("https://api.example.com/")
        url = client._build_url("/users/123")
        assert url == "https://api.example.com/users/123"

    @patch('urllib.request.urlopen')
    def test_get_request(self, mock_urlopen):
        """Test GET request."""
        # Mock response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.read.return_value = b'{"id": 123, "name": "Test"}'
        mock_urlopen.return_value = mock_response

        # Make request
        response = self.client.get("/users/123")

        # Verify
        assert response.status_code == 200
        assert response.json() == {"id": 123, "name": "Test"}
        mock_urlopen.assert_called_once()

    @patch('urllib.request.urlopen')
    def test_post_request(self, mock_urlopen):
        """Test POST request with JSON body."""
        # Mock response
        mock_response = Mock()
        mock_response.status = 201
        mock_response.headers = {}
        mock_response.read.return_value = b'{"id": 456}'
        mock_urlopen.return_value = mock_response

        # Make request
        data = {"name": "New User"}
        response = self.client.post("/users", json=data)

        # Verify
        assert response.status_code == 201
        assert response.json()["id"] == 456

class TestResponse(unittest.TestCase):
    """Unit tests for Response class."""

    def test_json_parsing(self):
        """Test JSON response parsing."""
        response = Response(
            status_code=200,
            headers={},
            body=b'{"key": "value"}',
            url="https://api.example.com"
        )

        data = response.json()
        assert data == {"key": "value"}

    def test_invalid_json(self):
        """Test handling of invalid JSON."""
        response = Response(
            status_code=200,
            headers={},
            body=b'not json',
            url="https://api.example.com"
        )

        with self.assertRaises(json.JSONDecodeError):
            response.json()

if __name__ == "__main__":
    unittest.main()
```

### Testing Rate Limiting

```python
# test_rate_limiting.py
import time
import unittest
from unittest.mock import patch, Mock
from api_client import RESTClient

class TestRateLimiting(unittest.TestCase):
    """Test rate limiting functionality."""

    @patch('urllib.request.urlopen')
    def test_rate_limit_enforcement(self, mock_urlopen):
        """Test that rate limiting is enforced."""
        # Setup
        client = RESTClient("https://api.example.com", rate_limit=2)  # 2 req/sec

        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b'{}'
        mock_urlopen.return_value = mock_response

        # Make rapid requests
        start_time = time.time()
        for i in range(4):
            client.get(f"/test/{i}")
        elapsed = time.time() - start_time

        # Should take at least 1.5 seconds for 4 requests at 2 req/sec
        assert elapsed >= 1.5, f"Rate limiting not enforced: {elapsed}s"

    def test_rate_limit_calculation(self):
        """Test rate limit timing calculations."""
        client = RESTClient("https://api.example.com", rate_limit=10)

        # Calculate delay between requests
        delay = client._calculate_delay()
        assert abs(delay - 0.1) < 0.01  # 10 req/sec = 0.1s delay

        # Test different rate
        client.rate_limit = 5
        delay = client._calculate_delay()
        assert abs(delay - 0.2) < 0.01  # 5 req/sec = 0.2s delay
```

## Integration Testing

### Testing with Real APIs

```python
# test_integration.py
import pytest
from api_client import RESTClient

@pytest.mark.integration
class TestGitHubIntegration:
    """Integration tests with GitHub API."""

    @pytest.fixture
    def client(self):
        """Create GitHub API client."""
        return RESTClient("https://api.github.com", rate_limit=1)

    def test_get_public_repo(self, client):
        """Test fetching public repository."""
        response = client.get("/repos/python/cpython")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "cpython"
        assert data["owner"]["login"] == "python"

    def test_list_commits(self, client):
        """Test listing repository commits."""
        response = client.get(
            "/repos/python/cpython/commits",
            params={"per_page": 5}
        )

        assert response.status_code == 200
        commits = response.json()
        assert len(commits) <= 5
        assert all("sha" in commit for commit in commits)

    def test_rate_limit_headers(self, client):
        """Test rate limit header handling."""
        response = client.get("/rate_limit")

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
```

### Testing Error Scenarios

```python
# test_error_handling.py
import pytest
from unittest.mock import patch
from api_client import RESTClient

class TestErrorHandling:
    """Test error handling in integration scenarios."""

    @pytest.fixture
    def client(self):
        return RESTClient("https://api.example.com")

    def test_404_handling(self, client):
        """Test handling of 404 responses."""
        with patch('urllib.request.urlopen') as mock:
            mock.side_effect = urllib.error.HTTPError(
                url="https://api.example.com/missing",
                code=404,
                msg="Not Found",
                hdrs={},
                fp=None
            )

            response = client.get("/missing")
            assert response.status_code == 404

    def test_timeout_handling(self, client):
        """Test timeout error handling."""
        with patch('urllib.request.urlopen') as mock:
            mock.side_effect = TimeoutError("Request timed out")

            with pytest.raises(TimeoutError):
                client.get("/slow-endpoint")

    def test_connection_error(self, client):
        """Test connection error handling."""
        with patch('urllib.request.urlopen') as mock:
            mock.side_effect = ConnectionError("Connection refused")

            with pytest.raises(ConnectionError):
                client.get("/endpoint")
```

## Mock Testing

### Creating Mock API Server

```python
# fixtures/mock_server.py
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading

class MockAPIHandler(BaseHTTPRequestHandler):
    """Mock API server for testing."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/users/123":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"id": 123, "name": "Test User"}
            self.wfile.write(json.dumps(response).encode())

        elif self.path == "/error":
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Server Error")

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)

        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {"created": True, "data": json.loads(body)}
        self.wfile.write(json.dumps(response).encode())

def start_mock_server(port=8888):
    """Start mock API server in background thread."""
    server = HTTPServer(('localhost', port), MockAPIHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server

# Usage in tests
@pytest.fixture(scope="session")
def mock_api_server():
    """Fixture to provide mock API server."""
    server = start_mock_server(8888)
    yield f"http://localhost:8888"
    server.shutdown()
```

### Testing with Mock Server

```python
# test_with_mock.py
import pytest
from api_client import RESTClient

def test_with_mock_server(mock_api_server):
    """Test client with mock API server."""
    client = RESTClient(mock_api_server)

    # Test successful GET
    response = client.get("/users/123")
    assert response.status_code == 200
    assert response.json()["name"] == "Test User"

    # Test POST
    response = client.post("/users", json={"name": "New User"})
    assert response.status_code == 201
    assert response.json()["created"] is True

    # Test 404
    response = client.get("/nonexistent")
    assert response.status_code == 404

    # Test server error
    response = client.get("/error")
    assert response.status_code == 500
```

## Test Fixtures

### Shared Fixtures

```python
# conftest.py
import pytest
import json
from pathlib import Path
from api_client import RESTClient, Response

@pytest.fixture
def sample_response():
    """Provide sample response object."""
    return Response(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=b'{"test": "data"}',
        url="https://api.example.com/test"
    )

@pytest.fixture
def test_data():
    """Load test data from JSON file."""
    data_file = Path(__file__).parent / "fixtures" / "test_data.json"
    with open(data_file) as f:
        return json.load(f)

@pytest.fixture
def authenticated_client():
    """Provide authenticated API client."""
    client = RESTClient("https://api.example.com")
    client.default_headers = {"Authorization": "Bearer test-token"}
    return client

@pytest.fixture
def slow_client():
    """Client configured for slow endpoints."""
    return RESTClient(
        "https://api.example.com",
        timeout=120,
        rate_limit=1
    )
```

### Response Fixtures

```python
# fixtures/responses.py
from api_client import Response

def success_response(data=None):
    """Create successful response fixture."""
    if data is None:
        data = {"success": True}
    return Response(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=json.dumps(data).encode(),
        url="https://api.example.com"
    )

def error_response(status_code=500, message="Error"):
    """Create error response fixture."""
    return Response(
        status_code=status_code,
        headers={},
        body=json.dumps({"error": message}).encode(),
        url="https://api.example.com"
    )

def rate_limit_response():
    """Create rate limit response fixture."""
    return Response(
        status_code=429,
        headers={"Retry-After": "60"},
        body=b'{"error": "Rate limited"}',
        url="https://api.example.com"
    )
```

## Testing Patterns

### Parameterized Testing

```python
# test_parameterized.py
import pytest
from api_client import RESTClient

@pytest.mark.parametrize("method,path,expected_status", [
    ("get", "/users", 200),
    ("get", "/users/123", 200),
    ("post", "/users", 201),
    ("put", "/users/123", 200),
    ("delete", "/users/123", 204),
])
def test_http_methods(mock_api_server, method, path, expected_status):
    """Test different HTTP methods."""
    client = RESTClient(mock_api_server)
    response = getattr(client, method)(path)
    assert response.status_code == expected_status

@pytest.mark.parametrize("status_code,should_retry", [
    (200, False),
    (400, False),
    (401, False),
    (429, True),
    (500, True),
    (502, True),
    (503, True),
])
def test_retry_logic(status_code, should_retry):
    """Test retry decision based on status code."""
    from api_client import should_retry_status
    assert should_retry_status(status_code) == should_retry
```

### Property-Based Testing

```python
# test_property.py
from hypothesis import given, strategies as st
from api_client import RESTClient

@given(
    base_url=st.text(min_size=1),
    timeout=st.integers(min_value=1, max_value=300),
    rate_limit=st.floats(min_value=0.1, max_value=100)
)
def test_client_properties(base_url, timeout, rate_limit):
    """Test client with random valid inputs."""
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"

    client = RESTClient(
        base_url=base_url,
        timeout=timeout,
        rate_limit=rate_limit
    )

    assert client.timeout == timeout
    assert client.rate_limit == rate_limit
    assert client.base_url == base_url
```

## Performance Testing

### Load Testing

```python
# test_performance.py
import time
import concurrent.futures
from api_client import RESTClient

def test_concurrent_requests(mock_api_server):
    """Test client under concurrent load."""
    client = RESTClient(mock_api_server, rate_limit=100)

    def make_request(i):
        response = client.get(f"/users/{i}")
        return response.status_code

    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request, i) for i in range(100)]
        results = [f.result() for f in futures]

    elapsed = time.time() - start_time

    assert all(status == 200 for status in results)
    assert elapsed < 10  # Should complete within 10 seconds

def test_rate_limit_performance():
    """Test rate limiting accuracy."""
    client = RESTClient("https://api.example.com", rate_limit=10)

    # Measure actual rate
    request_times = []

    for i in range(20):
        start = time.time()
        client._apply_rate_limit()
        request_times.append(time.time())

    # Calculate actual rate
    intervals = [request_times[i+1] - request_times[i]
                  for i in range(len(request_times)-1)]
    avg_interval = sum(intervals) / len(intervals)
    actual_rate = 1 / avg_interval

    # Should be close to configured rate
    assert abs(actual_rate - 10) < 1
```

## End-to-End Testing

### Complete Workflow Test

```python
# test_e2e.py
import pytest
from api_client import RESTClient

@pytest.mark.e2e
def test_complete_user_workflow():
    """Test complete user management workflow."""
    client = RESTClient("https://jsonplaceholder.typicode.com")

    # 1. List users
    response = client.get("/users")
    assert response.status_code == 200
    users = response.json()
    assert len(users) > 0

    # 2. Get specific user
    user_id = users[0]["id"]
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    user = response.json()
    assert user["id"] == user_id

    # 3. Create new user
    new_user = {
        "name": "Test User",
        "email": "test@example.com"
    }
    response = client.post("/users", json=new_user)
    assert response.status_code == 201
    created = response.json()
    assert "id" in created

    # 4. Update user
    update_data = {"email": "updated@example.com"}
    response = client.patch(f"/users/{user_id}", json=update_data)
    assert response.status_code == 200

    # 5. Delete user
    response = client.delete(f"/users/{user_id}")
    assert response.status_code in [200, 204]
```

## Continuous Integration

### GitHub Actions Configuration

```yaml
# .github/workflows/test.yml
name: Test REST API Client

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install pytest pytest-cov pytest-timeout hypothesis

      - name: Run unit tests
        run: |
          pytest tests/unit -v --cov=api_client

      - name: Run integration tests
        run: |
          pytest tests/integration -v -m integration

      - name: Run E2E tests
        run: |
          pytest tests/e2e -v -m e2e --timeout=60

      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml
```

### Test Configuration

```ini
# pytest.ini
[pytest]
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (may call real APIs)
    e2e: End-to-end tests (complete workflows)
    slow: Slow tests
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --tb=short
    -ra
```

### Coverage Configuration

```ini
# .coveragerc
[run]
source = api_client
omit =
    */tests/*
    */test_*.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
precision = 2

[html]
directory = htmlcov
```

## Best Practices

1. **Test in isolation** - Mock external dependencies
2. **Use fixtures** - Share common test setup
3. **Test edge cases** - Empty responses, large data, special characters
4. **Test failure modes** - Network errors, timeouts, invalid data
5. **Measure coverage** - Aim for >80% code coverage
6. **Test performance** - Ensure rate limiting works
7. **Use CI/CD** - Run tests automatically on every change
8. **Document test requirements** - Make tests easy to run
9. **Keep tests fast** - Unit tests should run in seconds
10. **Test real APIs carefully** - Respect rate limits in integration tests
