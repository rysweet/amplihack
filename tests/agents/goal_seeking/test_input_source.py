"""Unit tests for InputSource implementations.

Tests cover:
- ListInputSource: iteration, exhaustion, close(), remaining()
- StdinInputSource: normal reads, EOF, close
- ServiceBusInputSource: constructor guard (no azure-servicebus dependency needed for most tests)
- InputSource protocol conformance
- GoalSeekingAgent.run_ooda_loop integration with ListInputSource (mocked process())
"""

from __future__ import annotations

import io

import pytest

from amplihack.agents.goal_seeking.input_source import (
    InputSource,
    ListInputSource,
    StdinInputSource,
    _extract_text_from_bus_event,
)

# ---------------------------------------------------------------------------
# ListInputSource tests
# ---------------------------------------------------------------------------


class TestListInputSource:
    def test_returns_items_in_order(self):
        src = ListInputSource(["a", "b", "c"])
        assert src.next() == "a"
        assert src.next() == "b"
        assert src.next() == "c"

    def test_returns_none_when_exhausted(self):
        src = ListInputSource(["x"])
        src.next()
        assert src.next() is None

    def test_empty_list_returns_none_immediately(self):
        src = ListInputSource([])
        assert src.next() is None

    def test_close_makes_next_return_none(self):
        src = ListInputSource(["a", "b"])
        src.close()
        assert src.next() is None

    def test_remaining_tracks_unconsumed_items(self):
        src = ListInputSource(["a", "b", "c"])
        assert src.remaining() == 3
        src.next()
        assert src.remaining() == 2
        src.next()
        src.next()
        assert src.remaining() == 0

    def test_len(self):
        src = ListInputSource(["a", "b", "c", "d"])
        assert len(src) == 4

    def test_does_not_mutate_original_list(self):
        original = ["a", "b"]
        src = ListInputSource(original)
        src.next()
        assert original == ["a", "b"]

    def test_conforms_to_protocol(self):
        src = ListInputSource(["x"])
        assert isinstance(src, InputSource)


# ---------------------------------------------------------------------------
# StdinInputSource tests
# ---------------------------------------------------------------------------


class TestStdinInputSource:
    def test_reads_lines_from_stream(self):
        stream = io.StringIO("hello\nworld\n")
        src = StdinInputSource(stream=stream)
        assert src.next() == "hello"
        assert src.next() == "world"

    def test_eof_returns_none(self):
        stream = io.StringIO("")
        src = StdinInputSource(stream=stream)
        assert src.next() is None

    def test_empty_line_signals_eof_by_default(self):
        stream = io.StringIO("\n")
        src = StdinInputSource(stream=stream, eof_on_empty=True)
        assert src.next() is None

    def test_empty_line_not_eof_when_disabled(self):
        stream = io.StringIO("\nhello\n")
        src = StdinInputSource(stream=stream, eof_on_empty=False)
        assert src.next() == ""
        assert src.next() == "hello"

    def test_close_makes_next_return_none(self):
        stream = io.StringIO("hello\n")
        src = StdinInputSource(stream=stream)
        src.close()
        assert src.next() is None

    def test_strips_newline(self):
        stream = io.StringIO("line1\n")
        src = StdinInputSource(stream=stream)
        assert src.next() == "line1"

    def test_conforms_to_protocol(self):
        src = StdinInputSource(stream=io.StringIO())
        assert isinstance(src, InputSource)


# ---------------------------------------------------------------------------
# _extract_text_from_bus_event helper tests
# ---------------------------------------------------------------------------


