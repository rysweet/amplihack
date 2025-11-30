"""
Test suite for integration scenarios.

Tests end-to-end request flows with all features enabled, combined retry + rate
limiting scenarios, authentication integration, and real-world error scenarios.

Testing Philosophy:
- Integration tests combining multiple components
- End-to-end workflows
- Real-world usage patterns
- Mock server using responses library
"""

from unittest.mock import patch

import pytest
import responses

from amplihack.utils.api_client import (
    APIClient,
    APIRequest,
    HTTPError,
    RateLimitConfig,
    RequestError,
    RetryConfig,
    RetryExhaustedError,
)


class TestEndToEndRequestFlow:
    """Test complete request flows with all features enabled"""

    @responses.activate
    def test_complete_successful_flow(self):
        """Test complete flow: request → response with all features"""
        responses.add(
            responses.GET,
            "https://api.example.com/users/123",
            json={"id": 123, "name": "Alice", "email": "alice@example.com"},
            status=200,
            headers={"X-RateLimit-Remaining": "100"},
        )

        client = APIClient(
            base_url="https://api.example.com",
            timeout=30.0,
            verify_ssl=True,
            default_headers={"User-Agent": "TestClient/1.0"},
            retry_config=RetryConfig(max_retries=3, base_delay=1.0),
            rate_limit_config=RateLimitConfig(max_wait_time=300.0),
        )

        response = client.get("/users/123")

        assert response.status_code == 200
        assert response.data["id"] == 123
        assert response.data["name"] == "Alice"
        assert isinstance(response.elapsed_time, float)
        assert response.headers["X-RateLimit-Remaining"] == "100"

    @responses.activate
    def test_crud_operations_flow(self):
        """Test complete CRUD operation flow"""
        client = APIClient(
            base_url="https://api.example.com",
            default_headers={"Authorization": "Bearer token123"},
        )

        # CREATE
        responses.add(
            responses.POST,
            "https://api.example.com/users",
            json={"id": 456, "name": "Bob"},
            status=201,
        )

        create_response = client.post("/users", json={"name": "Bob"})
        assert create_response.status_code == 201
        user_id = create_response.data["id"]

        # READ
        responses.add(
            responses.GET,
            f"https://api.example.com/users/{user_id}",
            json={"id": user_id, "name": "Bob"},
            status=200,
        )

        read_response = client.get(f"/users/{user_id}")
        assert read_response.status_code == 200

        # UPDATE
        responses.add(
            responses.PUT,
            f"https://api.example.com/users/{user_id}",
            json={"id": user_id, "name": "Bob Updated"},
            status=200,
        )

        update_response = client.put(f"/users/{user_id}", json={"name": "Bob Updated"})
        assert update_response.status_code == 200

        # DELETE
        responses.add(
            responses.DELETE,
            f"https://api.example.com/users/{user_id}",
            status=204,
        )

        delete_response = client.delete(f"/users/{user_id}")
        assert delete_response.status_code == 204


class TestRetryAndRateLimitCombination:
    """Test combined retry and rate limiting scenarios"""

    @responses.activate
    def test_retry_then_rate_limit(self):
        """Test retry exhausted followed by rate limit"""
        # First request: 500 error (will retry)
        responses.add(responses.GET, "https://api.example.com/resource", status=500)

        # Second request: 500 error (will retry again)
        responses.add(responses.GET, "https://api.example.com/resource", status=500)

        # Third request: 429 rate limit
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "60"},
        )

        # Fourth request: success
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"success": True},
            status=200,
        )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
            rate_limit_config=RateLimitConfig(max_wait_time=120.0),
        )

        with patch("time.sleep"):
            response = client.get("/resource")

        assert response.status_code == 200
        assert len(responses.calls) == 4

    @responses.activate
    def test_rate_limit_then_server_error_then_success(self):
        """Test rate limit followed by server error followed by success"""
        # First: rate limited
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "1"},
        )

        # Second: server error (will retry)
        responses.add(responses.GET, "https://api.example.com/resource", status=503)

        # Third: success
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"data": "value"},
            status=200,
        )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
            rate_limit_config=RateLimitConfig(max_wait_time=10.0),
        )

        with patch("time.sleep"):
            response = client.get("/resource")

        assert response.status_code == 200

    @responses.activate
    def test_multiple_rate_limits_with_retry(self):
        """Test multiple rate limits interspersed with retries"""
        # Rate limit 1
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "1"},
        )

        # Server error (retry)
        responses.add(responses.GET, "https://api.example.com/resource", status=500)

        # Rate limit 2
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "1"},
        )

        # Success
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"success": True},
            status=200,
        )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=5, base_delay=0.1),
            rate_limit_config=RateLimitConfig(max_wait_time=10.0),
        )

        with patch("time.sleep"):
            response = client.get("/resource")

        assert response.status_code == 200


