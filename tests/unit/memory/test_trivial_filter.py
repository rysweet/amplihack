"""Unit tests fer trivial content filtering logic.

Tests pre-filter logic that rejects low-value content before
storage pipeline to save processing time.

Philosophy:
- Fast rejection of obvious trivial content
- Clear rules fer what constitutes trivial
- Transparent filtering decisions
"""

from typing import Any

import pytest

# These imports will fail until implementation exists (TDD)
try:
    from amplihack.memory.trivial_filter import (
        FilterReason,
        FilterResult,
        TrivialFilter,
        is_already_documented,
        is_temporary_debug,
        is_trivial_command,
        is_trivial_greeting,
    )
except ImportError:
    pytest.skip("Trivial filter not implemented yet", allow_module_level=True)


class TestTrivialGreetingDetection:
    """Test detection of simple greetings without context."""

    def test_simple_hello_is_trivial(self):
        """Simple 'hello' without context is trivial."""
        assert is_trivial_greeting("Hello")
        assert is_trivial_greeting("Hi there")
        assert is_trivial_greeting("Hey")

    def test_greeting_with_context_not_trivial(self):
        """Greeting with actual question is not trivial."""
        assert not is_trivial_greeting("Hello, can you help me fix this bug?")
        assert not is_trivial_greeting("Hi, I need to implement authentication")

    def test_greeting_in_conversation_not_trivial(self):
        """Greeting as part of larger conversation is not trivial."""
        content = "Hello! I'm working on the auth module and ran into an issue..."
        assert not is_trivial_greeting(content)

    def test_multiple_greetings_still_trivial(self):
        """Multiple greetings without substance still trivial."""
        assert is_trivial_greeting("Hi! Hello there! How are you?")

    def test_empty_string_not_trivial(self):
        """Empty content is handled separately, not as greeting."""
        assert not is_trivial_greeting("")


class TestTrivialCommandDetection:
    """Test detection of commands that succeeded without learnings."""

    def test_successful_ls_is_trivial(self):
        """Simple ls command that succeeded is trivial."""
        context = {
            "command": "ls",
            "exit_code": 0,
            "output": "file1.py\nfile2.py",
            "learnings": None,
        }
        assert is_trivial_command(context)

    def test_failed_command_not_trivial(self):
        """Failed command provides learning opportunity."""
        context = {
            "command": "pytest",
            "exit_code": 1,
            "output": "FAILED tests/test_auth.py",
            "learnings": None,
        }
        assert not is_trivial_command(context)

    def test_command_with_learning_not_trivial(self):
        """Command with explicit learning is not trivial."""
        context = {
            "command": "git status",
            "exit_code": 0,
            "output": "nothing to commit",
            "learnings": "Project state is clean before starting work",
        }
        assert not is_trivial_command(context)

    def test_complex_command_not_trivial(self):
        """Complex commands are worth remembering."""
        context = {
            "command": "find . -name '*.py' | xargs grep 'TODO'",
            "exit_code": 0,
            "output": "Found 5 TODOs",
            "learnings": None,
        }
        assert not is_trivial_command(context)

    def test_command_with_side_effects_not_trivial(self):
        """Commands that modify state are not trivial."""
        context = {
            "command": "git commit -m 'Fix bug'",
            "exit_code": 0,
            "output": "1 file changed",
            "learnings": None,
        }
        assert not is_trivial_command(context)


