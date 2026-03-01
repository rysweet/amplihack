"""Tests for the per-session reasoning loop.

Tests context gathering, decision parsing, and dry-run behavior.
All LLM calls are mocked.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet.fleet_session_reasoner import (
    AnthropicBackend,
    CopilotBackend,
    LiteLLMBackend,
    LLMBackend,
    SessionContext,
    SessionDecision,
    SessionReasoner,
    auto_detect_backend,
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
    """Tests for tmux output status inference — especially thinking detection.

    Test cases are derived from REAL live data observed across 9 sessions on 4 VMs.
    """

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

    def test_thinking_claude_bash_tool(self):
        """Claude Code actively running a Bash tool."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "some prior output\n● Bash(uv run python -m pytest tests/ -v)"
        assert reasoner._infer_status(tmux) == "thinking"

    def test_thinking_copilot(self):
        """Copilot shows Thinking... indicator."""
        reasoner = SessionReasoner(dry_run=True)
        assert reasoner._infer_status("Thinking...") == "thinking"

    def test_idle_claude_bare_prompt_with_bypass_status(self):
        """Bare ❯ prompt + status bar showing 'bypass on' = IDLE, not waiting.

        The status bar text '⏵⏵ bypass permissions on' describes the current mode,
        NOT a permission request. The agent is idle at the prompt.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "❯ \n──────\n  ~/src/repo  ⏵⏵ bypass permissions on"
        assert reasoner._infer_status(tmux) == "idle"

    # --- FIX 1: ✻ (timing verb) = JUST FINISHED thinking, not active thinking ---

    def test_finished_thinking_then_idle(self):
        """✻ past-tense verb followed by bare ❯ prompt = IDLE, not thinking.

        Real live data: '✻ Brewed for 6m 11s' means agent finished processing.
        If followed by bare prompt, agent is idle at prompt waiting for next task.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "✻ Brewed for 6m 11s\n❯ \n  ⏵⏵ bypass permissions on"
        assert reasoner._infer_status(tmux) == "idle"

    def test_finished_thinking_cogitated_then_idle(self):
        """✻ Cogitated for Xm Ys + bare prompt = IDLE."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "some output\n✻ Cogitated for 4m 2s\n❯ \n  ~/src  Opus 4.6  ⏵⏵ bypass"
        assert reasoner._infer_status(tmux) == "idle"

    def test_finished_thinking_sauteed_then_idle(self):
        """✻ Sautéed for Xm Ys + bare prompt = IDLE."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "✻ Sautéed for 2m 28s\n❯ \n  ⏵⏵ on"
        assert reasoner._infer_status(tmux) == "idle"

    def test_finished_thinking_no_prompt_yet(self):
        """✻ alone without prompt = still finishing up = thinking."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "✻ Sautéed for 2m 28s"
        assert reasoner._infer_status(tmux) == "thinking"

    # --- FIX 1b: · (middle dot) with active verb = CURRENTLY thinking ---

    def test_active_thinking_middle_dot_scampering(self):
        """· Scampering... with middle dot = CURRENTLY thinking.

        Real live data: '· Scampering… (3m 20s · ↓ 575 tokens)' means agent
        is actively processing right now.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "\u00b7 Scampering\u2026 (3m 20s \u00b7 \u2193 575 tokens)"
        assert reasoner._infer_status(tmux) == "thinking"

    def test_active_thinking_middle_dot_brewing(self):
        """· Brewing... = CURRENTLY thinking."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "\u00b7 Brewing\u2026"
        assert reasoner._infer_status(tmux) == "thinking"

    def test_active_thinking_middle_dot_with_prior_output(self):
        """Middle dot active verb after prior output = thinking."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "some prior tool output\n\u00b7 Saut\u00e9ing\u2026 (1m 5s)"
        assert reasoner._infer_status(tmux) == "thinking"

    # --- FIX 2: ❯ with user text = agent processing input, not idle ---

    def test_prompt_with_user_input_is_thinking(self):
        """❯ followed by user text = agent processing submitted input.

        Real live data: '❯ now close issue 12 and commit the .gitignore change'
        means user typed input and agent is working on it.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "❯ now close issue 12 and commit the .gitignore change\n  ⏵⏵ bypass permissions on"
        assert reasoner._infer_status(tmux) == "thinking"

    def test_prompt_with_user_input_no_status_bar(self):
        """❯ with user text but no status bar = still thinking."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "❯ fix the auth module and run tests"
        assert reasoner._infer_status(tmux) == "thinking"

    def test_bare_prompt_with_status_bar_is_idle(self):
        """Bare ❯ with status bar = idle (waiting for next task).

        Real live data: bare '❯ ' with '⏵⏵' = truly idle.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "❯ \n  ⏵⏵ bypass permissions on"
        assert reasoner._infer_status(tmux) == "idle"

    def test_bare_prompt_no_status_bar_is_idle(self):
        """Bare ❯ without status bar = idle."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "some output\n❯ "
        assert reasoner._infer_status(tmux) == "idle"

    def test_finished_then_user_typed_input(self):
        """✻ finished indicator + ❯ with user text = thinking (processing new input).

        Real scenario: agent finished one task, user typed next task at prompt.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "✻ Brewed for 6m 11s\n❯ now fix the tests\n  ⏵⏵ bypass on"
        assert reasoner._infer_status(tmux) == "thinking"

    # --- FIX 3: Status bar "(running)" = running ---

    def test_status_bar_running_indicator(self):
        """Status bar with '(running)' suffix = subagent/background task active.

        Real live data: '· Wire LadybugDB backend for graph-query (running)'
        in status bar means a background task is running.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "❯ \n  ~/src  ⏵⏵ · Wire LadybugDB backend for graph-query (running)"
        assert reasoner._infer_status(tmux) == "running"

    def test_status_bar_running_with_prompt(self):
        """(running) in status bar even with bare prompt = running."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "some output\n❯ \n  ⏵⏵ Implement auth (running)"
        assert reasoner._infer_status(tmux) == "running"

    # --- Regression tests for existing behavior that must still work ---

    def test_waiting_input_yes_no_prompt(self):
        reasoner = SessionReasoner(dry_run=True)
        assert reasoner._infer_status("Do you want to continue? (yes/no)") == "waiting_input"

    def test_waiting_claude_permission_allow_no_prompt(self):
        """Claude Code permission prompt with 'allow' but no bare ❯ prompt = waiting."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "Some tool output\n  ⏵⏵ allow all"
        assert reasoner._infer_status(tmux) == "waiting_input"

    def test_waiting_claude_actual_permission_request(self):
        """Real permission request scenario: tool wants to run, asking for approval.

        When Claude Code asks for permission, the Y/n prompt is the last line.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "I need to run a cleanup command.\nAllow this tool call? [Y/n]"
        assert reasoner._infer_status(tmux) == "waiting_input"

    def test_error_fatal(self):
        reasoner = SessionReasoner(dry_run=True)
        assert reasoner._infer_status("fatal: not a git repository") == "error"

    def test_completed_workflow(self):
        reasoner = SessionReasoner(dry_run=True)
        assert reasoner._infer_status("GOAL_STATUS: ACHIEVED") == "completed"

    def test_idle_bare_shell(self):
        reasoner = SessionReasoner(dry_run=True)
        assert reasoner._infer_status("user@host:~/code$") == "idle"

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

    # --- Combined real-world scenario tests ---

    def test_real_scenario_agent_just_finished_at_prompt(self):
        """Full realistic tmux capture: agent finished task, sitting at prompt.

        This is the most common misdetection case from live testing.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = """  I've completed the implementation of the new auth module.
  The tests are passing and the PR has been created.

✻ Cogitated for 4m 2s

❯
  ~/src/amplihack  main  Opus 4.6  ⏵⏵ bypass permissions on"""
        assert reasoner._infer_status(tmux) == "idle"

    def test_real_scenario_agent_actively_processing(self):
        """Full realistic tmux: agent is mid-thought with streaming indicator."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = """  Let me analyze the codebase structure...

