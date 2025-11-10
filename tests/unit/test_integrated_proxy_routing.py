"""
Comprehensive test coverage for integrated_proxy.py routing logic.

This module tests:
- LiteLLM router initialization and configuration
- Error handling when router unavailable
- Request routing logic (Azure Responses API vs Chat API)
- Response transformation (Anthropic <-> Azure <-> LiteLLM)
- Edge cases and failure modes
- Tool calling and streaming support
"""
# pyright: reportGeneralTypeIssues=false

import json
import os
from unittest.mock import MagicMock, patch

try:
    import pytest
except ImportError:
    pytest = None  # type: ignore[assignment]

# Import the module under test
from amplihack.proxy.integrated_proxy import (
    AzureAPIError,
    AzureAuthenticationError,
    AzureConfigurationError,
    AzureRateLimitError,
    AzureTransientError,
    ConversationState,
    Message,
    MessagesRequest,
    ToolCallError,
    ToolTimeoutError,
    ToolValidationError,
    classify_azure_error,
    clean_gemini_schema,
    convert_anthropic_to_azure_responses,
    convert_anthropic_to_litellm,
    convert_azure_responses_to_anthropic,
    convert_litellm_to_anthropic,
    extract_user_friendly_message,
    get_litellm_router,
    is_azure_chat_api,
    is_azure_responses_api,
    sanitize_error_message,
    setup_litellm_router,
    should_use_responses_api_for_model,
    validate_tool_schema,
)


class TestSanitizeErrorMessage:
    """Test sanitization of error messages to prevent credential leakage."""

    def test_sanitize_openai_api_key(self):
        """Test sanitization of OpenAI-style API keys."""
        error_msg = "Authentication failed with key: sk-1234567890abcdefghijklmnopqrst"  # pragma: allowlist secret
        sanitized = sanitize_error_message(error_msg)
        assert "sk-1234567890abcdefghijklmnopqrst" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_bearer_token(self):
        """Test sanitization of Bearer tokens."""
        error_msg = (
            "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"  # pragma: allowlist secret
        )
        sanitized = sanitize_error_message(error_msg)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_hex_keys(self):
        """Test sanitization of hexadecimal API keys."""
        error_msg = "API key: 1a2b3c4d5e6f7890abcdef1234567890"  # pragma: allowlist secret
        sanitized = sanitize_error_message(error_msg)
        assert "1a2b3c4d5e6f7890abcdef1234567890" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_base64_patterns(self):
        """Test sanitization of base64-like patterns."""
        error_msg = "Token: YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo="  # pragma: allowlist secret
        sanitized = sanitize_error_message(error_msg)
        assert "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo=" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_multiple_keys(self):
        """Test sanitization when multiple keys are present."""
        error_msg = "OpenAI: sk-abcd1234567890efghij, Azure: 1a2b3c4d5e6f7890abcdef1234567890"  # pragma: allowlist secret
        sanitized = sanitize_error_message(error_msg)
        assert "sk-abcd1234567890efghij" not in sanitized
        assert "1a2b3c4d5e6f7890abcdef1234567890" not in sanitized
        assert sanitized.count("[REDACTED]") >= 2

    def test_sanitize_no_keys_present(self):
        """Test that messages without keys are unchanged."""
        error_msg = "Simple error message without keys"
        sanitized = sanitize_error_message(error_msg)
        assert sanitized == error_msg


