"""Pytest fixtures and configuration for API Client tests.

Provides:
- Mock HTTP server fixtures using responses library
- Sample request/response data
- APIClient test instances
"""

import sys
from pathlib import Path

# Add parent directory (scenarios/) to path so api_client can be imported
scenarios_dir = Path(__file__).parent.parent.parent
if str(scenarios_dir) not in sys.path:
    sys.path.insert(0, str(scenarios_dir))

from collections.abc import Generator

import pytest
import responses

# These imports will FAIL until implementation exists (TDD)
# from api_client import APIClient
# from api_client.models import Request, Response
# from api_client.exceptions import APIClientError


# =============================================================================
# Constants for Testing
# =============================================================================

TEST_BASE_URL = "https://api.example.com"
TEST_API_KEY = "test-api-key-12345"  # pragma: allowlist secret
TEST_TIMEOUT = 30


# =============================================================================
# Fixtures: Mock HTTP Responses
# =============================================================================


@pytest.fixture
def mock_responses() -> Generator[responses.RequestsMock, None, None]:
    """Activate responses mock for HTTP requests.

    This fixture ALWAYS activates responses mock. Tests using this fixture
    should NOT also use @responses.activate decorator.

    For tests that use @responses.activate, they can use responses.add()
    directly without needing this fixture.
    """
    # Always start the mock when this fixture is used
    responses.mock.start()
    responses.mock.assert_all_requests_are_fired = False
    try:
        yield responses.mock
    finally:
        responses.mock.stop()
        responses.mock.reset()


@pytest.fixture
def successful_get_response(mock_responses: responses.RequestsMock) -> responses.RequestsMock:
    """Mock a successful GET response."""
    # Add directly to responses module (works with @responses.activate)
    responses.add(
        responses.GET,
        f"{TEST_BASE_URL}/users/1",
        json={"id": 1, "name": "Test User", "email": "test@example.com"},
        status=200,
    )
    return mock_responses


@pytest.fixture
def successful_post_response(mock_responses: responses.RequestsMock) -> responses.RequestsMock:
    """Mock a successful POST response."""
    responses.add(
        responses.POST,
        f"{TEST_BASE_URL}/users",
        json={"id": 2, "name": "New User", "email": "new@example.com"},
        status=201,
    )
    return mock_responses


@pytest.fixture
def server_error_response(mock_responses: responses.RequestsMock) -> responses.RequestsMock:
    """Mock a 500 server error response."""
    responses.add(
        responses.GET,
        f"{TEST_BASE_URL}/error",
        json={"error": "Internal Server Error"},
        status=500,
    )
    return mock_responses


@pytest.fixture
def rate_limit_response(mock_responses: responses.RequestsMock) -> responses.RequestsMock:
    """Mock a 429 rate limit response with Retry-After header."""
    responses.add(
        responses.GET,
        f"{TEST_BASE_URL}/rate-limited",
        json={"error": "Too Many Requests"},
        status=429,
        headers={"Retry-After": "5"},
    )
    return mock_responses


@pytest.fixture
def not_found_response(mock_responses: responses.RequestsMock) -> responses.RequestsMock:
    """Mock a 404 not found response."""
    responses.add(
        responses.GET,
        f"{TEST_BASE_URL}/missing",
        json={"error": "Not Found"},
        status=404,
    )
    return mock_responses


@pytest.fixture
def timeout_response(mock_responses: responses.RequestsMock) -> responses.RequestsMock:
    """Mock a connection timeout."""
    from requests.exceptions import ConnectTimeout

    responses.add(
        responses.GET,
        f"{TEST_BASE_URL}/timeout",
        body=ConnectTimeout("Connection timed out"),
    )
    return mock_responses


@pytest.fixture
def connection_error_response(mock_responses: responses.RequestsMock) -> responses.RequestsMock:
    """Mock a connection error."""
    from requests.exceptions import ConnectionError as RequestsConnectionError

    responses.add(
        responses.GET,
        f"{TEST_BASE_URL}/connection-error",
        body=RequestsConnectionError("Failed to establish connection"),
    )
    return mock_responses


# =============================================================================
# Fixtures: Retry Scenarios
# =============================================================================


@pytest.fixture
def retry_then_success(mock_responses: responses.RequestsMock) -> responses.RequestsMock:
    """Mock failing twice then succeeding (for retry tests)."""
    # First two calls fail with 500
    responses.add(
        responses.GET,
        f"{TEST_BASE_URL}/flaky",
        json={"error": "Server Error"},
        status=500,
    )
    responses.add(
        responses.GET,
        f"{TEST_BASE_URL}/flaky",
        json={"error": "Server Error"},
        status=500,
    )
    # Third call succeeds
    responses.add(
        responses.GET,
        f"{TEST_BASE_URL}/flaky",
        json={"status": "success"},
        status=200,
    )
    return mock_responses


@pytest.fixture
def always_fails(mock_responses: responses.RequestsMock) -> responses.RequestsMock:
    """Mock endpoint that always fails (for max retry tests)."""
    for _ in range(5):  # More than max retries
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/always-fails",
            json={"error": "Server Error"},
            status=500,
        )
    return mock_responses


@pytest.fixture
def rate_limit_then_success(mock_responses: responses.RequestsMock) -> responses.RequestsMock:
    """Mock rate limit then success (for rate limit retry tests)."""
    responses.add(
        responses.GET,
        f"{TEST_BASE_URL}/rate-then-ok",
        json={"error": "Too Many Requests"},
        status=429,
        headers={"Retry-After": "1"},
    )
    responses.add(
        responses.GET,
        f"{TEST_BASE_URL}/rate-then-ok",
        json={"status": "success"},
        status=200,
    )
    return mock_responses


# =============================================================================
# Fixtures: Sample Data
# =============================================================================


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user data for POST/PUT requests."""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "role": "developer",
    }


@pytest.fixture
def sample_headers() -> dict:
    """Sample custom headers."""
    return {
        "X-Custom-Header": "custom-value",
        "Accept": "application/json",
    }


# =============================================================================
# Fixtures: Client Instances (will fail until implementation exists)
# =============================================================================


@pytest.fixture
def api_client():
    """Create a test API client instance.

    This fixture will FAIL until APIClient is implemented.
    """
    # Import here to get clear error on missing implementation
    from api_client import APIClient

    return APIClient(
        base_url=TEST_BASE_URL,
        api_key=TEST_API_KEY,
        timeout=TEST_TIMEOUT,
    )


@pytest.fixture
def api_client_no_retry():
    """Create an API client with retries disabled."""
    from api_client import APIClient

    return APIClient(
        base_url=TEST_BASE_URL,
        api_key=TEST_API_KEY,
        timeout=TEST_TIMEOUT,
        max_retries=0,
    )


@pytest.fixture
def api_client_custom_retry():
    """Create an API client with custom retry settings."""
    from api_client import APIClient

    return APIClient(
        base_url=TEST_BASE_URL,
        api_key=TEST_API_KEY,
        timeout=TEST_TIMEOUT,
        max_retries=5,
        retry_delay=0.5,
    )
