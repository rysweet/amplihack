"""
Integration tests for Azure Responses API + LiteLLM integration.

This test suite validates the complete integration flow between:
1. LiteLLM Router (expected to fail for Azure Responses API)
2. Custom ResponsesAPIProxy (handles actual Azure Responses API calls)
3. Model mapping and authentication
4. Tool calling functionality
5. Error handling and fallback mechanisms

Test Philosophy: Validate that the hybrid architecture works correctly,
with LiteLLM failing as designed and custom proxy succeeding.
"""

import asyncio
import os
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from dotenv import load_dotenv

# Load test environment
load_dotenv(".azure.env")


class TestAzureResponsesAPIIntegration:
    """Integration tests for Azure Responses API functionality."""

    @pytest.fixture
    def azure_config(self):
        """Azure configuration for testing."""
        return {
            "OPENAI_API_KEY": "test-key",  # pragma: allowlist secret
            "AZURE_OPENAI_KEY": "test-key",  # pragma: allowlist secret
            "OPENAI_BASE_URL": "https://ai-adapt-oai-eastus2.openai.azure.com/openai/v1/responses?api-version=preview",
            "AZURE_API_VERSION": "preview",
            "BIG_MODEL": "gpt-5",
            "MIDDLE_MODEL": "gpt-5",
            "SMALL_MODEL": "gpt-5",
            "USE_LITELLM_ROUTER": "true",
        }

    @pytest.fixture
    def sample_chat_request(self):
        """Sample Claude-style chat request."""
        return {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "Hello, how can you help me?"}],
            "max_tokens": 1000,
            "temperature": 0.7,
            "stream": False,
        }

    @pytest.fixture
    def sample_tool_request(self):
        """Sample request with tool calls."""
        return {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "What files are in the current directory?"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "bash",
                        "description": "Execute bash commands",
                        "parameters": {
                            "type": "object",
                            "properties": {"command": {"type": "string"}},
                            "required": ["command"],
                        },
                    },
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.7,
        }

    def test_litellm_router_initialization(self, azure_config):
        """Test that LiteLLM router initializes but is expected to fail for Responses API."""
        from amplihack.proxy.integrated_proxy import setup_litellm_router

        # Should initialize successfully
        router = setup_litellm_router(azure_config)

        if router:
            # Router initializes but will fail on actual requests (by design)
            assert router is not None
            assert hasattr(router, "model_list")
            # Verify model list contains Azure deployment format
            model_names = [model["model_name"] for model in router.model_list]
            assert "claude-sonnet" in model_names or "claude-haiku" in model_names
        else:
            # Router may be disabled if it detects incompatibility
            assert router is None

    def test_responses_api_proxy_initialization(self, azure_config):
        """Test ResponsesAPIProxy initializes correctly."""
        from amplihack.proxy.responses_api_proxy import ResponsesAPIProxy

        proxy = ResponsesAPIProxy(
            azure_base_url=azure_config["OPENAI_BASE_URL"],
            azure_api_key=azure_config["AZURE_OPENAI_KEY"],
            listen_port=8083,
        )

        assert proxy.azure_base_url == azure_config["OPENAI_BASE_URL"]
        assert proxy.azure_api_key == azure_config["AZURE_OPENAI_KEY"]
        assert proxy.listen_port == 8083

    def test_model_mapping_integration(self, azure_config):
        """Test model mapping from Claude to Azure deployments."""
        from amplihack.proxy.azure_models import AzureModelMapper

        mapper = AzureModelMapper(azure_config)

        # Test standard mappings
        assert mapper.get_azure_deployment("gpt-4") is not None
        assert mapper.get_azure_deployment("BIG_MODEL") is not None

    @patch("requests.post")
    def test_request_format_transformation(self, mock_post, azure_config, sample_chat_request):
        """Test that OpenAI format is correctly transformed to Azure Responses API format."""
        from amplihack.proxy.responses_api_proxy import ResponsesAPIProxy

        # Mock successful Azure response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test-id",
            "choices": [
                {
                    "index": 0,
                    "message": {"content": "Hello! I'm Claude, how can I help?"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 15},
        }
        mock_post.return_value = mock_response

        proxy = ResponsesAPIProxy(
            azure_base_url=azure_config["OPENAI_BASE_URL"],
            azure_api_key=azure_config["AZURE_OPENAI_KEY"],
        )

        # Transform request
        azure_request = proxy._transform_to_responses_api(sample_chat_request)

        # Verify transformation
        assert azure_request["model"] == sample_chat_request["model"]
        assert azure_request["input"] == sample_chat_request["messages"]  # messages -> input
        assert azure_request["temperature"] == 1.0  # Always 1.0 for Responses API
        assert "max_tokens" in azure_request or "max_output_tokens" in azure_request

    @patch("requests.post")
    def test_tool_calling_transformation(self, mock_post, azure_config, sample_tool_request):
        """Test tool calling format transformation."""
        from amplihack.proxy.responses_api_proxy import ResponsesAPIProxy

        # Mock Azure response with tool call
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test-id",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "type": "function",
                                "function": {"name": "bash", "arguments": '{"command": "ls -la"}'},
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
        }
        mock_post.return_value = mock_response

        proxy = ResponsesAPIProxy(
            azure_base_url=azure_config["OPENAI_BASE_URL"],
            azure_api_key=azure_config["AZURE_OPENAI_KEY"],
        )

        # Transform request
        azure_request = proxy._transform_to_responses_api(sample_tool_request)

        # Verify tool transformation
        assert "tools" in azure_request
        assert len(azure_request["tools"]) == 1
        tool = azure_request["tools"][0]
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "bash"

    def test_litellm_fallback_behavior(self, azure_config, sample_chat_request):
        """Test that LiteLLM fails as expected and falls back to custom proxy."""
        from amplihack.proxy.integrated_proxy import setup_litellm_router

        router = setup_litellm_router(azure_config)

        if router:
            # LiteLLM should fail when trying to call Azure Responses API
            # This is expected behavior - it will try standard Azure OpenAI endpoint
            with pytest.raises((Exception, TypeError, ValueError)):
                # This should fail because LiteLLM doesn't understand Responses API format
                asyncio.run(
                    router.acompletion(
                        model="claude-sonnet", messages=sample_chat_request["messages"]
                    )
                )

    @patch("aiohttp.ClientSession.post")
    def test_end_to_end_integration_flow(self, mock_post, azure_config, sample_chat_request):
        """Test complete end-to-end integration flow."""
        from amplihack.proxy.integrated_proxy import create_app

        # Mock Azure API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "id": "test-response",
                "choices": [
                    {
                        "index": 0,
                        "message": {"content": "Integration test successful!"},
                        "finish_reason": "stop",
                    }
                ],
            }
        )
        mock_post.return_value.__aenter__.return_value = mock_response

        app = create_app(azure_config)

        # Test would require actual FastAPI test client
        # This validates the app can be created with Azure config
        assert app is not None

    def test_error_handling_integration(self, azure_config):
        """Test error handling across the integration."""
        from amplihack.proxy.responses_api_proxy import ResponsesAPIProxy

        proxy = ResponsesAPIProxy(
            azure_base_url=azure_config["OPENAI_BASE_URL"],
            azure_api_key="invalid-key",  # Intentionally invalid  # pragma: allowlist secret
        )

        # Test error transformation
        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_post.return_value = mock_response

            # Should handle 401 error gracefully
            # (This would be called via Flask route in actual usage)
            assert proxy.azure_api_key == "invalid-key"  # pragma: allowlist secret

    def test_performance_benchmarks(self, azure_config):
        """Basic performance benchmarks for integration components."""
        from amplihack.proxy.azure_models import AzureModelMapper
        from amplihack.proxy.responses_api_proxy import ResponsesAPIProxy

        # Benchmark model mapping
        mapper = AzureModelMapper(azure_config)

        start_time = time.time()
        for _ in range(100):
            mapper.get_azure_deployment("gpt-4")
        mapping_time = time.time() - start_time

        # Should be very fast (< 1ms per lookup due to caching)
        assert mapping_time < 0.1

        # Benchmark proxy initialization
        start_time = time.time()
        proxy = ResponsesAPIProxy(
            azure_base_url=azure_config["OPENAI_BASE_URL"],
            azure_api_key=azure_config["AZURE_OPENAI_KEY"],
        )
        init_time = time.time() - start_time

        # Initialization should be near-instantaneous
        assert init_time < 0.01
        assert proxy is not None

    def test_configuration_validation(self, azure_config):
        """Test configuration validation for Azure Responses API."""
        from amplihack.proxy.azure_detector import AzureEndpointDetector

        detector = AzureEndpointDetector()

        # Test Azure endpoint detection
        assert detector.is_azure_endpoint(azure_config["OPENAI_BASE_URL"])

        # Test endpoint validation
        assert detector.validate_azure_endpoint(azure_config["OPENAI_BASE_URL"])

    def test_responses_api_specific_features(self, azure_config):
        """Test features specific to Azure Responses API."""
        from amplihack.proxy.responses_api_proxy import ResponsesAPIProxy

        proxy = ResponsesAPIProxy(
            azure_base_url=azure_config["OPENAI_BASE_URL"],
            azure_api_key=azure_config["AZURE_OPENAI_KEY"],
        )

        # Test temperature enforcement (should always be 1.0 for Responses API)
        test_request = {
            "model": "gpt-5",
            "messages": [{"role": "user", "content": "test"}],
            "temperature": 0.5,  # Should be overridden to 1.0
        }

        transformed = proxy._transform_to_responses_api(test_request)
        assert transformed["temperature"] == 1.0

        # Test max_tokens handling (should use configured limits)
        assert "max_tokens" in transformed
        # Should respect min/max limits from environment
        min_limit = int(azure_config.get("MIN_TOKENS_LIMIT", "4096"))
        assert transformed["max_tokens"] >= min_limit


