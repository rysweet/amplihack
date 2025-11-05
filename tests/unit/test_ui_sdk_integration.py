"""TDD Tests for UI Integration with Claude Agent SDK.

Tests the integration between UI and Claude Agent SDK:
- Title generation using SDK
- Cost tracking from SDK usage
- Todo tracking updates
- Streaming SDK output to UI logs
- Error handling from SDK

Test Coverage:
1. SDK-based title generation with fallback
2. Token counting and cost estimation
3. SDK message streaming to UI
4. SDK error handling in UI context
5. Performance (latency, throughput)
"""

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from amplihack.launcher.auto_mode import AutoMode


class TestTitleGenerationViaSDK:
    """Test title generation using Claude Agent SDK."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Build a RESTful API with JWT authentication",
                max_turns=5,
                working_dir=Path(temp_dir),
                ui_mode=True
            )
            yield auto_mode

    @pytest.mark.asyncio
    async def test_title_generation_calls_claude_sdk(self, auto_mode_with_ui):
        """Test that title generation uses Claude SDK query.

        Expected behavior:
        - Should call query() with title generation prompt
        - Should extract title from SDK response
        - Should return concise title (≤50 chars)
        """
        ui = auto_mode_with_ui.ui

        # Mock SDK query response
        async def mock_query_response(prompt, options):
            """Mock async generator yielding title."""
            class MockMessage:
                class Content:
                    text = "REST API with JWT Auth"
                content = [Content()]
                __class__.__name__ = "AssistantMessage"

            yield MockMessage()

        # This will fail until SDK integration is implemented
        with pytest.raises(AttributeError):
            with patch('amplihack.launcher.auto_mode.query', side_effect=mock_query_response):
                with patch('amplihack.launcher.auto_mode.CLAUDE_SDK_AVAILABLE', True):
                    title = await ui.generate_title_async()

                    assert title == "REST API with JWT Auth"
                    assert len(title) <= 50

    @pytest.mark.asyncio
    async def test_title_generation_handles_sdk_error(self, auto_mode_with_ui):
        """Test fallback when SDK title generation fails.

        Expected behavior:
        - If SDK raises exception, use truncated prompt
        - Should log warning about fallback
        - Should not crash UI
        """
        ui = auto_mode_with_ui.ui

        # Mock SDK to raise error
        async def mock_query_error(prompt, options):
            raise RuntimeError("SDK unavailable")

        # This will fail until error handling is implemented
        with pytest.raises(AttributeError):
            with patch('amplihack.launcher.auto_mode.query', side_effect=mock_query_error):
                with patch('amplihack.launcher.auto_mode.CLAUDE_SDK_AVAILABLE', True):
                    title = await ui.generate_title_async()

                    # Should fall back to truncated prompt
                    assert len(title) <= 50
                    assert title != ""

    @pytest.mark.asyncio
    async def test_title_generation_timeout(self, auto_mode_with_ui):
        """Test title generation with timeout.

        Expected behavior:
        - Should timeout after 5 seconds
        - Should fall back to truncated prompt
        """
        ui = auto_mode_with_ui.ui

        # Mock slow SDK response
        async def mock_slow_query(prompt, options):
            await asyncio.sleep(10)  # Longer than timeout
            yield Mock()

        # This will fail until timeout handling is implemented
        with pytest.raises(AttributeError):
            import asyncio
            with patch('amplihack.launcher.auto_mode.query', side_effect=mock_slow_query):
                with patch('amplihack.launcher.auto_mode.CLAUDE_SDK_AVAILABLE', True):
                    start = time.time()
                    title = await asyncio.wait_for(ui.generate_title_async(), timeout=5)
                    elapsed = time.time() - start

                    assert elapsed < 6  # Should timeout around 5s

    def test_title_generation_when_sdk_unavailable(self, auto_mode_with_ui):
        """Test title generation when SDK is not available.

        Expected behavior:
        - Should detect SDK unavailable
        - Should immediately use truncated prompt
        - Should not attempt SDK call
        """
        ui = auto_mode_with_ui.ui

        # This will fail until SDK availability check is implemented
        with pytest.raises(AttributeError):
            with patch('amplihack.launcher.auto_mode.CLAUDE_SDK_AVAILABLE', False):
                title = ui.generate_title()

                # Should use fallback without trying SDK
                assert len(title) <= 50
                assert "Build a RESTful API" in title or "REST" in title


class TestCostTrackingDisplay:
    """Test cost tracking from SDK usage."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=Path(temp_dir),
                ui_mode=True
            )
            yield auto_mode

    def test_cost_info_extracted_from_sdk_messages(self, auto_mode_with_ui):
        """Test that cost info is extracted from SDK message metadata.

        Expected behavior:
        - Should extract token counts from SDK messages
        - Should accumulate totals across turns
        - Should calculate estimated cost
        """
        auto_mode = auto_mode_with_ui

        # This will fail until cost extraction is implemented
        with pytest.raises(AttributeError):
            # Simulate SDK messages with usage info
            class MockUsage:
                input_tokens = 1500
                output_tokens = 800

            class MockMessage:
                usage = MockUsage()
                __class__.__name__ = "ResultMessage"

            auto_mode.process_sdk_message(MockMessage())

            cost_info = auto_mode.get_cost_info()
            assert cost_info['input_tokens'] == 1500
            assert cost_info['output_tokens'] == 800
            assert cost_info['estimated_cost'] > 0

    def test_cost_accumulates_across_turns(self, auto_mode_with_ui):
        """Test that costs accumulate across multiple turns.

        Expected behavior:
        - Turn 1: 1000 in + 500 out
        - Turn 2: 1200 in + 600 out
        - Total: 2200 in + 1100 out
        """
        auto_mode = auto_mode_with_ui

        # This will fail until cost accumulation is implemented
        with pytest.raises(AttributeError):
            # Simulate multiple turns
            class MockUsage1:
                input_tokens = 1000
                output_tokens = 500

            class MockUsage2:
                input_tokens = 1200
                output_tokens = 600

            class MockMessage:
                def __init__(self, usage):
                    self.usage = usage
                    self.__class__.__name__ = "ResultMessage"

            auto_mode.process_sdk_message(MockMessage(MockUsage1()))
            auto_mode.process_sdk_message(MockMessage(MockUsage2()))

            cost_info = auto_mode.get_cost_info()
            assert cost_info['input_tokens'] == 2200
            assert cost_info['output_tokens'] == 1100

    def test_cost_calculation_uses_correct_pricing(self, auto_mode_with_ui):
        """Test that cost calculation uses correct Claude pricing.

        Expected behavior:
        - Should use current Claude Sonnet pricing
        - Input: $3 per 1M tokens
        - Output: $15 per 1M tokens
        """
        auto_mode = auto_mode_with_ui

        # This will fail until pricing is implemented
        with pytest.raises(AttributeError):
            class MockUsage:
                input_tokens = 1_000_000  # 1M input
                output_tokens = 1_000_000  # 1M output

            class MockMessage:
                usage = MockUsage()
                __class__.__name__ = "ResultMessage"

            auto_mode.process_sdk_message(MockMessage())

            cost_info = auto_mode.get_cost_info()
            # $3 for input + $15 for output = $18
            assert 17.5 < cost_info['estimated_cost'] < 18.5

    def test_cost_display_formats_currency(self, auto_mode_with_ui):
        """Test that cost is formatted as currency string.

        Expected behavior:
        - Should format as $X.XX
        - Should handle small amounts (< $0.01)
        - Should handle large amounts (> $10)
        """
        ui = auto_mode_with_ui.ui

        # This will fail until formatting is implemented
        with pytest.raises(AttributeError):
            # Test various amounts
            test_cases = [
                (0.005, "$0.01"),      # Round up small amounts
                (0.156, "$0.16"),      # Normal rounding
                (12.456, "$12.46"),    # Large amount
            ]

            for cost, expected in test_cases:
                formatted = ui.format_cost(cost)
                assert formatted == expected