class TestAuthenticationIntegration:
    """Test authentication integration scenarios"""

    @responses.activate
    def test_bearer_token_authentication(self):
        """Test Bearer token authentication flow"""

        def request_callback(request):
            auth_header = request.headers.get("Authorization")
            if auth_header == "Bearer valid-token":
                return (200, {}, '{"authenticated": true}')
            return (401, {}, '{"error": "Unauthorized"}')

        responses.add_callback(
            responses.GET,
            "https://api.example.com/protected",
            callback=request_callback,
        )

        client = APIClient(
            base_url="https://api.example.com",
            default_headers={"Authorization": "Bearer valid-token"},
        )

        response = client.get("/protected")
        assert response.status_code == 200
        assert response.data["authenticated"] is True

    @responses.activate
    def test_api_key_authentication(self):
        """Test API key authentication flow"""

        def request_callback(request):
            api_key = request.headers.get("X-API-Key")
            if api_key == "secret-key-123":
                return (200, {}, '{"access": "granted"}')
            return (403, {}, '{"error": "Forbidden"}')

        responses.add_callback(
            responses.GET,
            "https://api.example.com/resource",
            callback=request_callback,
        )

        client = APIClient(
            base_url="https://api.example.com",
            default_headers={"X-API-Key": "secret-key-123"},
        )

        response = client.get("/resource")
        assert response.status_code == 200

    @responses.activate
    def test_authentication_failure_then_retry(self):
        """Test authentication failure followed by retry with new token"""
        # First attempt: unauthorized
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"error": "Token expired"},
            status=401,
        )

        client = APIClient(
            base_url="https://api.example.com",
            default_headers={"Authorization": "Bearer expired-token"},
        )

        with pytest.raises(HTTPError) as exc_info:
            client.get("/resource")

        assert exc_info.value.status_code == 401

        # Second attempt with new token
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"data": "success"},
            status=200,
        )

        client.default_headers["Authorization"] = "Bearer fresh-token"
        response = client.get("/resource")

        assert response.status_code == 200


class TestRealWorldErrorScenarios:
    """Test real-world error scenarios"""

    @responses.activate
    def test_intermittent_network_issues(self):
        """Test handling of intermittent network issues"""
        # Fail, fail, succeed pattern (common in flaky networks)
        responses.add(responses.GET, "https://api.example.com/resource", status=503)
        responses.add(responses.GET, "https://api.example.com/resource", status=503)
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"data": "recovered"},
            status=200,
        )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
        )

        with patch("time.sleep"):
            response = client.get("/resource")

        assert response.status_code == 200
        assert response.data["data"] == "recovered"

    @responses.activate
    def test_api_degradation_and_recovery(self):
        """Test API degradation (rate limits) and recovery"""
        # Heavy load: rate limited twice, then recovers
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "1"},
        )

        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "1"},
        )

        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"status": "recovered"},
            status=200,
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(max_wait_time=10.0),
        )

        with patch("time.sleep"):
            response = client.get("/resource")

        assert response.status_code == 200

    @responses.activate
    def test_server_restart_scenario(self):
        """Test server restart: multiple 502/503 then success"""
        # Simulates server being restarted
        responses.add(responses.GET, "https://api.example.com/resource", status=502)
        responses.add(responses.GET, "https://api.example.com/resource", status=503)
        responses.add(responses.GET, "https://api.example.com/resource", status=503)
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"status": "online"},
            status=200,
        )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_retries=5, base_delay=0.1),
        )

        with patch("time.sleep"):
            response = client.get("/resource")

        assert response.status_code == 200

    def test_complete_network_failure(self):
        """Test complete network failure (no retries help)"""
        client = APIClient(
            base_url="https://nonexistent-domain-12345.com",
            retry_config=RetryConfig(max_retries=2, base_delay=0.1),
        )

        with patch("time.sleep"):
            with pytest.raises(RetryExhaustedError) as exc_info:
                client.get("/resource")

        assert exc_info.value.attempts == 2
        assert isinstance(exc_info.value.last_error, RequestError)


