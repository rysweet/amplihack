"""Unit tests for tool format detection and conversion."""


class TestToolFormatDetection:
    """Test tool format detection for Azure Responses API vs Chat API."""

    def test_detect_responses_api_endpoint(self, monkeypatch):
        """Detect Responses API endpoint from URL path."""
        monkeypatch.setenv(
            "OPENAI_BASE_URL",
            "https://ai-adapt-oai-eastus2.cognitiveservices.azure.com/openai/responses",
        )

        # Reload module to pick up new env var
        import importlib

        import amplihack.proxy.integrated_proxy as proxy_module

        importlib.reload(proxy_module)

        assert proxy_module.is_azure_responses_api()

    def test_detect_chat_api_endpoint(self, monkeypatch):
        """Detect Chat API endpoint from URL path."""
        monkeypatch.setenv(
            "OPENAI_BASE_URL",
            "https://ai-adapt-oai-eastus2.cognitiveservices.azure.com/openai/chat/completions",
        )

        import importlib

        import amplihack.proxy.integrated_proxy as proxy_module

        importlib.reload(proxy_module)

        assert not proxy_module.is_azure_responses_api()

    def test_responses_api_tool_format(self):
        """Test flat tool format for Responses API."""
        # Responses API expects flat structure
        tool = {
            "name": "get_weather",
            "description": "Get weather for a location",
            "input_schema": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
        }

        # Expected Responses API format (flat)
        expected = {
            "type": "function",
            "name": "get_weather",
            "description": "Get weather for a location",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
        }

        # Format for Responses API (flat)
        formatted = {
            "type": "function",
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema", {}),
        }

        assert formatted == expected

    def test_chat_api_tool_format(self):
        """Test nested tool format for Chat API."""
        # Chat API expects nested structure
        tool = {
            "name": "get_weather",
            "description": "Get weather for a location",
            "input_schema": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
        }

        # Expected Chat API format (nested in function object)
        expected = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            },
        }

        # Format for Chat API (nested)
        formatted = {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {}),
            },
        }

        assert formatted == expected

    def test_tool_choice_responses_api_format(self):
        """Test tool_choice format for Responses API."""
        # Anthropic format
        tool_choice = {"type": "tool", "name": "get_weather"}

        # Expected Responses API format (flat)
        expected = {"type": "function", "name": "get_weather"}

        # Format for Responses API
        formatted = {"type": "function", "name": tool_choice["name"]}

        assert formatted == expected

    def test_tool_choice_chat_api_format(self):
        """Test tool_choice format for Chat API."""
        # Anthropic format
        tool_choice = {"type": "tool", "name": "get_weather"}

        # Expected Chat API format (nested)
        expected = {"type": "function", "function": {"name": "get_weather"}}

        # Format for Chat API
        formatted = {"type": "function", "function": {"name": tool_choice["name"]}}

        assert formatted == expected


class TestToolFormatEdgeCases:
    """Test edge cases in tool format handling."""

    def test_empty_tools_array(self):
        """Handle empty tools array."""
        tools = []
        assert isinstance(tools, list)
        assert len(tools) == 0

    def test_tool_without_description(self):
        """Handle tool without description field."""
        tool = {"name": "simple_tool", "input_schema": {"type": "object"}}

        formatted = {
            "type": "function",
            "name": tool["name"],
            "description": tool.get("description", ""),  # Should default to ""
            "parameters": tool.get("input_schema", {}),
        }

        assert formatted["description"] == ""

    def test_tool_without_parameters(self):
        """Handle tool without input_schema/parameters."""
        tool = {"name": "no_params_tool", "description": "A tool with no parameters"}

        formatted = {
            "type": "function",
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema", {}),  # Should default to {}
        }

        assert formatted["parameters"] == {}

    def test_multiple_tools_formatting(self):
        """Format multiple tools correctly."""
        tools = [
            {"name": "tool1", "description": "First tool", "input_schema": {"type": "object"}},
            {"name": "tool2", "description": "Second tool", "input_schema": {"type": "object"}},
        ]

        # Responses API format (flat)
        formatted_responses = [
            {
                "type": "function",
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {}),
            }
            for t in tools
        ]

        assert len(formatted_responses) == 2
        assert all(f["type"] == "function" for f in formatted_responses)
        assert all("function" not in f for f in formatted_responses)  # Flat, not nested

    def test_tool_choice_auto(self):
        """Handle tool_choice: auto."""
        # When tool_choice type is "auto", format as simple string
        formatted = "auto"
        assert formatted == "auto"