class TestAzureErrorClassification:
    """Test Azure API error classification and exception types."""

    def test_classify_rate_limit_error(self):
        """Test classification of rate limit errors (429)."""
        error = classify_azure_error(429, "Rate limit exceeded")
        assert isinstance(error, AzureRateLimitError)
        assert error.status_code == 429
        assert error.is_retryable

    def test_classify_authentication_error(self):
        """Test classification of authentication errors (401)."""
        error = classify_azure_error(401, "Invalid credentials")
        assert isinstance(error, AzureAuthenticationError)
        assert error.status_code == 401
        assert not error.is_retryable

    def test_classify_transient_error(self):
        """Test classification of transient errors (503)."""
        error = classify_azure_error(503, "Service temporarily unavailable")
        assert isinstance(error, AzureTransientError)
        assert error.is_retryable

    def test_classify_configuration_error(self):
        """Test classification of configuration errors (404)."""
        error = classify_azure_error(404, "Deployment not found")
        assert isinstance(error, AzureConfigurationError)
        assert not error.is_retryable

    def test_classify_json_error_response(self):
        """Test parsing of JSON error responses."""
        error_json = json.dumps({"code": "InvalidRequest", "message": "Bad request"})
        error = classify_azure_error(400, error_json)
        assert isinstance(error, AzureAPIError)
        assert error.status_code == 400

    def test_classify_nested_error_structure(self):
        """Test parsing of nested error structures with innererror."""
        error_json = json.dumps(
            {
                "error": {
                    "code": "InvalidParameter",
                    "message": "Invalid model parameter",
                    "innererror": {
                        "code": "ModelNotFound",
                        "message": "Model deployment not found",
                    },
                }
            }
        )
        error = classify_azure_error(404, error_json)
        assert isinstance(error, AzureConfigurationError)


class TestUserFriendlyMessages:
    """Test extraction of user-friendly error messages."""

    def test_extract_rate_limit_message(self):
        """Test user-friendly message for rate limits."""
        error = AzureRateLimitError("Rate limit exceeded", retry_after=60)
        message = extract_user_friendly_message(error)
        assert "rate limit" in message.lower()
        assert not any(key in message for key in ["sk-", "Bearer", "0x"])

    def test_extract_authentication_message(self):
        """Test user-friendly message for authentication errors."""
        error = AzureAuthenticationError("Invalid API key: sk-abc123")
        message = extract_user_friendly_message(error)
        assert "authentication" in message.lower() or "api key" in message.lower()
        assert "sk-abc123" not in message

    def test_extract_transient_error_message(self):
        """Test user-friendly message for transient errors."""
        error = AzureTransientError("Service unavailable")
        message = extract_user_friendly_message(error)
        assert "temporarily" in message.lower() or "try again" in message.lower()


class TestLiteLLMRouterInitialization:
    """Test LiteLLM router initialization and configuration."""

    @patch.dict(os.environ, {"AMPLIHACK_USE_LITELLM": "false"})
    def test_router_disabled_by_env_var(self):
        """Test that router returns None when disabled via environment variable."""
        # Need to reload the module to pick up env var change
        import importlib

        import amplihack.proxy.integrated_proxy as proxy_module

        importlib.reload(proxy_module)
        router = proxy_module.setup_litellm_router()
        assert router is None

    @patch.dict(
        os.environ,
        {"AMPLIHACK_USE_LITELLM": "true", "AZURE_OPENAI_KEY": "", "OPENAI_API_KEY": ""},
        clear=True,
    )
    def test_router_missing_credentials(self):
        """Test router returns None when credentials are missing."""
        router = setup_litellm_router({})
        assert router is None

    @patch("amplihack.proxy.integrated_proxy.create_unified_litellm_router")
    @patch("amplihack.proxy.integrated_proxy.validate_azure_unified_config")
    @patch.dict(
        os.environ,
        {
            "AMPLIHACK_USE_LITELLM": "true",
            "AZURE_OPENAI_KEY": "test-key",
            "OPENAI_BASE_URL": "https://test.openai.azure.com",
        },
    )
    def test_router_initialization_success(self, mock_validate, mock_create_router):
        """Test successful router initialization."""
        mock_validate.return_value = True
        mock_router = MagicMock()
        mock_create_router.return_value = mock_router

        config = {
            "AZURE_OPENAI_KEY": "test-key",
            "OPENAI_BASE_URL": "https://test.openai.azure.com",
        }
        router = setup_litellm_router(config)

        assert router is mock_router
        mock_validate.assert_called_once()
        mock_create_router.assert_called_once()

    @patch("amplihack.proxy.integrated_proxy.create_unified_litellm_router")
    @patch("amplihack.proxy.integrated_proxy.validate_azure_unified_config")
    @patch.dict(
        os.environ,
        {
            "AMPLIHACK_USE_LITELLM": "true",
            "AZURE_OPENAI_KEY": "test-key",
            "OPENAI_BASE_URL": "https://test.openai.azure.com",
        },
    )
    def test_router_initialization_failure(self, mock_validate, mock_create_router):
        """Test router initialization failure."""
        mock_validate.return_value = True
        mock_create_router.side_effect = Exception("Initialization failed")

        config = {
            "AZURE_OPENAI_KEY": "test-key",
            "OPENAI_BASE_URL": "https://test.openai.azure.com",
        }
        router = setup_litellm_router(config)

        assert router is None

    @patch("amplihack.proxy.integrated_proxy.validate_azure_unified_config")
    @patch.dict(
        os.environ,
        {
            "AMPLIHACK_USE_LITELLM": "true",
            "AZURE_OPENAI_KEY": "test-key",
            "OPENAI_BASE_URL": "https://test.openai.azure.com",
        },
    )
    def test_router_validation_failure(self, mock_validate):
        """Test router returns None when validation fails."""
        mock_validate.return_value = False

        config = {
            "AZURE_OPENAI_KEY": "test-key",
            "OPENAI_BASE_URL": "https://test.openai.azure.com",
        }
        router = setup_litellm_router(config)

        assert router is None


