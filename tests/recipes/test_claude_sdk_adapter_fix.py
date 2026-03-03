"""Test ClaudeSDKAdapter model parameter fix for Issue #2336.

This test verifies that ClaudeSDKAdapter passes model via ClaudeAgentOptions
instead of as a direct parameter to sdk.query(), and that query() is consumed
as an async generator (not awaited as a coroutine).
"""

import sys
from unittest.mock import MagicMock, patch

# Mock the claude_agent_sdk module before it gets imported
mock_claude_agent_sdk = MagicMock()
mock_claude_agent_sdk.ClaudeAgentOptions = MagicMock
sys.modules["claude_agent_sdk"] = mock_claude_agent_sdk


def _make_async_gen_query(return_text="Test response"):
    """Create a mock query function that behaves like the real async generator.

    The real ``claude_agent_sdk.query()`` is an async generator that yields
    Message objects.  The final message is a ResultMessage with a ``.result``
    attribute containing the text output.
    """
    result_msg = MagicMock()
    result_msg.result = return_text

    async def _fake_query(**kwargs):
        yield result_msg

    return _fake_query


def test_claude_sdk_adapter_uses_options_parameter():
    """Verify sdk.query() is called with options parameter, not model parameter."""
    from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter

    # Create adapter with custom model
    adapter = ClaudeSDKAdapter(model="claude-opus-4-20250514")

    # Mock the SDK with async generator query
    mock_sdk = MagicMock()
    captured_kwargs = {}

    async def _capturing_query(**kwargs):
        captured_kwargs.update(kwargs)
        msg = MagicMock()
        msg.result = "Test response"
        yield msg

    mock_sdk.query = _capturing_query

    # Patch _get_sdk to return our mock
    with patch.object(adapter, "_get_sdk", return_value=mock_sdk):
        adapter.execute_agent_step(prompt="Test prompt")

        assert "options" in captured_kwargs, (
            "sdk.query() should receive 'options' parameter"
        )
        assert "model" not in captured_kwargs, (
            "sdk.query() should NOT receive 'model' as direct parameter"
        )


def test_claude_sdk_adapter_creates_options_object():
    """Verify ClaudeAgentOptions object is created with correct model value."""
    from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter

    # Create adapter with custom model
    custom_model = "claude-opus-4-6"
    adapter = ClaudeSDKAdapter(model=custom_model)

    # Mock the SDK with async generator
    mock_sdk = MagicMock()
    mock_sdk.query = _make_async_gen_query("Test response")

    # Create a fresh mock for ClaudeAgentOptions for this test
    mock_options_class = MagicMock()
    mock_options_instance = MagicMock()
    mock_options_class.return_value = mock_options_instance

    # Patch both the SDK and ClaudeAgentOptions
    with patch.object(adapter, "_get_sdk", return_value=mock_sdk):
        with patch.dict(
            "sys.modules", {"claude_agent_sdk": MagicMock(ClaudeAgentOptions=mock_options_class)}
        ):
            adapter.execute_agent_step(prompt="Test prompt")

            assert mock_options_class.called, "ClaudeAgentOptions should be instantiated"

            call_kwargs = mock_options_class.call_args.kwargs
            assert "model" in call_kwargs, "ClaudeAgentOptions should receive model parameter"
            assert call_kwargs["model"] == custom_model


def test_claude_sdk_adapter_passes_prompt_correctly():
    """Verify prompt is passed correctly to sdk.query()."""
    from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter

    adapter = ClaudeSDKAdapter()

    mock_sdk = MagicMock()
    captured_kwargs = {}

    async def _capturing_query(**kwargs):
        captured_kwargs.update(kwargs)
        msg = MagicMock()
        msg.result = "Test response"
        yield msg

    mock_sdk.query = _capturing_query
    test_prompt = "What is the meaning of life?"

    with patch.object(adapter, "_get_sdk", return_value=mock_sdk):
        adapter.execute_agent_step(prompt=test_prompt)

        assert "prompt" in captured_kwargs, "sdk.query() should receive prompt parameter"
        assert captured_kwargs["prompt"] == test_prompt


def test_claude_sdk_adapter_enriches_prompt_with_system_context():
    """Verify agent system prompt is correctly prepended to user prompt."""
    from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter

    adapter = ClaudeSDKAdapter()

    mock_sdk = MagicMock()
    captured_kwargs = {}

    async def _capturing_query(**kwargs):
        captured_kwargs.update(kwargs)
        msg = MagicMock()
        msg.result = "Test response"
        yield msg

    mock_sdk.query = _capturing_query

    test_prompt = "Execute task"
    agent_name = "builder"
    system_prompt = "You are a code builder agent."

    with patch.object(adapter, "_get_sdk", return_value=mock_sdk):
        adapter.execute_agent_step(
            prompt=test_prompt, agent_name=agent_name, agent_system_prompt=system_prompt
        )

        enriched_prompt = captured_kwargs["prompt"]
        assert f"[System context for {agent_name}]" in enriched_prompt
        assert system_prompt in enriched_prompt
        assert "[Task]" in enriched_prompt
        assert test_prompt in enriched_prompt


