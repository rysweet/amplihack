"""Integration tests for APIClient.

These tests simulate real API interactions using mock responses.
Tests the full request/response cycle with the actual implementation API.

Note: ResponseError and ClientError do NOT have response_headers attribute.
Note: APIResponse does NOT have request attribute attached.

Testing pyramid target: 30% integration tests
"""

import json
from unittest.mock import Mock, patch

import pytest


class TestFullRequestResponseCycle:
    """Integration tests for complete request/response cycles."""

    def test_full_get_json_response_cycle(self) -> None:
        """Test complete GET request with JSON response."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = json.dumps(
            {"users": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]}
        )
        mock_response.elapsed.total_seconds.return_value = 0.15

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response

            with APIClient(config) as client:
                response = client.get("/users")

                assert response.status_code == 200
                assert response.is_success
                assert len(response.json["users"]) == 2
                assert response.json["users"][0]["name"] == "John"

    def test_full_post_with_json_body(self) -> None:
        """Test complete POST request with JSON body and response."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {"Content-Type": "application/json", "Location": "/users/3"}
        mock_response.text = json.dumps(
            {"id": 3, "name": "Alice", "email": "alice@example.com"}
        )
        mock_response.elapsed.total_seconds.return_value = 0.2

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response

            with APIClient(config) as client:
                response = client.post(
                    "/users",
                    json_body={"name": "Alice", "email": "alice@example.com"},
                )

                assert response.status_code == 201
                assert response.is_success
                assert response.json["id"] == 3
                assert response.headers["Location"] == "/users/3"

    def test_full_put_update_cycle(self) -> None:
        """Test complete PUT update cycle."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = json.dumps(
            {"id": 1, "name": "John Updated", "email": "john.updated@example.com"}
        )
        mock_response.elapsed.total_seconds.return_value = 0.15

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response

            with APIClient(config) as client:
                response = client.put(
                    "/users/1",
                    json_body={"name": "John Updated", "email": "john.updated@example.com"},
                )

                assert response.status_code == 200
                assert response.json["name"] == "John Updated"

    def test_full_delete_cycle(self) -> None:
        """Test complete DELETE cycle."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.elapsed.total_seconds.return_value = 0.1

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response

            with APIClient(config) as client:
                response = client.delete("/users/1")

                assert response.status_code == 204
                assert response.is_success


class TestRetryScenarios:
    """Integration tests for retry scenarios."""

    def test_retry_success_after_transient_failure(self) -> None:
        """Test successful retry after transient 503 error."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        # First two requests fail, third succeeds
        responses = [
            Mock(
                status_code=503,
                headers={},
                text="Service Unavailable",
                elapsed=Mock(total_seconds=Mock(return_value=0.1)),
            ),
            Mock(
                status_code=503,
                headers={},
                text="Service Unavailable",
                elapsed=Mock(total_seconds=Mock(return_value=0.1)),
            ),
            Mock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                text='{"status": "ok"}',
                elapsed=Mock(total_seconds=Mock(return_value=0.15)),
            ),
        ]

        config = APIClientConfig(
            base_url="https://api.example.com",
            max_retries=3,
            backoff_base=0.01,
            backoff_max=0.1,
        )

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.side_effect = responses
            with patch("time.sleep"):
                with APIClient(config) as client:
                    response = client.get("/health")

                    assert response.status_code == 200
                    assert response.json == {"status": "ok"}

    def test_rate_limit_recovery(self) -> None:
        """Test recovery from rate limiting with Retry-After."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        responses = [
            Mock(
                status_code=429,
                headers={"Retry-After": "1"},
                text="Too Many Requests",
                elapsed=Mock(total_seconds=Mock(return_value=0.1)),
            ),
            Mock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                text='{"data": "success"}',
                elapsed=Mock(total_seconds=Mock(return_value=0.15)),
            ),
        ]

        config = APIClientConfig(
            base_url="https://api.example.com",
            max_retries=3,
            backoff_base=0.01,
            backoff_max=0.1,
        )

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.side_effect = responses
            with patch("time.sleep") as mock_sleep:
                with APIClient(config) as client:
                    response = client.get("/api/data")

                    assert response.status_code == 200
                    # Should have respected Retry-After
                    mock_sleep.assert_called()


