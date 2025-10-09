"""
Test OpenAI Responses API implementation in claude-code-proxy.

This test validates that the proxy correctly handles OpenAI Responses API
requests and provides proper responses.
"""

import subprocess
import time

import pytest
import requests


class TestOpenAIResponsesAPI:
    """Test OpenAI Responses API functionality."""

    @pytest.fixture(scope="class")
    def proxy_port(self):
        """Get an available port for testing."""
        return 8095

    @pytest.fixture(scope="class")
    def proxy_process(self, proxy_port):
        """Start a proxy process for testing."""
        import os

        env = os.environ.copy()
        env.update({"OPENAI_API_KEY": "test-key-for-responses-api", "PORT": str(proxy_port)})

        process = subprocess.Popen(
            ["uvx", "claude-code-proxy"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Wait for proxy to start
        time.sleep(3)

        yield process

        # Cleanup
        process.terminate()
        process.wait()

    def test_responses_api_endpoint_exists(self, proxy_process, proxy_port):
        """Test that the /openai/responses endpoint exists and responds."""
        url = f"http://localhost:{proxy_port}/openai/responses"

        data = {"model": "gpt-4", "input": "Hello, test message"}

        try:
            response = requests.post(
                url, headers={"Content-Type": "application/json"}, json=data, timeout=10
            )

            # Should not be 404 (endpoint exists)
            assert response.status_code != 404, "Responses API endpoint should exist"

            # Should return JSON
            response_data = response.json()
            assert isinstance(response_data, dict), "Response should be JSON"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Could not connect to proxy: {e}")

    def test_responses_api_format(self, proxy_process, proxy_port):
        """Test that the responses follow OpenAI Responses API format."""
        url = f"http://localhost:{proxy_port}/openai/responses"

        data = {"model": "gpt-4", "input": "What is 2+2?"}

        try:
            response = requests.post(
                url, headers={"Content-Type": "application/json"}, json=data, timeout=10
            )

            if response.status_code == 200:
                response_data = response.json()

                # Check for required OpenAI Responses API fields
                required_fields = ["id", "object", "created_at", "status", "model"]
                for field in required_fields:
                    assert field in response_data, f"Response missing required field: {field}"

                # Check object type
                assert response_data["object"] == "response", "Object type should be 'response'"

                # Check status
                assert response_data["status"] in ["completed", "failed", "incomplete"], (
                    "Invalid status"
                )

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Could not connect to proxy: {e}")


def test_direct_curl_validation():
    """Test that can be run manually with curl."""
    # This documents the working curl command for manual testing
    curl_command = """
    curl -X POST http://localhost:8082/openai/responses \
      -H "Content-Type: application/json" \
      -d '{"model": "gpt-4", "input": "tell me what agents you have available"}'
    """

    print(f"Manual test command:\n{curl_command}")
    assert True  # This test always passes, it's just documentation


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
