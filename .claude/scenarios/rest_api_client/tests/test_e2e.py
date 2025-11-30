"""End-to-end tests for REST API client."""

import json
import time
from unittest.mock import Mock, patch

# These imports will fail initially (TDD)
from rest_api_client import APIClient
from rest_api_client.config import load_config
from rest_api_client.exceptions import ServerError, ValidationError


class TestCompleteUserWorkflows:
    """Test complete user workflows end-to-end."""

    def test_user_crud_workflow(self, mock_response, mock_session):
        """Test complete CRUD workflow for user management."""
        client = APIClient(base_url="https://api.example.com", api_key="test-key")

        # Mock responses for CRUD operations
        create_response = mock_response(
            201, json_data={"id": 123, "name": "John Doe", "email": "john@example.com"}
        )
        read_response = mock_response(
            200,
            json_data={
                "id": 123,
                "name": "John Doe",
                "email": "john@example.com",
                "created_at": "2024-01-01T00:00:00Z",
            },
        )
        update_response = mock_response(
            200, json_data={"id": 123, "name": "Jane Doe", "email": "jane@example.com"}
        )
        delete_response = mock_response(204, json_data=None)

        with patch.object(client, "_session", mock_session):
            # CREATE
            mock_session.post.return_value = create_response
            user = client.post("/users", json={"name": "John Doe", "email": "john@example.com"})
            assert user.status_code == 201
            user_id = user.json["id"]

            # READ
            mock_session.get.return_value = read_response
            fetched = client.get(f"/users/{user_id}")
            assert fetched.json["id"] == user_id
            assert fetched.json["name"] == "John Doe"

            # UPDATE
            mock_session.put.return_value = update_response
            updated = client.put(
                f"/users/{user_id}", json={"name": "Jane Doe", "email": "jane@example.com"}
            )
            assert updated.json["name"] == "Jane Doe"

            # DELETE
            mock_session.delete.return_value = delete_response
            deleted = client.delete(f"/users/{user_id}")
            assert deleted.status_code == 204

    def test_search_and_filter_workflow(self, mock_response, mock_session):
        """Test searching and filtering resources."""
        client = APIClient(base_url="https://api.example.com")

        # Mock search results
        search_results = [
            {"id": 1, "name": "Alice", "role": "admin"},
            {"id": 2, "name": "Bob", "role": "admin"},
        ]
        mock_session.get.return_value = mock_response(
            200, json_data={"results": search_results, "total": 2}
        )

        with patch.object(client, "_session", mock_session):
            # Search for admins
            response = client.get(
                "/users/search",
                params={"role": "admin", "active": True, "sort": "name", "limit": 10},
            )

            assert response.status_code == 200
            assert response.json["total"] == 2
            assert len(response.json["results"]) == 2

            # Verify search parameters were passed
            call_kwargs = mock_session.get.call_args.kwargs
            assert call_kwargs["params"]["role"] == "admin"
            assert call_kwargs["params"]["active"] is True

    def test_bulk_operations_workflow(self, mock_response, mock_session):
        """Test bulk operations workflow."""
        client = APIClient(base_url="https://api.example.com", max_retries=2, retry_delay=0.1)

        # Mock bulk operation responses
        mock_session.post.side_effect = [
            mock_response(202, json_data={"job_id": "job-123"}),
            mock_response(200, json_data={"status": "processing", "progress": 50}),
            mock_response(
                200,
                json_data={
                    "status": "completed",
                    "progress": 100,
                    "results": {"processed": 100, "succeeded": 95, "failed": 5},
                },
            ),
        ]

        with patch.object(client, "_session", mock_session):
            # Start bulk operation
            job = client.post(
                "/bulk/users/update",
                json={"updates": [{"id": i, "status": "active"} for i in range(100)]},
            )
            job_id = job.json["job_id"]

            # Poll for completion
            while True:
                mock_session.get = Mock(
                    side_effect=[
                        mock_response(200, json_data={"status": "processing", "progress": 50}),
                        mock_response(200, json_data={"status": "completed", "progress": 100}),
                    ]
                )

                status = client.get(f"/jobs/{job_id}")
                if status.json["status"] == "completed":
                    break
                time.sleep(0.1)

            # Check results
            assert status.json["results"]["processed"] == 100


