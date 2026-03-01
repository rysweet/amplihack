"""Tests for the per-session reasoning loop.

Tests context gathering, decision parsing, and dry-run behavior.
All LLM calls are mocked.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet.fleet_session_reasoner import (
    AnthropicBackend,
    LLMBackend,
    SessionContext,
    SessionDecision,
    SessionReasoner,
)


class MockBackend(LLMBackend):
    """Mock LLM backend for testing."""

    def __init__(self, response: str = ""):
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.response


class TestSessionContext:
    """Unit tests for SessionContext."""

    def test_to_prompt_context_minimal(self):
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")
        prompt = ctx.to_prompt_context()
        assert "vm-1" in prompt
        assert "sess-1" in prompt

    def test_to_prompt_context_full(self):
        ctx = SessionContext(
            vm_name="vm-1",
            session_name="sess-1",
            tmux_capture="Which approach? [1/2/3]",
            git_branch="feat/auth",
            repo_url="https://github.com/org/api",
            agent_status="waiting_input",
            task_prompt="Fix the auth bug",
            project_priorities="Security first",
        )
        prompt = ctx.to_prompt_context()
        assert "feat/auth" in prompt
        assert "Fix the auth bug" in prompt
        assert "Security first" in prompt
        assert "Which approach?" in prompt

    def test_to_prompt_context_truncates_long_tmux(self):
        ctx = SessionContext(
            vm_name="vm-1",
            session_name="sess-1",
            tmux_capture="x" * 5000,
        )
        prompt = ctx.to_prompt_context()
        assert len(prompt) < 5000  # Truncated


class TestSessionDecision:
    """Unit tests for SessionDecision."""

    def test_summary_send_input(self):
        decision = SessionDecision(
            session_name="sess-1",
            vm_name="vm-1",
            action="send_input",
            input_text="1",
            reasoning="Choosing simplest approach",
            confidence=0.9,
        )
        summary = decision.summary()
        assert "send_input" in summary
        assert "simplest approach" in summary
        assert '"1"' in summary

    def test_summary_wait(self):
        decision = SessionDecision(
            session_name="sess-1",
            vm_name="vm-1",
            action="wait",
            reasoning="Agent is working fine",
            confidence=0.8,
        )
        summary = decision.summary()
        assert "wait" in summary
        assert "working fine" in summary


class TestSessionReasonerDecisionParsing:
    """Tests that the reasoner correctly parses LLM responses."""

    def test_parse_valid_json_response(self):
        mock = MockBackend(response=json.dumps({
            "action": "send_input",
            "input_text": "2",
            "reasoning": "Option 2 is best for performance",
            "confidence": 0.85,
        }))

        reasoner = SessionReasoner(backend=mock, dry_run=True)
        ctx = SessionContext(
            vm_name="vm-1",
            session_name="sess-1",
            tmux_capture="Choose option [1/2/3]:",
            agent_status="waiting_input",
        )

        decision = reasoner._reason(ctx)
        assert decision.action == "send_input"
        assert decision.input_text == "2"
        assert decision.confidence == 0.85

    def test_parse_json_with_markdown_wrapping(self):
        mock = MockBackend(response='```json\n{"action": "wait", "reasoning": "all good", "confidence": 0.9}\n```')

        reasoner = SessionReasoner(backend=mock, dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")

        decision = reasoner._reason(ctx)
        assert decision.action == "wait"

    def test_parse_invalid_response(self):
        mock = MockBackend(response="I don't understand")

        reasoner = SessionReasoner(backend=mock, dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")

        decision = reasoner._reason(ctx)
        assert decision.action == "wait"
        assert decision.confidence <= 0.5

    def test_backend_failure(self):
        class FailingBackend(LLMBackend):
            def complete(self, system_prompt, user_prompt):
                raise ConnectionError("API down")

        reasoner = SessionReasoner(backend=FailingBackend(), dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")

        decision = reasoner._reason(ctx)
        assert decision.action == "escalate"
        assert "failed" in decision.reasoning.lower()


class TestSessionReasonerStatusInference:
    """Tests for tmux output status inference — especially thinking detection."""

    def test_infer_waiting_input_yn(self):
        reasoner = SessionReasoner(dry_run=True)
        assert reasoner._infer_status("Continue? [Y/n]") == "waiting_input"

    def test_infer_error(self):
        reasoner = SessionReasoner(dry_run=True)
        assert reasoner._infer_status("Traceback (most recent call last):") == "error"

    def test_infer_completed_pr_created(self):
        reasoner = SessionReasoner(dry_run=True)
        assert reasoner._infer_status("PR #42 created successfully") == "completed"

    def test_infer_idle_shell_prompt(self):
        reasoner = SessionReasoner(dry_run=True)
        assert reasoner._infer_status("azureuser@vm:~/code$ ") == "idle"

    def test_infer_running_output(self):
        reasoner = SessionReasoner(dry_run=True)
        # Needs >50 chars of content to distinguish from unknown
        tmux = "Step 5: Building the authentication module\nReading file src/auth/handler.py"
        assert reasoner._infer_status(tmux) == "running"

    # --- Thinking detection (critical for not interrupting agents) ---

    def test_thinking_claude_tool_call(self):
        """Claude Code shows ● for active tool calls."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "● Reading file src/auth.py"
        assert reasoner._infer_status(tmux) == "thinking"

    def test_thinking_claude_streaming_output(self):
        """Claude Code shows ⎿ for streaming tool output."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "● Bash(git status)\n  ⎿  M src/auth.py"
        assert reasoner._infer_status(tmux) == "thinking"

    def test_thinking_claude_processing(self):
        """Claude Code shows ✻ Sautéed for processing time."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "✻ Sautéed for 2m 28s"
        assert reasoner._infer_status(tmux) == "thinking"

    def test_thinking_claude_bash_tool(self):
        """Claude Code actively running a Bash tool."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "some prior output\n● Bash(uv run python -m pytest tests/ -v)"
        assert reasoner._infer_status(tmux) == "thinking"

    def test_thinking_copilot(self):
        """Copilot shows Thinking... indicator."""
        reasoner = SessionReasoner(dry_run=True)
        assert reasoner._infer_status("Thinking...") == "thinking"

    def test_waiting_claude_permission_prompt(self):
        """Claude Code permission prompt with ⏵⏵."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "❯ \n──────\n  ~/src/repo  ⏵⏵ bypass permissions on"
        assert reasoner._infer_status(tmux) == "waiting_input"

    def test_waiting_claude_idle_with_status_bar(self):
        """Claude Code at ❯ prompt but with status bar = waiting for input."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "❯ \n──────\n  ~/src  Opus 4.6  ⏵⏵ bypass permissions"
        assert reasoner._infer_status(tmux) == "waiting_input"

    def test_thinking_fast_path_skips_llm(self):
        """When status is thinking, the LLM call is skipped entirely."""
        mock = MockBackend(response='{"action":"wait","reasoning":"ok","confidence":0.8}')

        reasoner = SessionReasoner(backend=mock, dry_run=True)

        with patch.object(reasoner, "_gather_context") as mock_gather:
            mock_gather.return_value = SessionContext(
                vm_name="vm-1",
                session_name="sess-1",
                tmux_capture="● Reading file main.py",
                agent_status="thinking",
            )

            decision = reasoner.reason_about_session("vm-1", "sess-1")

            assert decision.action == "wait"
            assert decision.confidence == 1.0
            assert "thinking" in decision.reasoning.lower()
            # Key: LLM backend was NOT called
            assert len(mock.calls) == 0


class TestSessionReasonerDryRun:
    """Tests for dry-run mode."""

    def test_dry_run_does_not_execute(self):
        mock = MockBackend(response=json.dumps({
            "action": "send_input",
            "input_text": "yes",
            "reasoning": "Approving",
            "confidence": 0.9,
        }))

        reasoner = SessionReasoner(backend=mock, dry_run=True)

        # Mock the gather to avoid SSH
        with patch.object(reasoner, "_gather_context") as mock_gather:
            mock_gather.return_value = SessionContext(
                vm_name="vm-1",
                session_name="sess-1",
                tmux_capture="Proceed? [Y/n]",
                agent_status="waiting_input",
            )

            decision = reasoner.reason_about_session("vm-1", "sess-1")

            assert decision.action == "send_input"
            assert decision.input_text == "yes"
            # Key: _execute_decision should NOT have been called with SSH
            assert len(reasoner._decisions) == 1

    def test_dry_run_report(self):
        mock = MockBackend(response=json.dumps({
            "action": "wait",
            "reasoning": "Working fine",
            "confidence": 0.8,
        }))

        reasoner = SessionReasoner(backend=mock, dry_run=True)
        reasoner._decisions = [
            SessionDecision(session_name="s1", vm_name="vm-1", action="wait", reasoning="ok"),
            SessionDecision(session_name="s2", vm_name="vm-1", action="send_input", input_text="1", reasoning="chose 1"),
        ]

        report = reasoner.dry_run_report()
        assert "2 sessions analyzed" in report
        assert "wait: 1" in report
        assert "send_input: 1" in report


class TestLLMBackends:
    """Tests for LLM backend protocol."""

    def test_mock_backend(self):
        backend = MockBackend(response="test response")
        result = backend.complete("system", "user")
        assert result == "test response"
        assert len(backend.calls) == 1
        assert backend.calls[0] == ("system", "user")

    def test_llm_backend_protocol(self):
        """LLMBackend is a Protocol — cannot be instantiated directly."""
        from typing import Protocol
        from amplihack.fleet.fleet_session_reasoner import LLMBackend

        assert issubclass(LLMBackend, Protocol)
        with pytest.raises(TypeError, match="Protocols cannot be instantiated"):
            LLMBackend()