class TestLiteLLMRouterLazyLoading:
    """Test lazy loading behavior of LiteLLM router."""

    @patch("amplihack.proxy.integrated_proxy.setup_litellm_router")
    @patch.dict(os.environ, {"AMPLIHACK_USE_LITELLM": "true"})
    def test_router_lazy_initialization(self, mock_setup):
        """Test that router is initialized lazily on first access."""
        # Reset global state
        import amplihack.proxy.integrated_proxy as proxy_module

        proxy_module._litellm_router = None
        proxy_module._router_init_attempted = False

        mock_router = MagicMock()
        mock_setup.return_value = mock_router

        # First call should initialize
        router1 = get_litellm_router()
        assert router1 is mock_router
        mock_setup.assert_called_once()

        # Second call should use cached router
        router2 = get_litellm_router()
        assert router2 is mock_router
        mock_setup.assert_called_once()  # Still only called once

    @patch("amplihack.proxy.integrated_proxy.setup_litellm_router")
    @patch.dict(os.environ, {"AMPLIHACK_USE_LITELLM": "true"})
    def test_router_failed_initialization_cached(self, mock_setup):
        """Test that failed initialization is cached to avoid retries."""
        # Reset global state
        import amplihack.proxy.integrated_proxy as proxy_module

        proxy_module._litellm_router = None
        proxy_module._router_init_attempted = False

        mock_setup.return_value = None

        # First call attempts initialization
        router1 = get_litellm_router()
        assert router1 is None
        mock_setup.assert_called_once()

        # Second call should return None without retrying
        router2 = get_litellm_router()
        assert router2 is None
        mock_setup.assert_called_once()  # Still only called once


class TestAPIDetection:
    """Test detection of Azure Responses API vs Chat API."""

    @patch.dict(os.environ, {"OPENAI_BASE_URL": "https://test.openai.azure.com/openai/responses"})
    def test_is_azure_responses_api_true(self):
        """Test detection when Responses API URL is configured."""
        assert is_azure_responses_api() is True

    @patch.dict(os.environ, {"OPENAI_BASE_URL": "https://test.openai.azure.com"})
    def test_is_azure_responses_api_false(self):
        """Test detection when Chat API URL is configured."""
        assert is_azure_responses_api() is False

    @patch.dict(os.environ, {"OPENAI_BASE_URL": ""}, clear=True)
    def test_is_azure_responses_api_no_url(self):
        """Test detection when no URL is configured."""
        assert is_azure_responses_api() is False

    @patch.dict(os.environ, {"OPENAI_BASE_URL": "https://test.openai.azure.com"})
    def test_is_azure_chat_api_true(self):
        """Test detection of Azure Chat API."""
        assert is_azure_chat_api() is True

    def test_should_use_responses_api_for_sonnet(self):
        """Test that Sonnet models use Responses API."""
        assert should_use_responses_api_for_model("claude-sonnet-4.5") is True

    def test_should_use_responses_api_for_opus(self):
        """Test that Opus models use Responses API."""
        assert should_use_responses_api_for_model("claude-opus-3") is True

    def test_should_use_responses_api_for_haiku(self):
        """Test that Haiku models can use Responses API."""
        assert should_use_responses_api_for_model("claude-haiku-3.5") is True