class TestExtractTextFromBusEvent:
    def test_learn_content_returns_content(self):
        result = _extract_text_from_bus_event("LEARN_CONTENT", {"content": "hello"})
        assert result == "hello"

    def test_query_returns_question(self):
        result = _extract_text_from_bus_event("QUERY", {"question": "What is X?"})
        assert result == "What is X?"

    def test_input_event_returns_text(self):
        result = _extract_text_from_bus_event("INPUT", {"text": "some text"})
        assert result == "some text"

    def test_agent_ready_returns_none(self):
        assert _extract_text_from_bus_event("AGENT_READY", {}) is None

    def test_query_response_returns_none(self):
        assert _extract_text_from_bus_event("QUERY_RESPONSE", {}) is None

    def test_search_response_returns_none(self):
        assert _extract_text_from_bus_event("network_graph.search_response", {}) is None

    def test_feed_complete_returns_sentinel(self):
        result = _extract_text_from_bus_event("FEED_COMPLETE", {"total_turns": 5000})
        assert result == "__FEED_COMPLETE__:5000"

    def test_store_fact_batch_returns_sentinel(self):
        result = _extract_text_from_bus_event("STORE_FACT_BATCH", {"fact_batch": {"facts": []}})
        assert result == "__STORE_FACT_BATCH__"

    def test_generic_event_falls_back_to_content_field(self):
        result = _extract_text_from_bus_event("UNKNOWN_TYPE", {"content": "generic"})
        assert result == "generic"

    def test_empty_learn_content_returns_none(self):
        assert _extract_text_from_bus_event("LEARN_CONTENT", {"content": ""}) is None


# ---------------------------------------------------------------------------
# ServiceBusInputSource: constructor guard test
# ---------------------------------------------------------------------------


class TestServiceBusInputSourceGuard:
    def test_raises_import_error_without_azure_servicebus(self):
        """ServiceBusInputSource must raise ImportError when azure-servicebus is missing."""
        import importlib
        import sys

        original = sys.modules.get("azure.servicebus")
        sys.modules["azure.servicebus"] = None  # type: ignore[assignment]
        try:
            from amplihack.agents.goal_seeking import input_source as _is_mod

            importlib.reload(_is_mod)
            from amplihack.agents.goal_seeking.input_source import ServiceBusInputSource as _SBIs

            with pytest.raises((ImportError, TypeError)):
                _SBIs("Endpoint=sb://fake.servicebus.windows.net/;...", "agent-0")
        finally:
            if original is None:
                sys.modules.pop("azure.servicebus", None)
            else:
                sys.modules["azure.servicebus"] = original


# ---------------------------------------------------------------------------
# GoalSeekingAgent.run_ooda_loop integration test (mocked process)
# ---------------------------------------------------------------------------


class TestRunOodaLoop:
    def test_processes_all_turns_in_order(self):
        """run_ooda_loop calls process() once per turn with correct text."""
        from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent

        agent = GoalSeekingAgent.__new__(GoalSeekingAgent)
        agent._agent_name = "test-agent"
        processed = []
        agent.process = lambda text: processed.append(text) or ""

        src = ListInputSource(["turn-1", "turn-2", "turn-3"])
        agent.run_ooda_loop(src)

        assert processed == ["turn-1", "turn-2", "turn-3"]

    def test_exits_on_none(self):
        """run_ooda_loop exits cleanly when next() returns None."""
        from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent

        agent = GoalSeekingAgent.__new__(GoalSeekingAgent)
        agent._agent_name = "test-agent"
        call_count = [0]
        agent.process = lambda _: (call_count.__setitem__(0, call_count[0] + 1) or "")

        src = ListInputSource([])
        agent.run_ooda_loop(src)
        assert call_count[0] == 0

    def test_skips_feed_complete_sentinel(self):
        """FEED_COMPLETE sentinel is not forwarded to process()."""
        from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent

        agent = GoalSeekingAgent.__new__(GoalSeekingAgent)
        agent._agent_name = "test-agent"
        processed = []
        agent.process = lambda text: processed.append(text) or ""

        src = ListInputSource(["real-turn", "__FEED_COMPLETE__:100"])
        agent.run_ooda_loop(src)

        assert processed == ["real-turn"]
        assert "__FEED_COMPLETE__:100" not in processed

    def test_continues_after_process_exception(self):
        """run_ooda_loop continues to next turn when process() raises."""
        from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent

        agent = GoalSeekingAgent.__new__(GoalSeekingAgent)
        agent._agent_name = "test-agent"
        processed = []

        def _process(text):
            if text == "bad":
                raise RuntimeError("simulated error")
            processed.append(text)
            return ""

        agent.process = _process

        src = ListInputSource(["good-1", "bad", "good-2"])
        agent.run_ooda_loop(src)

        assert processed == ["good-1", "good-2"]