class TestErrorRecoveryWorkflows:
    """Test error recovery in complete workflows."""

    def test_recover_from_network_issues(self, mock_response, mock_session):
        """Test recovery from intermittent network issues."""
        import requests

        client = APIClient(base_url="https://api.example.com", max_retries=3, retry_delay=0.05)

        # Simulate network issues then recovery
        mock_session.get.side_effect = [
            requests.ConnectionError("Network unreachable"),
            requests.Timeout("Request timed out"),
            mock_response(200, json_data={"status": "ok"}),
        ]

        with patch.object(client, "_session", mock_session):
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json["status"] == "ok"

        # Should have retried 3 times
        assert mock_session.get.call_count == 3

    def test_handle_service_degradation(self, mock_response, mock_session):
        """Test handling service degradation gracefully."""
        client = APIClient(base_url="https://api.example.com", max_retries=5, retry_delay=0.1)

        # Service degrades then recovers
        responses = [
            mock_response(200, json_data={"page": 1}),  # OK
            mock_response(503, json_data={"error": "Service unavailable"}),  # Degraded
            mock_response(503, json_data={"error": "Service unavailable"}),  # Still degraded
            mock_response(200, json_data={"page": 2}),  # Recovered
        ]

        with patch.object(client, "_session", mock_session):
            results = []
            for i, resp in enumerate(responses):
                mock_session.get.return_value = resp
                try:
                    response = client.get(f"/data?page={i + 1}")
                    results.append(response.json)
                except ServerError:
                    # Wait and retry with same page
                    time.sleep(0.2)
                    continue

            # Should have successfully retrieved pages despite degradation
            assert len(results) >= 2

    def test_validation_error_recovery(self, mock_response, mock_session):
        """Test recovering from validation errors."""
        client = APIClient(base_url="https://api.example.com")

        # First attempt fails validation, second succeeds
        mock_session.post.side_effect = [
            mock_response(
                422,
                json_data={
                    "error": "Validation failed",
                    "fields": {"email": "Invalid format", "age": "Must be positive"},
                },
            ),
            mock_response(201, json_data={"id": 456, "email": "valid@example.com", "age": 25}),
        ]

        with patch.object(client, "_session", mock_session):
            # First attempt with invalid data
            try:
                client.post("/users", json={"email": "invalid-email", "age": -5})
            except ValidationError:
                # Fix validation errors
                fixed_data = {"email": "valid@example.com", "age": 25}

                # Retry with fixed data
                response = client.post("/users", json=fixed_data)
                assert response.status_code == 201
                assert response.json["id"] == 456


class TestConfigurationLoading:
    """Test configuration loading and usage."""

    def test_load_config_from_file(self, tmp_path, mock_response, mock_session):
        """Test loading configuration from file."""
        config_file = tmp_path / "api_config.json"
        config_file.write_text(
            json.dumps(
                {
                    "base_url": "https://production.api.com",
                    "timeout": 60,
                    "max_retries": 5,
                    "headers": {"X-API-Version": "v2", "User-Agent": "MyApp/1.0"},
                }
            )
        )

        # Load config and create client
        config = load_config(str(config_file))
        client = APIClient(config=config)

        mock_session.get.return_value = mock_response(200, json_data={})

        with patch.object(client, "_session", mock_session):
            client.get("/resource")

        # Verify config was applied
        call_kwargs = mock_session.get.call_args.kwargs
        assert "X-API-Version" in call_kwargs["headers"]
        assert call_kwargs["headers"]["User-Agent"] == "MyApp/1.0"
        assert call_kwargs["timeout"] == 60

    def test_environment_override(self, tmp_path, monkeypatch, mock_response, mock_session):
        """Test environment variables override file config."""
        # File config
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"base_url": "https://staging.api.com", "timeout": 30}))

        # Environment override
        monkeypatch.setenv("API_BASE_URL", "https://production.api.com")
        monkeypatch.setenv("API_TIMEOUT", "120")

        config = load_config(str(config_file))
        client = APIClient(config=config)

        assert client.base_url == "https://production.api.com"
        assert client.timeout == 120