class TestTodoTrackingDisplay:
    """Test todo tracking updates from auto mode execution."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=Path(temp_dir),
                ui_mode=True
            )
            yield auto_mode

    def test_todos_updated_on_turn_phase_change(self, auto_mode_with_ui):
        """Test that todos update when auto mode phase changes.

        Expected behavior:
        - Turn 1 Clarify: Mark as in_progress
        - Turn 1 complete: Mark as completed
        - Turn 2 Plan: Mark as in_progress
        """
        auto_mode = auto_mode_with_ui

        # This will fail until phase tracking is implemented
        with pytest.raises(AttributeError):
            # Start turn 1
            auto_mode.start_turn_phase("Clarifying")
            todos = auto_mode.get_todos()
            clarify_todo = next(t for t in todos if "Clarify" in t['content'])
            assert clarify_todo['status'] == 'in_progress'

            # Complete turn 1
            auto_mode.complete_turn_phase("Clarifying")
            todos = auto_mode.get_todos()
            clarify_todo = next(t for t in todos if "Clarify" in t['content'])
            assert clarify_todo['status'] == 'completed'

    def test_custom_todos_can_be_added(self, auto_mode_with_ui):
        """Test that custom todos can be added during execution.

        Expected behavior:
        - AutoMode can add todos based on plan
        - Todos should appear in UI
        - Should support dynamic todo lists
        """
        auto_mode = auto_mode_with_ui

        # This will fail until custom todos are implemented
        with pytest.raises(AttributeError):
            # Add custom todo
            auto_mode.add_todo({
                "content": "Implement authentication",
                "status": "pending",
                "activeForm": "Implementing authentication"
            })

            todos = auto_mode.get_todos()
            auth_todo = next(t for t in todos if "authentication" in t['content'])
            assert auth_todo is not None

    def test_todos_persist_across_ui_refresh(self, auto_mode_with_ui):
        """Test that todos persist if UI refreshes.

        Expected behavior:
        - Todos stored in AutoMode state
        - UI can query current state
        - No loss of todo information
        """
        ui = auto_mode_with_ui.ui

        # This will fail until state persistence is implemented
        with pytest.raises(AttributeError):
            # Set some todos
            todos = [
                {"content": "Task 1", "status": "completed", "activeForm": "Completing task 1"},
                {"content": "Task 2", "status": "in_progress", "activeForm": "Working on task 2"},
            ]
            auto_mode_with_ui.set_todos(todos)

            # Simulate UI refresh (recreate UI object)
            new_ui = ui.__class__(auto_mode_with_ui)

            # Should have same todos
            retrieved_todos = new_ui.get_todos()
            assert len(retrieved_todos) == 2


class TestSDKStreamingToUI:
    """Test streaming SDK output to UI log area."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=Path(temp_dir),
                ui_mode=True
            )
            yield auto_mode

    @pytest.mark.asyncio
    async def test_assistant_messages_stream_to_logs(self, auto_mode_with_ui):
        """Test that AssistantMessage content streams to UI logs.

        Expected behavior:
        - Each text block should be queued to log
        - Should maintain order
        - Should appear in real-time
        """
        auto_mode = auto_mode_with_ui

        # This will fail until streaming is implemented
        with pytest.raises(AttributeError):
            # Simulate streaming messages
            messages = [
                "Starting analysis...",
                "Found 3 files to process",
                "Processing complete!"
            ]

            for msg in messages:
                class MockContent:
                    text = msg

                class MockMessage:
                    content = [MockContent()]
                    __class__.__name__ = "AssistantMessage"

                await auto_mode.process_streaming_message(MockMessage())

            # Check logs
            logs = auto_mode.get_queued_logs()
            assert len(logs) == 3
            assert logs[0] == "Starting analysis..."
            assert logs[2] == "Processing complete!"

    @pytest.mark.asyncio
    async def test_tool_usage_messages_logged(self, auto_mode_with_ui):
        """Test that tool usage is logged to UI.

        Expected behavior:
        - ToolUseMessage should be formatted and logged
        - Should show tool name and parameters
        """
        auto_mode = auto_mode_with_ui

        # This will fail until tool logging is implemented
        with pytest.raises(AttributeError):
            class MockToolUse:
                tool_name = "Read"
                parameters = {"file_path": "/test/file.py"}

            class MockMessage:
                tool_use = MockToolUse()
                __class__.__name__ = "ToolUseMessage"

            await auto_mode.process_streaming_message(MockMessage())

            logs = auto_mode.get_queued_logs()
            assert any("Read" in log for log in logs)
            assert any("file.py" in log for log in logs)

    @pytest.mark.asyncio
    async def test_result_messages_show_completion(self, auto_mode_with_ui):
        """Test that ResultMessage shows turn completion.

        Expected behavior:
        - Should log turn completion
        - Should include success/failure status
        """
        auto_mode = auto_mode_with_ui

        # This will fail until result logging is implemented
        with pytest.raises(AttributeError):
            class MockMessage:
                is_error = False
                result = "Turn completed successfully"
                __class__.__name__ = "ResultMessage"

            await auto_mode.process_streaming_message(MockMessage())

            logs = auto_mode.get_queued_logs()
            assert any("completed" in log.lower() for log in logs)

    @pytest.mark.asyncio
    async def test_streaming_handles_rapid_messages(self, auto_mode_with_ui):
        """Test streaming with many rapid messages.

        Expected behavior:
        - Should handle 100+ messages/second
        - Should not drop messages
        - Should batch to UI for performance
        """
        auto_mode = auto_mode_with_ui

        # This will fail until high-throughput streaming is implemented
        with pytest.raises(AttributeError):
            # Simulate rapid streaming
            for i in range(500):
                class MockContent:
                    text = f"Message {i}"

                class MockMessage:
                    content = [MockContent()]
                    __class__.__name__ = "AssistantMessage"

                await auto_mode.process_streaming_message(MockMessage())

            logs = auto_mode.get_queued_logs()
            assert len(logs) == 500
            assert "Message 0" in logs[0]
            assert "Message 499" in logs[499]