class TestAnthropicToAzureConversion:
    """Test conversion from Anthropic format to Azure Responses format."""

    def test_convert_simple_request(self):
        """Test conversion of a simple text request."""
        anthropic_request = MessagesRequest(
            model="claude-sonnet-4.5",
            messages=[Message(role="user", content="Hello, world!")],
            max_tokens=1024,
        )

        azure_request = convert_anthropic_to_azure_responses(anthropic_request)

        assert azure_request["model"] is not None
        assert azure_request["max_tokens"] == 1024
        assert len(azure_request["messages"]) == 1
        assert azure_request["messages"][0]["role"] == "user"

    def test_convert_with_system_message(self):
        """Test conversion with system message."""
        anthropic_request = MessagesRequest(
            model="claude-sonnet-4.5",
            messages=[Message(role="user", content="Hello!")],
            max_tokens=1024,
            system=[{"type": "text", "text": "You are a helpful assistant."}],
        )

        azure_request = convert_anthropic_to_azure_responses(anthropic_request)

        # System should be converted to first message or preserved
        assert "system" in azure_request or azure_request["messages"][0]["role"] == "system"

    def test_convert_with_tools(self):
        """Test conversion with tool definitions."""
        anthropic_request = MessagesRequest(
            model="claude-sonnet-4.5",
            messages=[Message(role="user", content="Use the calculator")],
            max_tokens=1024,
            tools=[
                {
                    "name": "calculator",
                    "description": "Perform calculations",
                    "input_schema": {"type": "object", "properties": {}},
                }
            ],
        )

        azure_request = convert_anthropic_to_azure_responses(anthropic_request)

        assert "tools" in azure_request
        assert len(azure_request["tools"]) == 1

    def test_convert_streaming_enabled(self):
        """Test conversion with streaming enabled."""
        anthropic_request = MessagesRequest(
            model="claude-sonnet-4.5",
            messages=[Message(role="user", content="Stream this")],
            max_tokens=1024,
            stream=True,
        )

        azure_request = convert_anthropic_to_azure_responses(anthropic_request)

        assert azure_request["stream"] is True


class TestAzureToAnthropicConversion:
    """Test conversion from Azure Responses format to Anthropic format."""

    def test_convert_simple_response(self):
        """Test conversion of a simple Azure response."""
        azure_response = {
            "id": "msg-123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello!"}],
            "model": "gpt-5-codex",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }

        original_request = MessagesRequest(
            model="claude-sonnet-4.5",
            messages=[Message(role="user", content="Hi")],
            max_tokens=1024,
        )

        anthropic_response = convert_azure_responses_to_anthropic(azure_response, original_request)

        assert anthropic_response.id == "msg-123"
        assert anthropic_response.role == "assistant"
        assert anthropic_response.stop_reason == "end_turn"
        assert len(anthropic_response.content) == 1

    def test_convert_with_tool_use(self):
        """Test conversion of response with tool use."""
        azure_response = {
            "id": "msg-456",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "tool_use", "id": "tool-1", "name": "calculator", "input": {}}],
            "model": "gpt-5-codex",
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 15, "output_tokens": 8},
        }

        original_request = MessagesRequest(
            model="claude-sonnet-4.5",
            messages=[Message(role="user", content="Calculate 2+2")],
            max_tokens=1024,
        )

        anthropic_response = convert_azure_responses_to_anthropic(azure_response, original_request)

        assert anthropic_response.stop_reason == "tool_use"
        assert len(anthropic_response.content) == 1