def test_claude_sdk_adapter_model_parameter_not_direct():
    """Verify model is NEVER passed as direct parameter to sdk.query()."""
    from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter

    adapter = ClaudeSDKAdapter(model="claude-opus-4-20250514")

    mock_sdk = MagicMock()
    captured_kwargs = {}

    async def _capturing_query(**kwargs):
        captured_kwargs.update(kwargs)
        msg = MagicMock()
        msg.result = "Test response"
        yield msg

    mock_sdk.query = _capturing_query

    with patch.object(adapter, "_get_sdk", return_value=mock_sdk):
        adapter.execute_agent_step(prompt="Test")

        assert "model" not in captured_kwargs, (
            f"sdk.query() received 'model' as direct parameter. "
            f"This MUST be passed via ClaudeAgentOptions instead. "
            f"Current kwargs: {list(captured_kwargs.keys())}"
        )


def test_claude_sdk_adapter_accepts_mode_and_working_dir():
    """Verify execute_agent_step accepts mode and working_dir parameters."""
    from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter

    adapter = ClaudeSDKAdapter()

    mock_sdk = MagicMock()
    mock_sdk.query = _make_async_gen_query("Test response")

    with patch.object(adapter, "_get_sdk", return_value=mock_sdk):
        # This call would raise TypeError if mode/working_dir not accepted
        result = adapter.execute_agent_step(
            prompt="Test prompt",
            agent_name="builder",
            agent_system_prompt="You are a builder.",
            mode="plan",
            working_dir="/tmp/test",
        )
        assert result == "Test response"


def test_claude_sdk_adapter_matches_protocol_signature():
    """Verify ClaudeSDKAdapter.execute_agent_step signature matches SDKAdapter protocol."""
    import inspect

    from amplihack.recipes.adapters.base import SDKAdapter
    from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter

    protocol_sig = inspect.signature(SDKAdapter.execute_agent_step)
    adapter_sig = inspect.signature(ClaudeSDKAdapter.execute_agent_step)

    protocol_params = set(protocol_sig.parameters.keys()) - {"self"}
    adapter_params = set(adapter_sig.parameters.keys()) - {"self"}

    missing = protocol_params - adapter_params
    assert not missing, (
        f"ClaudeSDKAdapter.execute_agent_step is missing parameters "
        f"from SDKAdapter protocol: {missing}"
    )

    print(f"✅ All protocol parameters present: {protocol_params}")


def test_claude_sdk_adapter_consumes_async_generator():
    """Verify execute_agent_step properly consumes query() as an async generator.

    This is the core fix: query() yields Message objects, and the adapter must
    iterate them with ``async for`` instead of awaiting with ``asyncio.run()``.
    """
    from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter

    adapter = ClaudeSDKAdapter()

    mock_sdk = MagicMock()

    # Create a multi-message async generator (like the real SDK)
    async def _multi_message_query(**kwargs):
        # First message: a system/assistant message (no .result)
        msg1 = MagicMock(spec=[])
        yield msg1
        # Second message: the ResultMessage with .result
        msg2 = MagicMock()
        msg2.result = "Final answer from agent"
        yield msg2

    mock_sdk.query = _multi_message_query

    with patch.object(adapter, "_get_sdk", return_value=mock_sdk):
        result = adapter.execute_agent_step(prompt="Test prompt")

        # Should get the .result from the ResultMessage, not str() of generator
        assert result == "Final answer from agent"
        assert "async_generator" not in result


def test_claude_sdk_adapter_returns_empty_when_no_result_message():
    """Verify adapter returns empty string when query yields no ResultMessage."""
    from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter

    adapter = ClaudeSDKAdapter()

    mock_sdk = MagicMock()

    async def _no_result_query(**kwargs):
        msg = MagicMock(spec=[])  # No .result attribute
        yield msg

    mock_sdk.query = _no_result_query

    with patch.object(adapter, "_get_sdk", return_value=mock_sdk):
        result = adapter.execute_agent_step(prompt="Test prompt")
        assert result == ""


if __name__ == "__main__":
    print("Running ClaudeSDKAdapter tests\n")

    tests = [
        test_claude_sdk_adapter_uses_options_parameter,
        test_claude_sdk_adapter_creates_options_object,
        test_claude_sdk_adapter_passes_prompt_correctly,
        test_claude_sdk_adapter_enriches_prompt_with_system_context,
        test_claude_sdk_adapter_model_parameter_not_direct,
        test_claude_sdk_adapter_accepts_mode_and_working_dir,
        test_claude_sdk_adapter_matches_protocol_signature,
        test_claude_sdk_adapter_consumes_async_generator,
        test_claude_sdk_adapter_returns_empty_when_no_result_message,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        name = test_func.__name__
        try:
            test_func()
            print(f"  PASSED: {name}")
            passed += 1
        except Exception as e:
            print(f"  FAILED: {name}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