class TestErrorScenarios:
    """Integration tests for error scenarios."""

    def test_client_error_with_json_error_body(self) -> None:
        """Test handling 4xx error with JSON error body."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import ClientError

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = json.dumps(
            {
                "error": "validation_error",
                "message": "Invalid email format",
                "field": "email",
            }
        )
        mock_response.elapsed.total_seconds.return_value = 0.1

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response

            with APIClient(config) as client:
                with pytest.raises(ClientError) as exc_info:
                    client.post("/users", json_body={"email": "invalid"})

                assert exc_info.value.status_code == 400
                # Should be able to parse error body
                error_body = json.loads(exc_info.value.response_body)
                assert error_body["error"] == "validation_error"

    def test_unauthorized_error(self) -> None:
        """Test handling 401 Unauthorized."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import ClientError

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.headers = {"WWW-Authenticate": "Bearer"}
        mock_response.text = '{"error": "unauthorized"}'
        mock_response.elapsed.total_seconds.return_value = 0.1

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response

            with APIClient(config) as client:
                with pytest.raises(ClientError) as exc_info:
                    client.get("/protected")

                assert exc_info.value.status_code == 401
                # Note: ClientError does NOT have response_headers attribute
                # We can verify the error has response_body though
                assert "unauthorized" in exc_info.value.response_body

    def test_not_found_error(self) -> None:
        """Test handling 404 Not Found."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import ClientError

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"error": "not_found", "resource": "user"}'
        mock_response.elapsed.total_seconds.return_value = 0.1

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response

            with APIClient(config) as client:
                with pytest.raises(ClientError) as exc_info:
                    client.get("/users/99999")

                assert exc_info.value.status_code == 404

    def test_server_error_after_exhausted_retries(self) -> None:
        """Test handling persistent 500 error.

        The implementation re-raises ServerError when retries are exhausted.
        """
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import ServerError

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.headers = {}
        mock_response.text = "Internal Server Error"
        mock_response.elapsed.total_seconds.return_value = 0.1

        config = APIClientConfig(
            base_url="https://api.example.com",
            max_retries=2,
            backoff_base=0.01,
            backoff_max=0.1,
        )

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response
            with patch("time.sleep"):
                with APIClient(config) as client:
                    with pytest.raises(ServerError):
                        client.get("/failing-endpoint")


class TestConfigurationIntegration:
    """Integration tests for configuration behavior."""

    def test_default_headers_applied_to_all_requests(self) -> None:
        """Test that config headers are applied to all requests."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.elapsed.total_seconds.return_value = 0.1

        config = APIClientConfig(
            base_url="https://api.example.com",
            default_headers={
                "Authorization": "Bearer default-token",
                "X-API-Version": "v2",
            },
        )

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response

            with APIClient(config) as client:
                client.get("/users")
                client.post("/users", json_body={"name": "Test"})

                # Both requests should have default headers
                for call in MockSession.return_value.request.call_args_list:
                    headers = call[1]["headers"]
                    assert "Authorization" in headers
                    assert "X-API-Version" in headers

    def test_per_request_headers_override_defaults(self) -> None:
        """Test that per-request headers override config defaults."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.elapsed.total_seconds.return_value = 0.1

        config = APIClientConfig(
            base_url="https://api.example.com",
            default_headers={"Authorization": "Bearer default-token"},
        )

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response

            with APIClient(config) as client:
                client.get("/users", headers={"Authorization": "Bearer override-token"})

                call_headers = MockSession.return_value.request.call_args[1]["headers"]
                assert call_headers["Authorization"] == "Bearer override-token"

    def test_timeout_configuration_applied(self) -> None:
        """Test that timeout configuration is applied to requests."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.elapsed.total_seconds.return_value = 0.1

        config = APIClientConfig(
            base_url="https://api.example.com",
            timeout=45.0,
        )

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response

            with APIClient(config) as client:
                client.get("/test")

                call_kwargs = MockSession.return_value.request.call_args[1]
                assert call_kwargs["timeout"] == 45.0


class TestAPIRequestModelIntegration:
    """Integration tests for APIRequest model usage."""

    def test_request_model_with_all_fields(self) -> None:
        """Test using APIRequest model with all fields."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.models import APIRequest

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = '{"result": "ok"}'
        mock_response.elapsed.total_seconds.return_value = 0.15

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response

            with APIClient(config) as client:
                request = APIRequest(
                    method="POST",
                    path="/search",
                    headers={"Accept-Language": "en-US"},
                    params={"q": "test", "page": "1"},
                    json_body={"filters": {"active": True}},
                )

                response = client.request(request)

                assert response.status_code == 200
                call_kwargs = MockSession.return_value.request.call_args[1]
                assert call_kwargs["method"] == "POST"
                assert call_kwargs["params"] == {"q": "test", "page": "1"}
                assert call_kwargs["json"] == {"filters": {"active": True}}


class TestMultipleRequestsInSession:
    """Integration tests for multiple requests in single session."""

    def test_multiple_requests_reuse_session(self) -> None:
        """Test that multiple requests reuse the same session."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.elapsed.total_seconds.return_value = 0.1

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response

            with APIClient(config) as client:
                client.get("/users")
                client.get("/posts")
                client.post("/comments", json_body={"text": "Hello"})

                # Should have created only one session
                assert MockSession.call_count == 1
                # But made 3 requests
                assert MockSession.return_value.request.call_count == 3