class TestDocumentationCheck:
    """Test detection of information already in documentation."""

    def test_documented_fact_is_trivial(self):
        """Information directly from docs is trivial to store."""
        content = "amplihack uses specialized agents fer different tasks"
        docs_content = [
            "amplihack architecture uses specialized agents",
            "different agents handle different tasks",
        ]
        assert is_already_documented(content, docs_content)

    def test_new_insight_not_trivial(self):
        """New insight not in docs should be stored."""
        content = "architect agent works better when given module specs first"
        docs_content = [
            "architect agent designs systems",
            "module specs define contracts",
        ]
        assert not is_already_documented(content, docs_content)

    def test_rephrased_documentation_is_trivial(self):
        """Rephrasing of existing docs is trivial."""
        content = "Agents in amplihack are specialized fer specific tasks"
        docs_content = [
            "amplihack uses specialized agents",
            "each agent handles specific tasks",
        ]
        assert is_already_documented(content, docs_content)

    def test_empty_docs_nothing_trivial(self):
        """With no docs, nothing can be documented."""
        content = "Some fact"
        docs_content = []
        assert not is_already_documented(content, docs_content)


class TestTemporaryDebugDetection:
    """Test detection of temporary debugging output."""

    def test_print_statement_output_trivial(self):
        """Debug print output is trivial."""
        assert is_temporary_debug("DEBUG: x = 42")
        assert is_temporary_debug("print: Processing item 5")
        assert is_temporary_debug("TRACE: Entering function foo()")

    def test_meaningful_log_not_trivial(self):
        """Meaningful log with error info not trivial."""
        assert not is_temporary_debug("ERROR: Authentication failed fer user john@example.com")
        assert not is_temporary_debug("WARNING: Rate limit approaching (90% capacity)")

    def test_stack_trace_not_trivial(self):
        """Stack traces contain valuable debugging info."""
        trace = """Traceback (most recent call last):
  File "auth.py", line 42, in validate_token
    raise ValueError("Invalid token")
ValueError: Invalid token"""
        assert not is_temporary_debug(trace)

    def test_variable_dump_trivial(self):
        """Variable dumps without context are trivial."""
        assert is_temporary_debug("x=1, y=2, z=3")
        assert is_temporary_debug("vars: {'foo': 'bar', 'baz': 42}")


class TestFilterResult:
    """Test FilterResult data structure."""

    def test_filter_result_not_trivial(self):
        """FilterResult fer non-trivial content."""
        result = FilterResult(
            is_trivial=False,
            reason=None,
            confidence=1.0,
        )
        assert not result.is_trivial
        assert result.reason is None
        assert result.should_store()

    def test_filter_result_trivial_with_reason(self):
        """FilterResult fer trivial content includes reason."""
        result = FilterResult(
            is_trivial=True,
            reason=FilterReason.SIMPLE_GREETING,
            confidence=0.95,
        )
        assert result.is_trivial
        assert result.reason == FilterReason.SIMPLE_GREETING
        assert not result.should_store()

    def test_filter_result_confidence_threshold(self):
        """Low confidence trivial detection allows storage."""
        result = FilterResult(
            is_trivial=True,
            reason=FilterReason.SIMPLE_GREETING,
            confidence=0.3,  # Low confidence
        )
        # With low confidence, allow storage fer agent review
        assert result.should_store_despite_low_confidence()


class TestFilterReason:
    """Test FilterReason enum."""

    def test_filter_reason_enum_complete(self):
        """All expected filter reasons are defined."""
        assert FilterReason.SIMPLE_GREETING
        assert FilterReason.SUCCESSFUL_SIMPLE_COMMAND
        assert FilterReason.ALREADY_DOCUMENTED
        assert FilterReason.TEMPORARY_DEBUG
        assert FilterReason.EMPTY_CONTENT
        assert FilterReason.TOO_SHORT

    def test_filter_reason_has_description(self):
        """Each reason has human-readable description."""
        reason = FilterReason.SIMPLE_GREETING
        assert reason.description
        assert len(reason.description) > 10


