"""Integration tests for full client workflow."""

import pytest

from amplihack.api_client import RestApiClient, RestApiConfig
from amplihack.api_client.exceptions import SecurityError


@pytest.mark.integration
class TestFullWorkflow:
    """Test complete client workflows."""

    def test_get_json_workflow(self):
        """Test complete GET workflow with JSON response."""
        config = RestApiConfig(base_url="https://httpbin.org")
        client = RestApiClient(config)

        response = client.get("/json")
        assert response.ok
        data = response.json()
        assert isinstance(data, dict)

    def test_post_json_workflow(self):
        """Test complete POST workflow with JSON."""
        config = RestApiConfig(base_url="https://httpbin.org")
        client = RestApiClient(config)

        import json

        payload = {"key": "value", "number": 42}
        body = json.dumps(payload).encode()

        response = client.post("/post", body=body, headers={"Content-Type": "application/json"})
        assert response.ok
        data = response.json()
        assert json.loads(data["data"]) == payload

    def test_custom_headers_workflow(self):
        """Test workflow with custom headers."""
        config = RestApiConfig(
            base_url="https://httpbin.org", headers={"X-Custom-Header": "test-value"}
        )
        client = RestApiClient(config)

        response = client.get("/headers")
        assert response.ok
        data = response.json()
        assert data["headers"]["X-Custom-Header"] == "test-value"

    def test_security_workflow(self):
        """Test security features in workflow."""
        config = RestApiConfig(base_url="https://127.0.0.1")
        client = RestApiClient(config)

        # SSRF should block
        with pytest.raises(SecurityError):
            client.get("/admin")
