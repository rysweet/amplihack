"""
Comprehensive tests for tool calling implementation in ResponsesAPIProxy.

Tests for:
1. Request Transformation (OpenAI → Azure Responses API)
2. Response Transformation (Azure → OpenAI)
3. Integration Tests (complete cycles)
4. Error Handling for tool-related errors
"""

import json
import time

import pytest

from amplihack.proxy.responses_api_proxy import ResponsesAPIProxy


class TestRequestTransformation:
    """Tests for OpenAI tools format → Azure Responses API format transformation."""

    @pytest.fixture
    def proxy(self):
        """Create a ResponsesAPIProxy instance for testing."""
        return ResponsesAPIProxy(
            azure_base_url="https://test.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2024-02-01",
            azure_api_key="test-key",  # pragma: allowlist secret
            listen_port=8082,
        )

    def test_basic_tool_transformation(self, proxy):
        """Test basic OpenAI tools format is correctly transformed to Azure format."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "What's the weather?"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current weather",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string", "description": "City name"}
                            },
                            "required": ["location"],
                        },
                    },
                }
            ],
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        # Verify basic structure
        assert azure_request["model"] == "gpt-4"
        assert azure_request["input"] == openai_request["messages"]
        assert "tools" in azure_request

        # Verify tool transformation
        azure_tool = azure_request["tools"][0]
        assert azure_tool["type"] == "function"
        assert azure_tool["function"]["name"] == "get_weather"
        assert azure_tool["function"]["description"] == "Get current weather"
        assert azure_tool["function"]["parameters"]["type"] == "object"
        assert "location" in azure_tool["function"]["parameters"]["properties"]
        assert azure_tool["function"]["parameters"]["required"] == ["location"]

    def test_multiple_tools_transformation(self, proxy):
        """Test transformation of multiple tools."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Help me with tasks"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather info",
                        "parameters": {"type": "object", "properties": {}},
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "send_email",
                        "description": "Send an email",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "to": {"type": "string"},
                                "subject": {"type": "string"},
                                "body": {"type": "string"},
                            },
                        },
                    },
                },
            ],
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        assert len(azure_request["tools"]) == 2
        assert azure_request["tools"][0]["function"]["name"] == "get_weather"
        assert azure_request["tools"][1]["function"]["name"] == "send_email"
        assert (
            azure_request["tools"][1]["function"]["parameters"]["properties"]["to"]["type"]
            == "string"
        )

    def test_tool_choice_auto(self, proxy):
        """Test tool_choice='auto' transformation."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Help me"}],
            "tools": [{"type": "function", "function": {"name": "test_tool"}}],
            "tool_choice": "auto",
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        assert azure_request["tool_choice"] == "auto"

    def test_tool_choice_none(self, proxy):
        """Test tool_choice='none' transformation."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Just chat"}],
            "tools": [{"type": "function", "function": {"name": "test_tool"}}],
            "tool_choice": "none",
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        assert azure_request["tool_choice"] == "none"

    def test_tool_choice_required(self, proxy):
        """Test tool_choice='required' transformation."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Use a tool"}],
            "tools": [{"type": "function", "function": {"name": "required_tool"}}],
            "tool_choice": "required",
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        assert azure_request["tool_choice"] == "required"

    def test_tool_choice_specific_function(self, proxy):
        """Test tool_choice with specific function specification."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Use specific tool"}],
            "tools": [
                {"type": "function", "function": {"name": "tool_a"}},
                {"type": "function", "function": {"name": "tool_b"}},
            ],
            "tool_choice": {"type": "function", "function": {"name": "tool_b"}},
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        assert azure_request["tool_choice"]["type"] == "function"
        assert azure_request["tool_choice"]["function"]["name"] == "tool_b"

    def test_empty_tools_array(self, proxy):
        """Test handling of empty tools array."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "No tools"}],
            "tools": [],
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        # Empty tools array should not be included in the request
        assert "tools" not in azure_request
        assert "tool_choice" not in azure_request

    def test_malformed_tool_structure(self, proxy):
        """Test handling of malformed tool definitions."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Test"}],
            "tools": [
                {
                    "type": "function",
                    # Missing function key
                },
                {
                    "type": "function",
                    "function": {
                        # Missing name
                        "description": "Test tool"
                    },
                },
            ],
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        # Should handle gracefully - tools with missing data get empty strings
        assert len(azure_request["tools"]) == 2
        assert azure_request["tools"][0]["function"]["name"] == ""
        assert azure_request["tools"][1]["function"]["name"] == ""

    def test_no_tools_request(self, proxy):
        """Test transformation when no tools are present."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Simple chat"}],
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        assert "tools" not in azure_request
        assert "tool_choice" not in azure_request
        assert azure_request["model"] == "gpt-4"
        assert azure_request["input"] == openai_request["messages"]


class TestResponseTransformation:
    """Tests for Azure tool call responses → OpenAI tool_calls format transformation."""

    @pytest.fixture
    def proxy(self):
        """Create a ResponsesAPIProxy instance for testing."""
        return ResponsesAPIProxy(
            azure_base_url="https://test.openai.azure.com",
            azure_api_key="test-key",  # pragma: allowlist secret
        )

    def test_tool_calls_in_choice_message(self, proxy):
        """Test transformation of tool calls in choice message."""
        azure_response = {
            "id": "resp-123",
            "model": "gpt-4",
            "created": 1704067200,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_abc123",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"location": "New York"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
        }

        openai_response = proxy._transform_to_openai_format(azure_response)

        # Verify basic structure
        assert openai_response["id"] == "resp-123"
        assert openai_response["object"] == "chat.completion"
        assert openai_response["model"] == "gpt-4"

        # Verify tool call transformation
        choice = openai_response["choices"][0]
        assert choice["finish_reason"] == "tool_calls"
        assert choice["message"]["content"] is None
        assert len(choice["message"]["tool_calls"]) == 1

        tool_call = choice["message"]["tool_calls"][0]
        assert tool_call["id"] == "call_abc123"
        assert tool_call["type"] == "function"
        assert tool_call["function"]["name"] == "get_weather"
        assert tool_call["function"]["arguments"] == '{"location": "New York"}'

    def test_tool_calls_in_choice_root(self, proxy):
        """Test transformation when tool_calls are at choice root level."""
        azure_response = {
            "id": "resp-456",
            "choices": [
                {
                    "index": 0,
                    "text": "",
                    "tool_calls": [
                        {
                            "id": "call_def456",
                            "function": {
                                "name": "send_email",
                                "arguments": '{"to": "user@example.com", "subject": "Test"}',
                            },
                        }
                    ],
                    "finish_reason": "stop",
                }
            ],
        }

        openai_response = proxy._transform_to_openai_format(azure_response)

        choice = openai_response["choices"][0]
        assert choice["finish_reason"] == "tool_calls"  # Should be mapped to tool_calls
        assert len(choice["message"]["tool_calls"]) == 1

        tool_call = choice["message"]["tool_calls"][0]
        assert tool_call["id"] == "call_def456"
        assert tool_call["function"]["name"] == "send_email"
        assert tool_call["function"]["arguments"] == '{"to": "user@example.com", "subject": "Test"}'

    def test_multiple_tool_calls(self, proxy):
        """Test transformation of multiple tool calls."""
        azure_response = {
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"location": "NYC"}',
                                },
                            },
                            {
                                "id": "call_2",
                                "function": {
                                    "name": "get_time",
                                    "arguments": '{"timezone": "UTC"}',
                                },
                            },
                        ]
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }

        openai_response = proxy._transform_to_openai_format(azure_response)

        tool_calls = openai_response["choices"][0]["message"]["tool_calls"]
        assert len(tool_calls) == 2
        assert tool_calls[0]["function"]["name"] == "get_weather"
        assert tool_calls[1]["function"]["name"] == "get_time"

    def test_tool_call_id_generation(self, proxy):
        """Test generation of tool call IDs when missing."""
        azure_response = {
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "tool_calls": [
                            {
                                # Missing id
                                "function": {"name": "test_function", "arguments": "{}"}
                            }
                        ]
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }

        openai_response = proxy._transform_to_openai_format(azure_response)

        tool_call = openai_response["choices"][0]["message"]["tool_calls"][0]
        assert tool_call["id"].startswith("call_")
        assert len(tool_call["id"]) > 5  # Should be a generated ID

    def test_finish_reason_mapping(self, proxy):
        """Test proper finish_reason mapping for tool calls."""
        test_cases = [
            # (azure_finish_reason, has_tool_calls, expected_openai_finish_reason)
            ("tool_calls", True, "tool_calls"),
            ("stop", True, "tool_calls"),  # When tool calls present, map stop to tool_calls
            ("length", True, "length"),  # Length should stay length
            ("stop", False, "stop"),  # Without tool calls, stop stays stop
            ("length", False, "length"),  # Length without tools stays length
        ]

        for azure_reason, has_tools, expected_reason in test_cases:
            azure_response = {
                "choices": [
                    {"index": 0, "message": {"content": "Test"}, "finish_reason": azure_reason}
                ]
            }

            if has_tools:
                azure_response["choices"][0]["message"]["tool_calls"] = [
                    {"id": "call_test", "function": {"name": "test", "arguments": "{}"}}
                ]

            openai_response = proxy._transform_to_openai_format(azure_response)
            assert openai_response["choices"][0]["finish_reason"] == expected_reason

    def test_content_handling_with_tool_calls(self, proxy):
        """Test content handling when tool calls are present."""
        azure_response = {
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "content": "I'll help you with that.",
                        "tool_calls": [
                            {"id": "call_test", "function": {"name": "help", "arguments": "{}"}}
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }

        openai_response = proxy._transform_to_openai_format(azure_response)

        message = openai_response["choices"][0]["message"]
        # Content should be preserved when present
        assert message["content"] == "I'll help you with that."
        assert len(message["tool_calls"]) == 1

    def test_empty_content_with_tool_calls(self, proxy):
        """Test null/empty content with tool calls."""
        azure_response = {
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "content": "",  # Empty content
                        "tool_calls": [
                            {"id": "call_test", "function": {"name": "test", "arguments": "{}"}}
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }

        openai_response = proxy._transform_to_openai_format(azure_response)

        message = openai_response["choices"][0]["message"]
        # Empty content should become None when tool calls are present
        assert message["content"] is None
        assert len(message["tool_calls"]) == 1


class TestIntegrationTests:
    """Integration tests for complete request/response cycle."""

    @pytest.fixture
    def proxy(self):
        return ResponsesAPIProxy(
            azure_base_url="https://test.openai.azure.com",
            azure_api_key="test-key",  # pragma: allowlist secret
        )

    def test_complete_tool_call_cycle(self, proxy):
        """Test complete transformation cycle: OpenAI request → Azure → OpenAI response."""
        # Original OpenAI request
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Get weather for NYC"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current weather",
                        "parameters": {
                            "type": "object",
                            "properties": {"location": {"type": "string"}},
                            "required": ["location"],
                        },
                    },
                }
            ],
            "tool_choice": "auto",
        }

        # Transform to Azure format
        azure_request = proxy._transform_to_responses_api(openai_request)

        # Verify Azure request format
        assert azure_request["tool_choice"] == "auto"
        assert len(azure_request["tools"]) == 1
        assert azure_request["tools"][0]["function"]["name"] == "get_weather"

        # Simulate Azure response with tool call
        azure_response = {
            "id": "resp-integration-test",
            "model": "gpt-4",
            "created": int(time.time()),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_weather123",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"location": "New York City"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
        }

        # Transform back to OpenAI format
        final_openai_response = proxy._transform_to_openai_format(azure_response)

        # Verify final response
        assert final_openai_response["object"] == "chat.completion"
        assert final_openai_response["model"] == "gpt-4"

        choice = final_openai_response["choices"][0]
        assert choice["finish_reason"] == "tool_calls"
        assert choice["message"]["content"] is None

        tool_call = choice["message"]["tool_calls"][0]
        assert tool_call["id"] == "call_weather123"
        assert tool_call["type"] == "function"
        assert tool_call["function"]["name"] == "get_weather"
        assert '"location": "New York City"' in tool_call["function"]["arguments"]

        # Usage should be preserved
        assert final_openai_response["usage"]["total_tokens"] == 70

    def test_tool_choice_function_specific_cycle(self, proxy):
        """Test cycle with function-specific tool_choice."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Send an email"}],
            "tools": [
                {"type": "function", "function": {"name": "get_weather"}},
                {"type": "function", "function": {"name": "send_email"}},
            ],
            "tool_choice": {"type": "function", "function": {"name": "send_email"}},
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        assert azure_request["tool_choice"]["type"] == "function"
        assert azure_request["tool_choice"]["function"]["name"] == "send_email"

        # Simulate Azure responding with the specified tool
        azure_response = {
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_email456",
                                "function": {
                                    "name": "send_email",
                                    "arguments": '{"to": "test@example.com"}',
                                },
                            }
                        ]
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }

        final_response = proxy._transform_to_openai_format(azure_response)
        tool_call = final_response["choices"][0]["message"]["tool_calls"][0]
        assert tool_call["function"]["name"] == "send_email"