class TestTrivialFilter:
    """Test complete TrivialFilter with all rules."""

    def test_filter_empty_content(self):
        """Empty content is trivial."""
        filter = TrivialFilter()
        result = filter.evaluate("")

        assert result.is_trivial
        assert result.reason == FilterReason.EMPTY_CONTENT

    def test_filter_too_short_content(self):
        """Very short content (< 10 chars) is likely trivial."""
        filter = TrivialFilter()
        result = filter.evaluate("ok")

        assert result.is_trivial
        assert result.reason == FilterReason.TOO_SHORT

    def test_filter_simple_greeting(self):
        """Simple greetings are filtered."""
        filter = TrivialFilter()
        result = filter.evaluate("Hello")

        assert result.is_trivial
        assert result.reason == FilterReason.SIMPLE_GREETING

    def test_filter_allows_meaningful_content(self):
        """Meaningful content passes filter."""
        filter = TrivialFilter()
        result = filter.evaluate(
            "Discovered that architect agent performs better when given module specs first"
        )

        assert not result.is_trivial
        assert result.reason is None

    def test_filter_with_context_command_success(self):
        """Filter considers context - successful simple commands."""
        filter = TrivialFilter()
        context = {
            "command": "ls",
            "exit_code": 0,
            "learnings": None,
        }
        result = filter.evaluate("Listed files", context)

        assert result.is_trivial
        assert result.reason == FilterReason.SUCCESSFUL_SIMPLE_COMMAND

    def test_filter_with_context_command_failure(self):
        """Filter considers context - failed commands are valuable."""
        filter = TrivialFilter()
        context = {
            "command": "pytest",
            "exit_code": 1,
            "learnings": None,
        }
        result = filter.evaluate("Tests failed", context)

        assert not result.is_trivial

    def test_filter_custom_rules(self):
        """TrivialFilter accepts custom rules."""

        def custom_rule(content: str, context: dict[str, Any]) -> FilterResult:
            if "internal-token-xyz" in content:
                return FilterResult(
                    is_trivial=True,
                    reason=FilterReason.TEMPORARY_DEBUG,
                    confidence=1.0,
                )
            return FilterResult(is_trivial=False, reason=None, confidence=1.0)

        filter = TrivialFilter(custom_rules=[custom_rule])
        result = filter.evaluate("Debug: internal-token-xyz")

        assert result.is_trivial

    def test_filter_statistics_tracking(self):
        """TrivialFilter tracks filtering statistics."""
        filter = TrivialFilter()

        filter.evaluate("Hello")  # Trivial
        filter.evaluate("Meaningful learning about agents")  # Not trivial
        filter.evaluate("Hi")  # Trivial

        stats = filter.get_statistics()
        assert stats["total_evaluated"] == 3
        assert stats["filtered_count"] == 2
        assert stats["passed_count"] == 1
        assert stats["filter_rate"] == pytest.approx(2 / 3)

    def test_filter_reason_distribution(self):
        """TrivialFilter tracks distribution of filter reasons."""
        filter = TrivialFilter()

        filter.evaluate("Hello")  # SIMPLE_GREETING
        filter.evaluate("Hi")  # SIMPLE_GREETING
        filter.evaluate("")  # EMPTY_CONTENT

        stats = filter.get_statistics()
        reason_dist = stats["reason_distribution"]

        assert reason_dist[FilterReason.SIMPLE_GREETING] == 2
        assert reason_dist[FilterReason.EMPTY_CONTENT] == 1


class TestFilteringPerformance:
    """Test that filtering is fast (pre-filter optimization)."""

    def test_filter_completes_quickly(self):
        """Filtering should complete in <1ms per item."""
        import time

        filter = TrivialFilter()
        content = "Some test content that needs filtering"

        start = time.perf_counter()
        for _ in range(1000):
            filter.evaluate(content)
        duration = time.perf_counter() - start

        # Should handle 1000 items in <1 second (1ms each)
        assert duration < 1.0

    def test_filter_scalable_to_large_content(self):
        """Filter handles large content efficiently."""
        import time

        filter = TrivialFilter()
        large_content = "test " * 10000  # 50k chars

        start = time.perf_counter()
        filter.evaluate(large_content)
        duration = time.perf_counter() - start

        # Even large content should filter quickly (<10ms)
        assert duration < 0.01