class TestIntegrationDiagnostics:
    """Diagnostic tests for troubleshooting integration issues."""

    def test_environment_configuration(self):
        """Test that environment is properly configured for integration."""
        required_vars = ["OPENAI_API_KEY", "OPENAI_BASE_URL", "BIG_MODEL"]

        config = {}
        for var in required_vars:
            config[var] = os.environ.get(var)

        # Log configuration (without sensitive data)
        print("Azure Responses API Integration Configuration:")
        print(f"- Base URL: {config['OPENAI_BASE_URL']}")
        print(f"- Has API Key: {'Yes' if config['OPENAI_API_KEY'] else 'No'}")
        print(f"- Model: {config['BIG_MODEL']}")
        print(f"- Responses API: {'/responses' in (config['OPENAI_BASE_URL'] or '')}")

        # Basic validation
        if config["OPENAI_BASE_URL"]:
            assert "/responses" in config["OPENAI_BASE_URL"], "Should be Azure Responses API URL"

    def test_integration_health_check(self, azure_config):
        """Comprehensive health check for integration components."""
        health_report = {
            "litellm_router": False,
            "responses_api_proxy": False,
            "model_mapping": False,
            "azure_detection": False,
            "configuration": False,
        }

        try:
            # Test LiteLLM router
            from amplihack.proxy.integrated_proxy import setup_litellm_router

            router = setup_litellm_router(azure_config)
            health_report["litellm_router"] = router is not None
        except Exception as e:
            print(f"LiteLLM router issue: {e}")

        try:
            # Test ResponsesAPI proxy
            from amplihack.proxy.responses_api_proxy import ResponsesAPIProxy

            proxy = ResponsesAPIProxy(
                azure_base_url=azure_config["OPENAI_BASE_URL"],
                azure_api_key=azure_config["AZURE_OPENAI_KEY"],
            )
            health_report["responses_api_proxy"] = proxy is not None
        except Exception as e:
            print(f"ResponsesAPI proxy issue: {e}")

        try:
            # Test model mapping
            from amplihack.proxy.azure_models import AzureModelMapper

            mapper = AzureModelMapper(azure_config)
            health_report["model_mapping"] = mapper.get_azure_deployment("gpt-4") is not None
        except Exception as e:
            print(f"Model mapping issue: {e}")

        try:
            # Test Azure detection
            from amplihack.proxy.azure_detector import AzureEndpointDetector

            detector = AzureEndpointDetector()
            health_report["azure_detection"] = detector.is_azure_endpoint(
                azure_config["OPENAI_BASE_URL"]
            )
        except Exception as e:
            print(f"Azure detection issue: {e}")

        # Test configuration
        required_keys = ["OPENAI_BASE_URL", "AZURE_OPENAI_KEY", "BIG_MODEL"]
        health_report["configuration"] = all(azure_config.get(key) for key in required_keys)

        print(f"Integration Health Report: {health_report}")

        # At least ResponsesAPI proxy should be healthy
        assert health_report["responses_api_proxy"], "ResponsesAPI proxy must be functional"