class TestRealWorldScenarios:
    """Test real-world API scenarios."""

    def test_github_api_workflow(self, mock_response, mock_session):
        """Test GitHub-like API workflow."""
        client = APIClient(
            base_url="https://api.github.com",
            api_key="ghp_test_token",
            headers={"Accept": "application/vnd.github.v3+json"},
        )

        # Mock GitHub API responses
        repos_response = mock_response(
            200,
            json_data=[
                {"id": 1, "name": "repo1", "full_name": "user/repo1"},
                {"id": 2, "name": "repo2", "full_name": "user/repo2"},
            ],
        )

        issues_response = mock_response(
            200,
            json_data=[
                {"id": 101, "title": "Bug fix", "state": "open"},
                {"id": 102, "title": "Feature", "state": "closed"},
            ],
        )

        with patch.object(client, "_session", mock_session):
            # Get user repos
            mock_session.get.return_value = repos_response
            repos = client.get("/user/repos")
            assert len(repos.json) == 2

            # Get issues for first repo
            mock_session.get.return_value = issues_response
            issues = client.get("/repos/user/repo1/issues")
            assert len(issues.json) == 2
            assert issues.json[0]["state"] == "open"

    def test_stripe_api_workflow(self, mock_response, mock_session):
        """Test Stripe-like API workflow with idempotency."""
        client = APIClient(
            base_url="https://api.stripe.com/v1",
            api_key="sk_test_key",
            headers={"Stripe-Version": "2023-10-16"},
        )

        # Mock Stripe charge creation
        charge_response = mock_response(
            200,
            json_data={"id": "ch_123", "amount": 2000, "currency": "usd", "status": "succeeded"},
        )

        with patch.object(client, "_session", mock_session):
            mock_session.post.return_value = charge_response

            # Create charge with idempotency key
            charge = client.post(
                "/charges",
                json={"amount": 2000, "currency": "usd", "source": "tok_visa"},
                headers={"Idempotency-Key": "unique-key-123"},
            )

            assert charge.json["id"] == "ch_123"
            assert charge.json["status"] == "succeeded"

            # Verify idempotency key was sent
            call_kwargs = mock_session.post.call_args.kwargs
            assert "Idempotency-Key" in call_kwargs["headers"]

    def test_oauth_token_refresh_workflow(self, mock_response, mock_session):
        """Test OAuth token refresh workflow."""

        class OAuthClient(APIClient):
            def __init__(self, *args, refresh_token=None, **kwargs):
                super().__init__(*args, **kwargs)
                self.refresh_token = refresh_token
                self.access_token = None

            def refresh_auth(self):
                # Refresh OAuth token
                response = self._session.post(
                    f"{self.base_url}/oauth/token",
                    data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
                )
                if response.status_code == 200:
                    token_data = response.json()
                    self.access_token = token_data["access_token"]
                    self.headers["Authorization"] = f"Bearer {self.access_token}"
                    return True
                return False

        client = OAuthClient(base_url="https://api.example.com", refresh_token="refresh_123")

        with patch.object(client, "_session", mock_session):
            # First request fails with 401
            mock_session.get.return_value = mock_response(401, json_data={"error": "Token expired"})

            # Token refresh succeeds
            mock_session.post.return_value = mock_response(
                200, json_data={"access_token": "new_access_token", "expires_in": 3600}
            )

            # Retry request succeeds
            mock_session.get.side_effect = [
                mock_response(401, json_data={"error": "Token expired"}),
                mock_response(200, json_data={"data": "protected"}),
            ]

            # Make request (should auto-refresh)
            client.auto_refresh_auth = True
            response = client.get("/protected")

            assert response.status_code == 200
            assert client.access_token == "new_access_token"
