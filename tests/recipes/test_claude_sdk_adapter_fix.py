"""Test ClaudeSDKAdapter model parameter fix for Issue #2336.

This test verifies that ClaudeSDKAdapter passes model via ClaudeAgentOptions
instead of as a direct parameter to sdk.query().

EXPECTED BEHAVIOR: These tests SHOULD FAIL before the fix is applied.
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock the claude_agent_sdk module before it gets imported
mock_claude_agent_sdk = MagicMock()
mock_claude_agent_sdk.ClaudeAgentOptions = MagicMock
sys.modules['claude_agent_sdk'] = mock_claude_agent_sdk


def test_claude_sdk_adapter_uses_options_parameter():
    """Verify sdk.query() is called with options parameter, not model parameter.

    EXPECTED TO FAIL: Before fix, sdk.query() receives model as direct parameter
    """
    from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter

    # Create adapter with custom model
    adapter = ClaudeSDKAdapter(model="claude-opus-4-20250514")

    # Mock the SDK
    mock_sdk = MagicMock()
    mock_sdk.query = AsyncMock(return_value="Test response")

    # Patch _get_sdk to return our mock
    with patch.object(adapter, "_get_sdk", return_value=mock_sdk):
        # Execute agent step
        adapter.execute_agent_step(prompt="Test prompt")

        # Verify sdk.query was called
        assert mock_sdk.query.called, "sdk.query() should be called"

        # Get the call arguments
        call_args = mock_sdk.query.call_args

        # THIS SHOULD FAIL before fix is applied
        # Before fix: sdk.query(prompt=..., model=...)
        # After fix: sdk.query(prompt=..., options=ClaudeAgentOptions(model=...))
        assert "options" in call_args.kwargs, (
            "sdk.query() should receive 'options' parameter, not 'model' parameter directly"
        )
        assert "model" not in call_args.kwargs, (
            "sdk.query() should NOT receive 'model' as direct parameter"
        )

        print("✅ sdk.query() called with options parameter")


def test_claude_sdk_adapter_creates_options_object():
    """Verify ClaudeAgentOptions object is created with correct model value.

    EXPECTED TO FAIL: Before fix, no ClaudeAgentOptions object is created
    """
    from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter

    # Create adapter with custom model
    custom_model = "claude-sonnet-4-5-20250929"
    adapter = ClaudeSDKAdapter(model=custom_model)

    # Mock the SDK
    mock_sdk = MagicMock()
    mock_sdk.query = AsyncMock(return_value="Test response")

    # Create a fresh mock for ClaudeAgentOptions for this test
    mock_options_class = MagicMock()
    mock_options_instance = MagicMock()
    mock_options_class.return_value = mock_options_instance

    # Patch both the SDK and ClaudeAgentOptions
    with patch.object(adapter, "_get_sdk", return_value=mock_sdk):
        with patch.dict('sys.modules', {'claude_agent_sdk': MagicMock(ClaudeAgentOptions=mock_options_class)}):
            # Execute agent step
            adapter.execute_agent_step(prompt="Test prompt")

            # THIS SHOULD FAIL before fix is applied
            # Verify ClaudeAgentOptions was instantiated
            assert mock_options_class.called, "ClaudeAgentOptions should be instantiated"

            # Verify it was called with model parameter
            call_kwargs = mock_options_class.call_args.kwargs
            assert "model" in call_kwargs, "ClaudeAgentOptions should receive model parameter"
            assert call_kwargs["model"] == custom_model, (
                f"ClaudeAgentOptions model should be '{custom_model}', "
                f"got '{call_kwargs.get('model')}'"
            )

            print(f"✅ ClaudeAgentOptions created with model='{custom_model}'")


def test_claude_sdk_adapter_passes_prompt_correctly():
    """Verify prompt is passed correctly to sdk.query()."""
    from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter

    adapter = ClaudeSDKAdapter()

    # Mock the SDK
    mock_sdk = MagicMock()
    mock_sdk.query = AsyncMock(return_value="Test response")

    test_prompt = "What is the meaning of life?"

    with patch.object(adapter, "_get_sdk", return_value=mock_sdk):
        adapter.execute_agent_step(prompt=test_prompt)

        # Verify prompt is passed
        call_args = mock_sdk.query.call_args
        assert "prompt" in call_args.kwargs, "sdk.query() should receive prompt parameter"
        assert call_args.kwargs["prompt"] == test_prompt, "Prompt should match input"

        print(f"✅ Prompt passed correctly to sdk.query()")


def test_claude_sdk_adapter_enriches_prompt_with_system_context():
    """Verify agent system prompt is correctly prepended to user prompt."""
    from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter

    adapter = ClaudeSDKAdapter()

    # Mock the SDK
    mock_sdk = MagicMock()
    mock_sdk.query = AsyncMock(return_value="Test response")

    test_prompt = "Execute task"
    agent_name = "builder"
    system_prompt = "You are a code builder agent."

    with patch.object(adapter, "_get_sdk", return_value=mock_sdk):
        adapter.execute_agent_step(
            prompt=test_prompt,
            agent_name=agent_name,
            agent_system_prompt=system_prompt
        )

        # Verify enriched prompt structure
        call_args = mock_sdk.query.call_args
        enriched_prompt = call_args.kwargs["prompt"]

        assert f"[System context for {agent_name}]" in enriched_prompt, (
            "Enriched prompt should include system context header"
        )
        assert system_prompt in enriched_prompt, (
            "Enriched prompt should include agent system prompt"
        )
        assert "[Task]" in enriched_prompt, (
            "Enriched prompt should include task header"
        )
        assert test_prompt in enriched_prompt, (
            "Enriched prompt should include original prompt"
        )

        print("✅ Prompt enrichment works correctly")


def test_claude_sdk_adapter_model_parameter_not_direct():
    """Comprehensive test: verify model is NEVER passed as direct parameter.

    EXPECTED TO FAIL: Before fix, model is passed as direct kwarg
    """
    from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter

    adapter = ClaudeSDKAdapter(model="claude-opus-4-20250514")

    # Mock the SDK
    mock_sdk = MagicMock()
    mock_sdk.query = AsyncMock(return_value="Test response")

    with patch.object(adapter, "_get_sdk", return_value=mock_sdk):
        # Execute agent step
        adapter.execute_agent_step(prompt="Test")

        # Get call kwargs
        call_kwargs = mock_sdk.query.call_args.kwargs

        # THIS IS THE KEY TEST - SHOULD FAIL before fix
        # Before fix: {'prompt': '...', 'model': '...'}
        # After fix: {'prompt': '...', 'options': ClaudeAgentOptions(model='...')}

        if "model" in call_kwargs:
            raise AssertionError(
                f"CRITICAL: sdk.query() received 'model' as direct parameter. "
                f"This MUST be passed via ClaudeAgentOptions instead. "
                f"Current kwargs: {list(call_kwargs.keys())}"
            )

        print("✅ Model is NOT passed as direct parameter (fix applied)")


if __name__ == "__main__":
    print("🧪 Running ClaudeSDKAdapter Model Parameter Tests (Issue #2336)\n")
    print("⚠️  These tests SHOULD FAIL before the fix is applied\n")

    tests = [
        ("sdk.query() uses options parameter", test_claude_sdk_adapter_uses_options_parameter),
        ("ClaudeAgentOptions created with model", test_claude_sdk_adapter_creates_options_object),
        ("Prompt passed correctly", test_claude_sdk_adapter_passes_prompt_correctly),
        ("Prompt enrichment works", test_claude_sdk_adapter_enriches_prompt_with_system_context),
        ("Model NOT direct parameter", test_claude_sdk_adapter_model_parameter_not_direct),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Test: {test_name}")
        print(f"{'='*60}")
        try:
            test_func()
            print(f"✅ PASSED")
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED (EXPECTED): {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"SUMMARY: {passed} passed, {failed} failed")
    if failed > 0:
        print(f"⚠️  Failures are EXPECTED before fix implementation")
    print(f"{'='*60}")