class TestAnthropicToLiteLLMConversion:
    """Test conversion from Anthropic format to LiteLLM format."""

    def test_convert_basic_request(self):
        """Test basic request conversion."""
        anthropic_request = MessagesRequest(
            model="claude-sonnet-4.5",
            messages=[Message(role="user", content="Hello!")],
            max_tokens=1024,
        )

        litellm_request = convert_anthropic_to_litellm(anthropic_request)

        assert "model" in litellm_request
        assert "messages" in litellm_request
        assert litellm_request["max_tokens"] == 1024

    def test_convert_with_temperature(self):
        """Test conversion with temperature parameter."""
        anthropic_request = MessagesRequest(
            model="claude-sonnet-4.5",
            messages=[Message(role="user", content="Hello!")],
            max_tokens=1024,
            temperature=0.7,
        )

        litellm_request = convert_anthropic_to_litellm(anthropic_request)

        assert litellm_request["temperature"] == 0.7

    def test_convert_preserves_stream_flag(self):
        """Test that stream flag is preserved."""
        anthropic_request = MessagesRequest(
            model="claude-sonnet-4.5",
            messages=[Message(role="user", content="Hello!")],
            max_tokens=1024,
            stream=True,
        )

        litellm_request = convert_anthropic_to_litellm(anthropic_request)

        assert litellm_request["stream"] is True


class TestLiteLLMToAnthropicConversion:
    """Test conversion from LiteLLM format to Anthropic format."""

    def test_convert_litellm_response(self):
        """Test conversion of LiteLLM response."""
        litellm_response = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        original_request = MessagesRequest(
            model="openai/gpt-4", messages=[Message(role="user", content="Hi")], max_tokens=1024
        )

        anthropic_response = convert_litellm_to_anthropic(litellm_response, original_request)

        assert anthropic_response.role == "assistant"
        assert len(anthropic_response.content) > 0
        assert anthropic_response.usage.input_tokens == 10
        assert anthropic_response.usage.output_tokens == 5