class TestPaginationPatterns:
    """Test common pagination patterns"""

    @responses.activate
    def test_page_based_pagination(self):
        """Test page-based pagination pattern"""
        # Page 1
        responses.add(
            responses.GET,
            "https://api.example.com/users?page=1&limit=2",
            json={"users": [{"id": 1}, {"id": 2}], "has_more": True},
            status=200,
        )

        # Page 2
        responses.add(
            responses.GET,
            "https://api.example.com/users?page=2&limit=2",
            json={"users": [{"id": 3}, {"id": 4}], "has_more": False},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")

        all_users = []
        page = 1

        while True:
            response = client.get("/users", params={"page": page, "limit": 2})
            all_users.extend(response.data["users"])

            if not response.data["has_more"]:
                break

            page += 1

        assert len(all_users) == 4
        assert all_users[0]["id"] == 1
        assert all_users[3]["id"] == 4

    @responses.activate
    def test_cursor_based_pagination(self):
        """Test cursor-based pagination pattern"""
        # First page
        responses.add(
            responses.GET,
            "https://api.example.com/items",
            json={"items": [{"id": 1}], "next_cursor": "abc123"},
            status=200,
        )

        # Second page
        responses.add(
            responses.GET,
            "https://api.example.com/items?cursor=abc123",
            json={"items": [{"id": 2}], "next_cursor": None},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")

        all_items = []
        cursor = None

        while True:
            params = {"cursor": cursor} if cursor else {}
            response = client.get("/items", params=params)

            all_items.extend(response.data["items"])
            cursor = response.data.get("next_cursor")

            if not cursor:
                break

        assert len(all_items) == 2


class TestBatchOperations:
    """Test batch operation patterns"""

    @responses.activate
    def test_batch_create_with_error_handling(self):
        """Test batch create with individual error handling"""
        items = [{"name": "Item1"}, {"name": "Item2"}, {"name": "Item3"}]

        # Item1: success
        responses.add(
            responses.POST,
            "https://api.example.com/items",
            json={"id": 1, "name": "Item1"},
            status=201,
        )

        # Item2: failure
        responses.add(
            responses.POST,
            "https://api.example.com/items",
            json={"error": "Duplicate name"},
            status=400,
        )

        # Item3: success
        responses.add(
            responses.POST,
            "https://api.example.com/items",
            json={"id": 3, "name": "Item3"},
            status=201,
        )

        client = APIClient(base_url="https://api.example.com")

        results = []
        for item in items:
            try:
                response = client.post("/items", json=item)
                results.append({"success": True, "data": response.data})
            except HTTPError as e:
                results.append({"success": False, "error": str(e)})

        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert results[2]["success"] is True


class TestComplexWorkflows:
    """Test complex multi-step workflows"""

    @responses.activate
    def test_user_registration_workflow(self):
        """Test complete user registration workflow"""
        client = APIClient(base_url="https://api.example.com")

        # Step 1: Check if email is available
        responses.add(
            responses.GET,
            "https://api.example.com/users/check?email=test@example.com",
            json={"available": True},
            status=200,
        )

        check_response = client.get("/users/check", params={"email": "test@example.com"})
        assert check_response.data["available"] is True

        # Step 2: Create user
        responses.add(
            responses.POST,
            "https://api.example.com/users",
            json={"id": 123, "email": "test@example.com"},
            status=201,
        )

        create_response = client.post(
            "/users", json={"email": "test@example.com", "password": "secure123"}
        )
        user_id = create_response.data["id"]

        # Step 3: Send verification email
        responses.add(
            responses.POST,
            f"https://api.example.com/users/{user_id}/send-verification",
            json={"sent": True},
            status=200,
        )

        verify_response = client.post(f"/users/{user_id}/send-verification")
        assert verify_response.data["sent"] is True

    @responses.activate
    def test_file_upload_workflow(self):
        """Test file upload workflow with multipart form data"""
        client = APIClient(base_url="https://api.example.com")

        # Step 1: Get upload URL
        responses.add(
            responses.GET,
            "https://api.example.com/files/upload-url",
            json={"upload_url": "/files/upload", "file_id": "abc123"},
            status=200,
        )

        url_response = client.get("/files/upload-url")
        file_id = url_response.data["file_id"]

        # Step 2: Upload file
        responses.add(
            responses.POST,
            "https://api.example.com/files/upload",
            json={"file_id": file_id, "status": "uploaded"},
            status=200,
        )

        upload_response = client.post(
            "/files/upload", data={"file_id": file_id, "content": "file data"}
        )

        assert upload_response.data["status"] == "uploaded"


class TestAPIRequestDataclassIntegration:
    """Test APIRequest dataclass in integration scenarios"""

    @responses.activate
    def test_api_request_full_workflow(self):
        """Test complete workflow using APIRequest dataclass"""
        responses.add(
            responses.POST,
            "https://api.example.com/users?notify=true",
            json={"id": 456, "name": "Charlie"},
            status=201,
        )

        client = APIClient(base_url="https://api.example.com")

        request = APIRequest(
            method="POST",
            url="/users",
            headers={"Authorization": "Bearer token123", "Content-Type": "application/json"},
            params={"notify": "true"},
            json={"name": "Charlie", "email": "charlie@example.com"},
        )

        response = client.execute(request)

        assert response.status_code == 201
        assert response.data["id"] == 456

    @responses.activate
    def test_multiple_requests_with_dataclass(self):
        """Test multiple requests using APIRequest dataclass"""
        client = APIClient(base_url="https://api.example.com")

        requests_to_make = [
            APIRequest(method="GET", url="/users/1", headers={"Accept": "application/json"}),
            APIRequest(method="GET", url="/users/2", headers={"Accept": "application/json"}),
            APIRequest(method="GET", url="/users/3", headers={"Accept": "application/json"}),
        ]

        # Add responses
        for i in range(1, 4):
            responses.add(
                responses.GET,
                f"https://api.example.com/users/{i}",
                json={"id": i, "name": f"User{i}"},
                status=200,
            )

        results = []
        for request in requests_to_make:
            response = client.execute(request)
            results.append(response.data)

        assert len(results) == 3
        assert results[0]["id"] == 1
        assert results[2]["id"] == 3


class TestConcurrentRequests:
    """Test patterns for concurrent/parallel requests"""

    @responses.activate
    def test_sequential_requests_maintain_state(self):
        """Test sequential requests maintain proper state"""
        client = APIClient(
            base_url="https://api.example.com",
            default_headers={"X-Session": "session123"},
        )

        # Request 1
        responses.add(
            responses.GET,
            "https://api.example.com/step1",
            json={"token": "step1-token"},
            status=200,
        )

        response1 = client.get("/step1")
        token = response1.data["token"]

        # Request 2 uses token from request 1
        responses.add(
            responses.GET,
            "https://api.example.com/step2",
            json={"result": "success"},
            status=200,
        )

        response2 = client.get("/step2", headers={"X-Token": token})

        assert response2.status_code == 200
        assert response2.data["result"] == "success"


class TestErrorRecoveryPatterns:
    """Test error recovery patterns"""

    @responses.activate
    def test_fallback_to_alternative_endpoint(self):
        """Test fallback to alternative endpoint on failure"""
        client = APIClient(base_url="https://api.example.com")

        # Primary endpoint fails
        responses.add(responses.GET, "https://api.example.com/primary/resource", status=500)

        try:
            client.get("/primary/resource")
        except HTTPError:
            # Fallback to alternative
            responses.add(
                responses.GET,
                "https://api.example.com/fallback/resource",
                json={"data": "from_fallback"},
                status=200,
            )

            response = client.get("/fallback/resource")
            assert response.status_code == 200
            assert response.data["data"] == "from_fallback"