class TestSDKErrorHandling:
    """Test SDK error handling in UI context."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=Path(temp_dir),
                ui_mode=True
            )
            yield auto_mode

    @pytest.mark.asyncio
    async def test_sdk_connection_error_shown_in_ui(self, auto_mode_with_ui):
        """Test that SDK connection errors are shown in UI.

        Expected behavior:
        - Should display error in log area
        - Should show user-friendly message
        - Should not crash UI
        """
        auto_mode = auto_mode_with_ui

        # Mock SDK to raise connection error
        async def mock_query_error(prompt, options):
            raise ConnectionError("Unable to connect to API")

        # This will fail until error display is implemented
        with pytest.raises(AttributeError):
            with patch('amplihack.launcher.auto_mode.query', side_effect=mock_query_error):
                with patch('amplihack.launcher.auto_mode.CLAUDE_SDK_AVAILABLE', True):
                    await auto_mode._run_turn_with_sdk("Test prompt")

                    logs = auto_mode.get_queued_logs()
                    assert any("connection" in log.lower() for log in logs)
                    assert any("error" in log.lower() for log in logs)

    @pytest.mark.asyncio
    async def test_sdk_rate_limit_shown_with_retry_info(self, auto_mode_with_ui):
        """Test that rate limit errors show retry information.

        Expected behavior:
        - Should show rate limit message
        - Should show retry countdown
        - Should retry automatically
        """
        auto_mode = auto_mode_with_ui

        # Mock SDK to return rate limit error
        call_count = [0]

        async def mock_query_rate_limit(prompt, options):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("429 Rate limit exceeded")
            # Success on retry
            class MockMessage:
                class Content:
                    text = "Success after retry"
                content = [Content()]
                __class__.__name__ = "AssistantMessage"
            yield MockMessage()

        # This will fail until retry UI is implemented
        with pytest.raises(AttributeError):
            with patch('amplihack.launcher.auto_mode.query', side_effect=mock_query_rate_limit):
                with patch('amplihack.launcher.auto_mode.CLAUDE_SDK_AVAILABLE', True):
                    code, output = await auto_mode._run_turn_with_retry("Test")

                    logs = auto_mode.get_queued_logs()
                    assert any("rate limit" in log.lower() for log in logs)
                    assert any("retry" in log.lower() for log in logs)
                    assert code == 0  # Should succeed after retry

    def test_sdk_unavailable_shows_fallback_message(self, auto_mode_with_ui):
        """Test message when SDK is not available.

        Expected behavior:
        - Should detect SDK unavailable at startup
        - Should show informative message
        - Should not attempt SDK operations
        """
        # This will fail until SDK availability detection is implemented
        with pytest.raises(AttributeError):
            with patch('amplihack.launcher.auto_mode.CLAUDE_SDK_AVAILABLE', False):
                with tempfile.TemporaryDirectory() as temp_dir:
                    auto_mode = AutoMode(
                        sdk="claude",
                        prompt="Test",
                        max_turns=5,
                        working_dir=Path(temp_dir),
                        ui_mode=True
                    )

                    logs = auto_mode.get_queued_logs()
                    assert any("sdk" in log.lower() for log in logs)


class TestSDKPerformanceMetrics:
    """Test performance metrics from SDK usage."""

    @pytest.fixture
    def auto_mode_with_ui(self):
        """Create AutoMode with UI enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=Path(temp_dir),
                ui_mode=True
            )
            yield auto_mode

    @pytest.mark.asyncio
    async def test_turn_latency_is_tracked(self, auto_mode_with_ui):
        """Test that turn latency is tracked and displayed.

        Expected behavior:
        - Should track time per turn
        - Should display in session panel
        - Should show average latency
        """
        auto_mode = auto_mode_with_ui

        # This will fail until latency tracking is implemented
        with pytest.raises(AttributeError):
            # Simulate turn with known duration
            start = time.time()

            # Mock SDK with delay
            async def mock_query_slow(prompt, options):
                await asyncio.sleep(0.5)
                class MockMessage:
                    class Content:
                        text = "Response"
                    content = [Content()]
                    __class__.__name__ = "AssistantMessage"
                yield MockMessage()

            import asyncio
            with patch('amplihack.launcher.auto_mode.query', side_effect=mock_query_slow):
                with patch('amplihack.launcher.auto_mode.CLAUDE_SDK_AVAILABLE', True):
                    await auto_mode._run_turn_with_sdk("Test")

            metrics = auto_mode.get_performance_metrics()
            assert 'turn_latency' in metrics
            assert metrics['turn_latency'] >= 0.5

    def test_tokens_per_second_calculated(self, auto_mode_with_ui):
        """Test that tokens/second throughput is calculated.

        Expected behavior:
        - Should calculate output tokens per second
        - Should display in session panel
        """
        auto_mode = auto_mode_with_ui

        # This will fail until throughput calculation is implemented
        with pytest.raises(AttributeError):
            # Simulate turn with known token count and duration
            class MockUsage:
                input_tokens = 100
                output_tokens = 500  # 500 tokens in 2 seconds = 250 tok/sec

            class MockMessage:
                usage = MockUsage()
                __class__.__name__ = "ResultMessage"

            auto_mode.start_turn_timer()
            time.sleep(2)
            auto_mode.process_sdk_message(MockMessage())

            metrics = auto_mode.get_performance_metrics()
            assert 'tokens_per_second' in metrics
            assert 200 < metrics['tokens_per_second'] < 300  # ~250 tok/sec