class TestErrorHandling:
    """Tests for error handling in tool-related scenarios."""

    @pytest.fixture
    def proxy(self):
        return ResponsesAPIProxy(
            azure_base_url="https://test.openai.azure.com",
            azure_api_key="test-key",  # pragma: allowlist secret
        )

    def test_malformed_azure_tool_calls(self, proxy):
        """Test handling of malformed tool calls in Azure response."""
        azure_response = {
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "tool_calls": [
                            {
                                # Missing required fields
                                "malformed": "data"
                            },
                            {
                                "id": "call_valid",
                                "function": {"name": "valid_function", "arguments": "{}"},
                            },
                        ]
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }

        openai_response = proxy._transform_to_openai_format(azure_response)

        # Should handle malformed entries gracefully
        tool_calls = openai_response["choices"][0]["message"]["tool_calls"]
        assert len(tool_calls) == 2

        # First tool call should have default values for missing fields
        assert tool_calls[0]["function"]["name"] == ""
        assert tool_calls[0]["function"]["arguments"] == "{}"

        # Second tool call should be valid
        assert tool_calls[1]["id"] == "call_valid"
        assert tool_calls[1]["function"]["name"] == "valid_function"

    def test_invalid_tool_choice_handling(self, proxy):
        """Test handling of invalid tool_choice values."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Test"}],
            "tools": [{"type": "function", "function": {"name": "test_tool"}}],
            "tool_choice": {"invalid": "structure"},  # Invalid tool_choice
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        # Should not include invalid tool_choice in Azure request
        assert "tool_choice" not in azure_request or azure_request.get("tool_choice") is None

    def test_missing_function_in_tool_choice(self, proxy):
        """Test tool_choice with missing function name."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Test"}],
            "tools": [{"type": "function", "function": {"name": "test_tool"}}],
            "tool_choice": {
                "type": "function",
                "function": {},  # Missing name
            },
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        # Should not include malformed tool_choice
        assert "tool_choice" not in azure_request or azure_request.get("tool_choice") is None

    def test_non_dict_tool_calls_handling(self, proxy):
        """Test handling of non-dict entries in tool_calls array."""
        azure_response = {
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "tool_calls": [
                            "invalid_string_entry",
                            None,
                            {"id": "call_valid", "function": {"name": "valid", "arguments": "{}"}},
                        ]
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }

        openai_response = proxy._transform_to_openai_format(azure_response)

        # Should filter out non-dict entries
        tool_calls = openai_response["choices"][0]["message"]["tool_calls"]
        assert len(tool_calls) == 1
        assert tool_calls[0]["id"] == "call_valid"

    def test_empty_azure_response_choices(self, proxy):
        """Test handling of Azure response with empty choices."""
        azure_response = {"id": "resp-empty", "choices": []}

        openai_response = proxy._transform_to_openai_format(azure_response)

        # Should handle gracefully
        assert openai_response["id"] == "resp-empty"
        assert openai_response["choices"] == []

    def test_missing_usage_info(self, proxy):
        """Test handling when usage info is missing from Azure response."""
        azure_response = {
            "choices": [
                {"index": 0, "message": {"content": "Test response"}, "finish_reason": "stop"}
            ]
        }

        openai_response = proxy._transform_to_openai_format(azure_response)

        # Should not include usage if not provided
        assert "usage" not in openai_response


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def proxy(self):
        return ResponsesAPIProxy(
            azure_base_url="https://test.openai.azure.com",
            azure_api_key="test-key",  # pragma: allowlist secret
        )

    def test_tools_with_no_parameters(self, proxy):
        """Test tools that don't require parameters."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Get random number"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_random_number",
                        "description": "Get a random number",
                        # No parameters field
                    },
                }
            ],
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        tool = azure_request["tools"][0]
        assert tool["function"]["name"] == "get_random_number"
        assert tool["function"]["parameters"] == {}  # Should default to empty object

    def test_large_tool_arguments(self, proxy):
        """Test handling of large argument strings in tool calls."""
        large_args = json.dumps({"data": "x" * 10000})  # Large argument string

        azure_response = {
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_large",
                                "function": {"name": "process_data", "arguments": large_args},
                            }
                        ]
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }

        openai_response = proxy._transform_to_openai_format(azure_response)

        tool_call = openai_response["choices"][0]["message"]["tool_calls"][0]
        assert tool_call["function"]["arguments"] == large_args
        assert len(tool_call["function"]["arguments"]) > 10000

    def test_unicode_in_tool_data(self, proxy):
        """Test handling of Unicode characters in tool names and arguments."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "测试工具"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "测试工具",
                        "description": "A test tool with Unicode",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "文本": {"type": "string", "description": "Unicode text"}
                            },
                        },
                    },
                }
            ],
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        tool = azure_request["tools"][0]
        assert tool["function"]["name"] == "测试工具"
        assert "文本" in tool["function"]["parameters"]["properties"]

    def test_nested_complex_parameters(self, proxy):
        """Test tools with deeply nested parameter structures."""
        openai_request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Complex tool"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "complex_tool",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "config": {
                                    "type": "object",
                                    "properties": {
                                        "nested": {
                                            "type": "object",
                                            "properties": {
                                                "deep_array": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {"value": {"type": "string"}},
                                                    },
                                                }
                                            },
                                        }
                                    },
                                }
                            },
                        },
                    },
                }
            ],
        }

        azure_request = proxy._transform_to_responses_api(openai_request)

        # Should preserve complex nested structure
        params = azure_request["tools"][0]["function"]["parameters"]
        nested_config = params["properties"]["config"]["properties"]["nested"]
        deep_array = nested_config["properties"]["deep_array"]
        assert deep_array["type"] == "array"
        assert deep_array["items"]["properties"]["value"]["type"] == "string"