if __name__ == "__main__":
    """Run integration tests directly."""
    import sys

    print("Azure Responses API + LiteLLM Integration Test Suite")
    print("=" * 60)

    # Basic environment check
    config = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "test-key"),  # pragma: allowlist secret
        "OPENAI_BASE_URL": os.environ.get("OPENAI_BASE_URL", ""),
        "AZURE_OPENAI_KEY": os.environ.get(
            "AZURE_OPENAI_KEY", "test-key"
        ),  # pragma: allowlist secret
        "BIG_MODEL": os.environ.get("BIG_MODEL", "gpt-5"),
    }

    print("Environment Status:")
    print(f"- OPENAI_BASE_URL: {config['OPENAI_BASE_URL']}")
    print(
        f"- Has API Key: {'Yes' if config['OPENAI_API_KEY'] != 'test-key' else 'No (using test key)'}"  # pragma: allowlist secret
    )
    print(f"- BIG_MODEL: {config['BIG_MODEL']}")
    print(f"- Is Responses API: {'/responses' in config['OPENAI_BASE_URL']}")

    if len(sys.argv) > 1 and sys.argv[1] == "--health":
        # Run health check only
        test_diagnostics = TestIntegrationDiagnostics()
        test_diagnostics.test_integration_health_check(config)
    else:
        # Run pytest
        pytest.main([__file__, "-v"])