· Scampering\u2026 (2m 15s \u00b7 \u2193 1.2k tokens)"""
        assert reasoner._infer_status(tmux) == "thinking"

    def test_real_scenario_user_just_submitted_task(self):
        """Full realistic tmux: user typed a command at the prompt."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = """✻ Brewed for 3m 45s

❯ now close issue 12 and commit the .gitignore change
  ⏵⏵ bypass permissions on"""
        assert reasoner._infer_status(tmux) == "thinking"


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

    def test_copilot_backend_import_error(self):
        """CopilotBackend.complete raises ImportError when copilot-sdk not installed."""
        backend = CopilotBackend(model="gpt-4o")
        assert backend.model == "gpt-4o"
        # Simulate copilot-sdk not being installed
        with patch.dict("sys.modules", {"copilot": None}):
            with pytest.raises((ImportError, ModuleNotFoundError)):
                backend.complete("system", "user")

    def test_litellm_backend_import_error(self):
        """LiteLLMBackend.complete raises ImportError when litellm not installed."""
        backend = LiteLLMBackend(model="gpt-4o")
        assert backend.model == "gpt-4o"
        # Patch litellm import to simulate missing package
        with patch.dict("sys.modules", {"litellm": None}):
            with pytest.raises((ImportError, ModuleNotFoundError)):
                backend.complete("system", "user")

    def test_auto_detect_with_anthropic_key(self):
        """auto_detect_backend returns AnthropicBackend when ANTHROPIC_API_KEY is set."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-123"}):
            backend = auto_detect_backend()
            assert isinstance(backend, AnthropicBackend)

    def test_auto_detect_without_any_backend(self):
        """auto_detect_backend raises RuntimeError when no backend is available."""
        with patch.dict(os.environ, {}, clear=True):
            with patch.dict("sys.modules", {"litellm": None, "copilot": None}):
                with pytest.raises(RuntimeError, match="No LLM backend available"):
                    auto_detect_backend()