class TestGeminiSchemaCleanup:
    """Test cleanup of JSON schemas for Gemini compatibility."""

    def test_remove_additional_properties(self):
        """Test removal of additionalProperties field."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": False,
        }

        cleaned = clean_gemini_schema(schema)

        assert "additionalProperties" not in cleaned
        assert "properties" in cleaned

    def test_remove_default_values(self):
        """Test removal of default values."""
        schema = {"type": "string", "default": "default_value"}

        cleaned = clean_gemini_schema(schema)

        assert "default" not in cleaned
        assert cleaned["type"] == "string"

    def test_remove_unsupported_string_formats(self):
        """Test removal of unsupported string formats."""
        schema = {"type": "string", "format": "email"}

        cleaned = clean_gemini_schema(schema)

        assert "format" not in cleaned

    def test_preserve_allowed_formats(self):
        """Test that allowed formats are preserved."""
        schema_datetime = {"type": "string", "format": "date-time"}
        cleaned_datetime = clean_gemini_schema(schema_datetime)
        assert cleaned_datetime["format"] == "date-time"

        schema_enum = {"type": "string", "format": "enum"}
        cleaned_enum = clean_gemini_schema(schema_enum)
        assert cleaned_enum["format"] == "enum"

    def test_recursive_cleaning(self):
        """Test that nested schemas are cleaned recursively."""
        schema = {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {"field": {"type": "string", "format": "uri"}},
                    "additionalProperties": True,
                }
            },
            "default": {},
        }

        cleaned = clean_gemini_schema(schema)

        assert "default" not in cleaned
        assert "additionalProperties" not in cleaned["properties"]["nested"]
        assert "format" not in cleaned["properties"]["nested"]["properties"]["field"]

    def test_clean_array_items(self):
        """Test cleaning of array item schemas."""
        schema = {
            "type": "array",
            "items": {"type": "string", "format": "email", "default": "test@example.com"},
        }

        cleaned = clean_gemini_schema(schema)

        assert "format" not in cleaned["items"]
        assert "default" not in cleaned["items"]


class TestToolValidation:
    """Test tool schema validation."""

    def test_valid_tool_schema(self):
        """Test validation of a valid tool schema."""
        tool = {
            "name": "calculator",
            "description": "Perform calculations",
            "input_schema": {
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "Math expression"}},
                "required": ["expression"],
            },
        }

        errors = validate_tool_schema(tool)
        assert len(errors) == 0

    def test_missing_name(self):
        """Test validation fails when name is missing."""
        tool = {
            "description": "Tool description",
            "input_schema": {"type": "object", "properties": {}},
        }

        errors = validate_tool_schema(tool)
        assert any("name" in error.lower() for error in errors)

    def test_missing_input_schema(self):
        """Test validation fails when input_schema is missing."""
        tool = {"name": "test_tool", "description": "Test tool"}

        errors = validate_tool_schema(tool)
        assert any("input_schema" in error.lower() for error in errors)

    def test_invalid_schema_type(self):
        """Test validation fails when schema type is invalid."""
        tool = {
            "name": "test_tool",
            "description": "Test tool",
            "input_schema": {"type": "invalid_type"},
        }

        errors = validate_tool_schema(tool)
        assert any("type" in error.lower() for error in errors)


class TestToolCallExceptions:
    """Test tool call exception types."""

    def test_tool_call_error_basic(self):
        """Test basic ToolCallError creation."""
        error = ToolCallError("Tool failed", tool_name="calculator", retry_count=1)
        assert str(error) == "Tool failed"
        assert error.tool_name == "calculator"
        assert error.retry_count == 1

    def test_tool_validation_error(self):
        """Test ToolValidationError with schema errors."""
        schema_errors = ["Missing required field: input", "Invalid type for field: output"]
        error = ToolValidationError(
            "Schema validation failed", tool_name="formatter", schema_errors=schema_errors
        )

        assert error.tool_name == "formatter"
        assert len(error.schema_errors) == 2
        assert "Missing required field" in error.schema_errors[0]

    def test_tool_timeout_error(self):
        """Test ToolTimeoutError."""
        error = ToolTimeoutError("Tool timed out", tool_name="slow_tool", timeout_seconds=30)
        assert error.tool_name == "slow_tool"
        assert error.timeout_seconds == 30


class TestEdgeCasesAndFailureModes:
    """Test edge cases and failure modes in routing logic."""

    def test_empty_messages_list(self):
        """Test handling of empty messages list."""
        with pytest.raises((ValueError, Exception)):
            MessagesRequest(model="claude-sonnet-4.5", messages=[], max_tokens=1024)

    def test_invalid_model_name(self):
        """Test handling of invalid model names."""
        request = MessagesRequest(
            model="invalid-model-name",
            messages=[Message(role="user", content="Test")],
            max_tokens=1024,
        )
        # Should not raise during creation, but might during routing
        assert request.model == "invalid-model-name"

    def test_max_tokens_zero(self):
        """Test handling of zero max_tokens."""
        with pytest.raises((ValueError, Exception)):
            MessagesRequest(
                model="claude-sonnet-4.5",
                messages=[Message(role="user", content="Test")],
                max_tokens=0,
            )

    def test_negative_temperature(self):
        """Test handling of negative temperature."""
        with pytest.raises((ValueError, Exception)):
            MessagesRequest(
                model="claude-sonnet-4.5",
                messages=[Message(role="user", content="Test")],
                max_tokens=1024,
                temperature=-0.5,
            )

    def test_temperature_above_one(self):
        """Test handling of temperature above 1.0."""
        # Some models allow temperature > 1.0, so this might be valid
        request = MessagesRequest(
            model="claude-sonnet-4.5",
            messages=[Message(role="user", content="Test")],
            max_tokens=1024,
            temperature=1.5,
        )
        assert request.temperature == 1.5


class TestConversationStateManagement:
    """Test conversation state tracking for tool calling."""

    def test_conversation_state_initialization(self):
        """Test ConversationState model initialization."""
        state = ConversationState(
            has_tool_use=True,
            has_tool_result=False,
            last_tool_use_id="tool-123",
            tool_call_count=1,
            consecutive_errors=0,
        )

        assert state.has_tool_use is True
        assert state.has_tool_result is False
        assert state.tool_call_count == 1

    def test_conversation_state_defaults(self):
        """Test ConversationState with default values."""
        state = ConversationState(
            has_tool_use=False,
            has_tool_result=False,
            last_tool_use_id=None,
            tool_call_count=0,
            consecutive_errors=0,
        )

        assert state.tool_call_count == 0
        assert state.last_tool_use_id is None


if __name__ == "__main__":
    if pytest is not None:
        pytest.main([__file__, "-v"])
    else:
        print("pytest not available - skipping test execution")
