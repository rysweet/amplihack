"""Tests for the per-session reasoning loop.

Tests context gathering, decision parsing, and dry-run behavior.
All LLM calls are mocked.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet._backends import (
    AnthropicBackend,
    CopilotBackend,
    LiteLLMBackend,
    LLMBackend,
    auto_detect_backend,
)
from amplihack.fleet._session_context import SessionContext, SessionDecision
from amplihack.fleet._status import infer_agent_status
from amplihack.fleet._session_gather import parse_context_output
from amplihack.fleet.fleet_session_reasoner import SessionReasoner


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

    def test_to_prompt_context_preserves_full_tmux(self):
        ctx = SessionContext(
            vm_name="vm-1",
            session_name="sess-1",
            tmux_capture="x" * 5000,
        )
        prompt = ctx.to_prompt_context()
        assert "x" * 5000 in prompt  # Full content preserved, no truncation

    def test_session_context_rejects_invalid_session_name(self):
        """SessionContext.__post_init__ rejects session names with shell metacharacters."""
        with pytest.raises(ValueError):
            SessionContext(vm_name="vm-1", session_name="bad;name")

    def test_session_context_accepts_valid_session_name(self):
        """SessionContext.__post_init__ accepts clean alphanumeric session names."""
        ctx = SessionContext(vm_name="vm-1", session_name="copilot")
        assert ctx.session_name == "copilot"


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
        assert infer_agent_status("Continue? [Y/n]") == "waiting_input"

    def test_infer_error(self):
        reasoner = SessionReasoner(dry_run=True)
        assert infer_agent_status("Traceback (most recent call last):") == "error"

    def test_infer_completed_pr_created(self):
        reasoner = SessionReasoner(dry_run=True)
        assert infer_agent_status("PR #42 created successfully") == "completed"

    def test_infer_shell_prompt(self):
        """Bare shell prompt ($) means agent is dead, distinct from idle (❯)."""
        reasoner = SessionReasoner(dry_run=True)
        assert infer_agent_status("azureuser@vm:~/code$ ") == "shell"

    def test_infer_running_output(self):
        reasoner = SessionReasoner(dry_run=True)
        # Needs >50 chars of content to distinguish from unknown
        tmux = "Step 5: Building the authentication module\nReading file src/auth/handler.py"
        assert infer_agent_status(tmux) == "running"

    # --- Thinking detection (critical for not interrupting agents) ---

    def test_thinking_claude_tool_call(self):
        """Claude Code shows ● for active tool calls."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "● Reading file src/auth.py"
        assert infer_agent_status(tmux) == "thinking"

    def test_thinking_claude_streaming_output(self):
        """Claude Code shows ⎿ for streaming tool output."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "● Bash(git status)\n  ⎿  M src/auth.py"
        assert infer_agent_status(tmux) == "thinking"

    def test_thinking_claude_bash_tool(self):
        """Claude Code actively running a Bash tool."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "some prior output\n● Bash(uv run python -m pytest tests/ -v)"
        assert infer_agent_status(tmux) == "thinking"

    def test_thinking_copilot(self):
        """Copilot shows Thinking... indicator."""
        reasoner = SessionReasoner(dry_run=True)
        assert infer_agent_status("Thinking...") == "thinking"

    def test_idle_claude_bare_prompt_with_bypass_status(self):
        """Bare ❯ prompt + status bar showing 'bypass on' = IDLE, not waiting.

        The status bar text '⏵⏵ bypass permissions on' describes the current mode,
        NOT a permission request. The agent is idle at the prompt.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "❯ \n──────\n  ~/src/repo  ⏵⏵ bypass permissions on"
        assert infer_agent_status(tmux) == "idle"

    # --- FIX 1: ✻ (timing verb) = JUST FINISHED thinking, not active thinking ---

    def test_finished_thinking_then_idle(self):
        """✻ past-tense verb followed by bare ❯ prompt = IDLE, not thinking.

        Real live data: '✻ Brewed for 6m 11s' means agent finished processing.
        If followed by bare prompt, agent is idle at prompt waiting for next task.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "✻ Brewed for 6m 11s\n❯ \n  ⏵⏵ bypass permissions on"
        assert infer_agent_status(tmux) == "idle"

    def test_finished_thinking_cogitated_then_idle(self):
        """✻ Cogitated for Xm Ys + bare prompt = IDLE."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "some output\n✻ Cogitated for 4m 2s\n❯ \n  ~/src  Opus 4.6  ⏵⏵ bypass"
        assert infer_agent_status(tmux) == "idle"

    def test_finished_thinking_sauteed_then_idle(self):
        """✻ Sautéed for Xm Ys + bare prompt = IDLE."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "✻ Sautéed for 2m 28s\n❯ \n  ⏵⏵ on"
        assert infer_agent_status(tmux) == "idle"

    def test_finished_thinking_no_prompt_yet(self):
        """✻ alone without prompt = still finishing up = thinking."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "✻ Sautéed for 2m 28s"
        assert infer_agent_status(tmux) == "thinking"

    # --- FIX 1b: · (middle dot) with active verb = CURRENTLY thinking ---

    def test_active_thinking_middle_dot_scampering(self):
        """· Scampering... with middle dot = CURRENTLY thinking.

        Real live data: '· Scampering… (3m 20s · ↓ 575 tokens)' means agent
        is actively processing right now.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "\u00b7 Scampering\u2026 (3m 20s \u00b7 \u2193 575 tokens)"
        assert infer_agent_status(tmux) == "thinking"

    def test_active_thinking_middle_dot_brewing(self):
        """· Brewing... = CURRENTLY thinking."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "\u00b7 Brewing\u2026"
        assert infer_agent_status(tmux) == "thinking"

    def test_active_thinking_middle_dot_with_prior_output(self):
        """Middle dot active verb after prior output = thinking."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "some prior tool output\n\u00b7 Saut\u00e9ing\u2026 (1m 5s)"
        assert infer_agent_status(tmux) == "thinking"

    # --- FIX 2: ❯ with user text = agent processing input, not idle ---

    def test_prompt_with_user_input_is_thinking(self):
        """❯ followed by user text = agent processing submitted input.

        Real live data: '❯ now close issue 12 and commit the .gitignore change'
        means user typed input and agent is working on it.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "❯ now close issue 12 and commit the .gitignore change\n  ⏵⏵ bypass permissions on"
        assert infer_agent_status(tmux) == "thinking"

    def test_prompt_with_user_input_no_status_bar(self):
        """❯ with user text but no status bar = still thinking."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "❯ fix the auth module and run tests"
        assert infer_agent_status(tmux) == "thinking"

    def test_bare_prompt_with_status_bar_is_idle(self):
        """Bare ❯ with status bar = idle (waiting for next task).

        Real live data: bare '❯ ' with '⏵⏵' = truly idle.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "❯ \n  ⏵⏵ bypass permissions on"
        assert infer_agent_status(tmux) == "idle"

    def test_bare_prompt_no_status_bar_is_idle(self):
        """Bare ❯ without status bar = idle."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "some output\n❯ "
        assert infer_agent_status(tmux) == "idle"

    def test_finished_then_user_typed_input(self):
        """✻ finished indicator + ❯ with user text = thinking (processing new input).

        Real scenario: agent finished one task, user typed next task at prompt.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "✻ Brewed for 6m 11s\n❯ now fix the tests\n  ⏵⏵ bypass on"
        assert infer_agent_status(tmux) == "thinking"

    # --- FIX 3: Status bar "(running)" = running ---

    def test_status_bar_running_indicator(self):
        """Status bar with '(running)' suffix = subagent/background task active.

        Real live data: '· Wire LadybugDB backend for graph-query (running)'
        in status bar means a background task is running.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "❯ \n  ~/src  ⏵⏵ · Wire LadybugDB backend for graph-query (running)"
        assert infer_agent_status(tmux) == "running"

    def test_status_bar_running_with_prompt(self):
        """(running) in status bar even with bare prompt = running."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "some output\n❯ \n  ⏵⏵ Implement auth (running)"
        assert infer_agent_status(tmux) == "running"

    # --- Regression tests for existing behavior that must still work ---

    def test_waiting_input_yes_no_prompt(self):
        reasoner = SessionReasoner(dry_run=True)
        assert infer_agent_status("Do you want to continue? (yes/no)") == "waiting_input"

    def test_waiting_claude_permission_allow_no_prompt(self):
        """Claude Code permission prompt with 'allow' but no bare ❯ prompt = waiting."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = "Some tool output\n  ⏵⏵ allow all"
        assert infer_agent_status(tmux) == "waiting_input"

    def test_waiting_claude_actual_permission_request(self):
        """Real permission request scenario: tool wants to run, asking for approval.

        When Claude Code asks for permission, the Y/n prompt is the last line.
        """
        reasoner = SessionReasoner(dry_run=True)
        tmux = "I need to run a cleanup command.\nAllow this tool call? [Y/n]"
        assert infer_agent_status(tmux) == "waiting_input"

    def test_error_fatal(self):
        reasoner = SessionReasoner(dry_run=True)
        assert infer_agent_status("fatal: not a git repository") == "error"

    def test_completed_workflow(self):
        reasoner = SessionReasoner(dry_run=True)
        assert infer_agent_status("GOAL_STATUS: ACHIEVED") == "completed"

    def test_shell_bare_prompt(self):
        """Bare shell prompt = shell (agent dead), not idle."""
        reasoner = SessionReasoner(dry_run=True)
        assert infer_agent_status("user@host:~/code$") == "shell"

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
        assert infer_agent_status(tmux) == "idle"

    def test_real_scenario_agent_actively_processing(self):
        """Full realistic tmux: agent is mid-thought with streaming indicator."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = """  Let me analyze the codebase structure...

· Scampering\u2026 (2m 15s \u00b7 \u2193 1.2k tokens)"""
        assert infer_agent_status(tmux) == "thinking"

    def test_real_scenario_user_just_submitted_task(self):
        """Full realistic tmux: user typed a command at the prompt."""
        reasoner = SessionReasoner(dry_run=True)
        tmux = """✻ Brewed for 3m 45s

❯ now close issue 12 and commit the .gitignore change
  ⏵⏵ bypass permissions on"""
        assert infer_agent_status(tmux) == "thinking"


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
        from amplihack.fleet._backends import LLMBackend

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

    def test_auto_detect_always_returns_backend(self):
        """auto_detect_backend always returns a backend (litellm is a base dependency)."""
        with patch.dict(os.environ, {}, clear=True):
            backend = auto_detect_backend()
            assert backend is not None


# ---------------------------------------------------------------------------
# Additional coverage: _backends.py (45% -> target 80%+)
# ---------------------------------------------------------------------------


class TestAnthropicBackend:
    """Tests for AnthropicBackend class."""

    def test_init_defaults(self):
        """Test default model and empty api_key."""
        with patch.dict(os.environ, {}, clear=True):
            backend = AnthropicBackend()
            assert backend.model == "claude-opus-4-6"
            assert backend.api_key == ""

    def test_init_with_explicit_api_key(self):
        backend = AnthropicBackend(api_key="sk-test-123")
        assert backend.api_key == "sk-test-123"

    def test_init_reads_env_key(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-env-key"}):
            backend = AnthropicBackend()
            assert backend.api_key == "sk-env-key"

    def test_init_explicit_key_overrides_env(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-env-key"}):
            backend = AnthropicBackend(api_key="sk-explicit")
            assert backend.api_key == "sk-explicit"

    def test_init_custom_model(self):
        backend = AnthropicBackend(model="claude-opus-4-20250514")
        assert backend.model == "claude-opus-4-20250514"

    def test_complete_success(self):
        """Test complete() with mocked anthropic streaming client."""
        backend = AnthropicBackend(api_key="test-key")

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.get_final_text.return_value = "Hello from Claude"

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        import sys
        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            result = backend.complete("system prompt", "user prompt")

        assert result == "Hello from Claude"
        mock_client.messages.stream.assert_called_once_with(
            model=backend.model,
            max_tokens=backend.max_tokens,
            system="system prompt",
            messages=[{"role": "user", "content": "user prompt"}],
        )

    def test_complete_empty_response(self):
        """Test complete() when stream returns empty text."""
        backend = AnthropicBackend(api_key="test-key")

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.get_final_text.return_value = ""

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        import sys
        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            result = backend.complete("sys", "usr")

        assert result == ""


class TestCopilotBackendComplete:
    """Tests for CopilotBackend async completion flow."""

    def test_copilot_default_model(self):
        backend = CopilotBackend()
        assert backend.model == "gpt-4o"

    def test_copilot_custom_model(self):
        backend = CopilotBackend(model="claude-3-5-sonnet")
        assert backend.model == "claude-3-5-sonnet"

    def test_copilot_complete_calls_asyncio_run(self):
        """CopilotBackend.complete() should call asyncio.run with _async_complete."""
        import sys
        mock_asyncio = MagicMock()
        mock_asyncio.run.return_value = "test response"
        backend = CopilotBackend()
        with patch.dict(sys.modules, {"asyncio": mock_asyncio}):
            # The import asyncio happens inside complete(), so patching sys.modules works
            result = backend.complete("system", "user")
        assert result == "test response"


class TestLiteLLMBackendComplete:
    """Tests for LiteLLMBackend.complete() with mocked litellm."""

    def test_litellm_default_model(self):
        backend = LiteLLMBackend()
        assert backend.model == "gpt-4o"

    def test_litellm_custom_model(self):
        backend = LiteLLMBackend(model="ollama/llama3")
        assert backend.model == "ollama/llama3"

    def test_complete_success(self):
        """LiteLLMBackend.complete() returns text from response."""
        backend = LiteLLMBackend(model="gpt-4o")

        mock_msg = MagicMock()
        mock_msg.content = "Hello from LiteLLM"
        mock_choice = MagicMock()
        mock_choice.message = mock_msg
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        import sys
        with patch.dict(sys.modules, {"litellm": mock_litellm_module}):
            result = backend.complete("system prompt", "user prompt")

        assert result == "Hello from LiteLLM"
        mock_litellm_module.completion.assert_called_once_with(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "user prompt"},
            ],
            max_tokens=backend.max_tokens,
        )

    def test_complete_empty_choices(self):
        """LiteLLMBackend returns empty string when choices are empty."""
        backend = LiteLLMBackend()
        mock_response = MagicMock()
        mock_response.choices = []

        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        import sys
        with patch.dict(sys.modules, {"litellm": mock_litellm_module}):
            result = backend.complete("sys", "usr")

        assert result == ""

    def test_complete_none_message(self):
        """LiteLLMBackend returns empty string when message is None."""
        backend = LiteLLMBackend()
        mock_choice = MagicMock()
        mock_choice.message = None
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        import sys
        with patch.dict(sys.modules, {"litellm": mock_litellm_module}):
            result = backend.complete("sys", "usr")

        assert result == ""

    def test_complete_none_content(self):
        """LiteLLMBackend returns empty string when content is None."""
        backend = LiteLLMBackend()
        mock_msg = MagicMock()
        mock_msg.content = None
        mock_choice = MagicMock()
        mock_choice.message = mock_msg
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        import sys
        with patch.dict(sys.modules, {"litellm": mock_litellm_module}):
            result = backend.complete("sys", "usr")

        assert result == ""


class TestAutoDetectBackendEdgeCases:
    """Edge cases for auto_detect_backend."""

    def test_no_env_returns_copilot(self):
        """Without ANTHROPIC_API_KEY, returns CopilotBackend."""
        with patch.dict(os.environ, {}, clear=True):
            backend = auto_detect_backend()
            assert isinstance(backend, CopilotBackend)

    def test_empty_anthropic_key_returns_copilot(self):
        """Empty ANTHROPIC_API_KEY is falsy, returns CopilotBackend."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            backend = auto_detect_backend()
            assert isinstance(backend, CopilotBackend)


# ---------------------------------------------------------------------------
# Additional coverage: fleet_session_reasoner.py (65% -> target 80%+)
# ---------------------------------------------------------------------------


class TestSessionReasonerGatherContext:
    """Tests for _gather_context method."""

    def test_gather_context_success(self):
        """Successful subprocess returns populated context."""
        mock_output = (
            "===TMUX===\n"
            "Some terminal output here\n"
            "===CWD===\n"
            "/home/user/project\n"
            "===GIT===\n"
            "BRANCH:feat/auth\n"
            "REMOTE:https://github.com/org/repo\n"
            "MODIFIED:file1.py,file2.py,\n"
            "===TRANSCRIPT===\n"
            "Working on auth module\n"
            "PR_CREATED:https://github.com/org/repo/pull/42\n"
            "===END===\n"
        )
        mock = MockBackend(response='{"action":"wait","reasoning":"ok","confidence":0.8}')
        reasoner = SessionReasoner(backend=mock, dry_run=True)

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            ctx = reasoner._gather_context("vm-1", "sess-1", "Fix auth", "Quality first")

        assert ctx.vm_name == "vm-1"
        assert ctx.session_name == "sess-1"
        assert ctx.task_prompt == "Fix auth"
        assert ctx.project_priorities == "Quality first"
        assert "terminal output" in ctx.tmux_capture
        assert ctx.working_directory == "/home/user/project"
        assert ctx.git_branch == "feat/auth"
        assert ctx.repo_url == "https://github.com/org/repo"
        assert "file1.py" in ctx.files_modified
        assert "file2.py" in ctx.files_modified
        assert ctx.pr_url == "https://github.com/org/repo/pull/42"
        assert "auth module" in ctx.transcript_summary

    def test_gather_context_no_session(self):
        """When tmux returns NO_SESSION, status is no_session."""
        mock_output = (
            "===TMUX===\n"
            "NO_SESSION\n"
            "===CWD===\n"
            "\n"
            "===GIT===\n"
            "\n"
            "===TRANSCRIPT===\n"
            "\n"
            "===END===\n"
        )
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=True)

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            ctx = reasoner._gather_context("vm-1", "sess-1", "", "")

        assert ctx.agent_status == "no_session"

    def test_gather_context_subprocess_failure(self):
        """Non-zero return code leaves context with default status."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=True)

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            ctx = reasoner._gather_context("vm-1", "sess-1", "", "")

        assert ctx.agent_status == ""

    def test_gather_context_timeout(self):
        """Timeout results in unreachable status."""
        import subprocess
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=True)

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test"], timeout=60)
            ctx = reasoner._gather_context("vm-1", "sess-1", "", "")

        assert ctx.agent_status == "unreachable"

    def test_gather_context_file_not_found(self):
        """FileNotFoundError results in unreachable status."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=True)

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("azlin not found")
            ctx = reasoner._gather_context("vm-1", "sess-1", "", "")

        assert ctx.agent_status == "unreachable"


class TestParseContextOutput:
    """Tests for _parse_context_output method."""

    def test_parse_empty_output(self):
        """Empty output should not crash."""
        reasoner = SessionReasoner(dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")
        parse_context_output("", ctx)
        assert ctx.tmux_capture == ""

    def test_parse_git_section_with_files(self):
        """Git section should populate branch, remote, and modified files."""
        reasoner = SessionReasoner(dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")
        output = (
            "===TMUX===\nsome output\n"
            "===CWD===\n/home/user\n"
            "===GIT===\n"
            "BRANCH:main\n"
            "REMOTE:https://github.com/org/repo\n"
            "MODIFIED:a.py,b.py,\n"
            "===TRANSCRIPT===\n\n"
            "===END===\n"
        )
        parse_context_output(output, ctx)
        assert ctx.git_branch == "main"
        assert ctx.repo_url == "https://github.com/org/repo"
        assert ctx.files_modified == ["a.py", "b.py"]

    def test_parse_no_git_info(self):
        """Git section without BRANCH/REMOTE lines should be fine."""
        reasoner = SessionReasoner(dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")
        output = "===TMUX===\noutput\n===CWD===\n/tmp\n===GIT===\n\n===END===\n"
        parse_context_output(output, ctx)
        assert ctx.git_branch == ""
        assert ctx.repo_url == ""


class TestExecuteDecision:
    """Tests for _execute_decision method."""

    def test_execute_send_input_success(self):
        """send_input with high confidence calls subprocess."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=False)

        decision = SessionDecision(
            session_name="sess-1",
            vm_name="vm-1",
            action="send_input",
            input_text="yes",
            confidence=0.9,
        )

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            reasoner._execute_decision(decision)

        assert mock_run.called

    def test_execute_send_input_low_confidence_suppressed(self):
        """send_input with confidence below threshold is suppressed."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=False)

        decision = SessionDecision(
            session_name="sess-1",
            vm_name="vm-1",
            action="send_input",
            input_text="yes",
            confidence=0.3,  # Below MIN_CONFIDENCE_SEND (0.6)
        )

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            reasoner._execute_decision(decision)

        mock_run.assert_not_called()

    def test_execute_restart_low_confidence_suppressed(self):
        """restart with confidence below threshold is suppressed."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=False)

        decision = SessionDecision(
            session_name="sess-1",
            vm_name="vm-1",
            action="restart",
            confidence=0.5,  # Below MIN_CONFIDENCE_RESTART (0.8)
        )

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            reasoner._execute_decision(decision)

        mock_run.assert_not_called()

    def test_execute_restart_high_confidence(self):
        """restart with high confidence calls subprocess."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=False)

        decision = SessionDecision(
            session_name="sess-1",
            vm_name="vm-1",
            action="restart",
            confidence=0.9,
        )

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            reasoner._execute_decision(decision)

        assert mock_run.called

    def test_execute_send_input_dangerous_blocked(self):
        """Dangerous input text is blocked — new escalate decision appended."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=False)

        decision = SessionDecision(
            session_name="sess-1",
            vm_name="vm-1",
            action="send_input",
            input_text="rm -rf /",
            confidence=0.9,
        )

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            reasoner._execute_decision(decision)

        mock_run.assert_not_called()
        # Original decision is NOT mutated (fix #9 from quality audit)
        assert decision.action == "send_input"
        # A new escalate decision is appended to the decisions list
        assert len(reasoner._decisions) == 1
        assert reasoner._decisions[0].action == "escalate"
        assert "BLOCKED" in reasoner._decisions[0].reasoning

    def test_execute_send_input_multiline(self):
        """Multi-line input sends each line separately."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=False)

        decision = SessionDecision(
            session_name="sess-1",
            vm_name="vm-1",
            action="send_input",
            input_text="line1\nline2\nline3",
            confidence=0.9,
        )

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            reasoner._execute_decision(decision)

        assert mock_run.call_count == 3

    def test_execute_send_input_timeout(self):
        """send_input timeout should log warning but not crash."""
        import subprocess
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=False)

        decision = SessionDecision(
            session_name="sess-1",
            vm_name="vm-1",
            action="send_input",
            input_text="hello",
            confidence=0.9,
        )

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test"], timeout=30)
            reasoner._execute_decision(decision)
            # Should not raise

    def test_execute_restart_timeout(self):
        """restart timeout should log warning but not crash."""
        import subprocess
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=False)

        decision = SessionDecision(
            session_name="sess-1",
            vm_name="vm-1",
            action="restart",
            confidence=0.9,
        )

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test"], timeout=30)
            reasoner._execute_decision(decision)
            # Should not raise

    def test_execute_wait_noop(self):
        """wait action does nothing."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=False)

        decision = SessionDecision(
            session_name="sess-1",
            vm_name="vm-1",
            action="wait",
            confidence=0.9,
        )

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            reasoner._execute_decision(decision)

        mock_run.assert_not_called()

    def test_execute_escalate_noop(self):
        """escalate action does nothing (no subprocess call)."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=False)

        decision = SessionDecision(
            session_name="sess-1",
            vm_name="vm-1",
            action="escalate",
            confidence=0.5,
        )

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            reasoner._execute_decision(decision)

        mock_run.assert_not_called()

    def test_execute_mark_complete_noop(self):
        """mark_complete action does nothing (no subprocess call)."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=False)

        decision = SessionDecision(
            session_name="sess-1",
            vm_name="vm-1",
            action="mark_complete",
            confidence=0.9,
        )

        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            reasoner._execute_decision(decision)

        mock_run.assert_not_called()

    def test_execute_invalid_vm_name_raises(self):
        """Invalid VM name in decision should raise ValueError."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=False)

        decision = SessionDecision(
            session_name="sess-1",
            vm_name="bad name with spaces!",
            action="wait",
            confidence=0.9,
        )

        with pytest.raises(ValueError, match="Invalid VM name"):
            reasoner._execute_decision(decision)

    def test_execute_invalid_session_name_raises(self):
        """Invalid session name in decision should raise ValueError."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=False)

        decision = SessionDecision(
            session_name="bad session!@#",
            vm_name="vm-1",
            action="wait",
            confidence=0.9,
        )

        with pytest.raises(ValueError, match="Invalid session name"):
            reasoner._execute_decision(decision)


class TestSessionReasonerReasonAboutAll:
    """Tests for reason_about_all method."""

    def test_reason_about_all_multiple_sessions(self):
        """reason_about_all should process all sessions."""
        mock = MockBackend(response=json.dumps({
            "action": "wait",
            "reasoning": "ok",
            "confidence": 0.8,
        }))
        reasoner = SessionReasoner(backend=mock, dry_run=True)

        sessions = [
            {"vm_name": "vm-1", "session_name": "sess-1", "task_prompt": "task1"},
            {"vm_name": "vm-1", "session_name": "sess-2", "task_prompt": "task2"},
        ]

        with patch.object(reasoner, "_gather_context") as mock_gather:
            mock_gather.return_value = SessionContext(
                vm_name="vm-1",
                session_name="sess-1",
                agent_status="running",
            )
            decisions = reasoner.reason_about_all(sessions, project_priorities="Quality")

        assert len(decisions) == 2

    def test_reason_about_all_empty(self):
        """reason_about_all with empty list returns empty list."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=True)
        decisions = reasoner.reason_about_all([], project_priorities="")
        assert decisions == []


class TestSessionReasonerReasonInvalidActions:
    """Test _reason handles invalid/malformed LLM responses."""

    def test_invalid_action_defaults_to_wait(self):
        """Invalid action value should default to 'wait'."""
        mock = MockBackend(response=json.dumps({
            "action": "destroy_everything",
            "reasoning": "bad idea",
            "confidence": 0.9,
        }))
        reasoner = SessionReasoner(backend=mock, dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")
        decision = reasoner._reason(ctx)
        assert decision.action == "wait"

    def test_non_string_action_defaults_to_wait(self):
        """Non-string action should default to 'wait'."""
        mock = MockBackend(response=json.dumps({
            "action": 123,
            "reasoning": "numeric action",
            "confidence": 0.5,
        }))
        reasoner = SessionReasoner(backend=mock, dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")
        decision = reasoner._reason(ctx)
        assert decision.action == "wait"

    def test_invalid_confidence_clamped(self):
        """Confidence values outside 0-1 should be clamped."""
        mock = MockBackend(response=json.dumps({
            "action": "wait",
            "reasoning": "ok",
            "confidence": 5.0,  # Way above 1.0
        }))
        reasoner = SessionReasoner(backend=mock, dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")
        decision = reasoner._reason(ctx)
        assert decision.confidence == 1.0

    def test_negative_confidence_clamped(self):
        """Negative confidence should be clamped to 0.0."""
        mock = MockBackend(response=json.dumps({
            "action": "wait",
            "reasoning": "ok",
            "confidence": -0.5,
        }))
        reasoner = SessionReasoner(backend=mock, dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")
        decision = reasoner._reason(ctx)
        assert decision.confidence == 0.0

    def test_non_numeric_confidence_defaults(self):
        """Non-numeric confidence should default to 0.5."""
        mock = MockBackend(response=json.dumps({
            "action": "wait",
            "reasoning": "ok",
            "confidence": "high",
        }))
        reasoner = SessionReasoner(backend=mock, dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")
        decision = reasoner._reason(ctx)
        assert decision.confidence == 0.5

    def test_non_string_input_text_defaults_empty(self):
        """Non-string input_text should default to empty string."""
        mock = MockBackend(response=json.dumps({
            "action": "send_input",
            "input_text": 42,
            "reasoning": "ok",
            "confidence": 0.8,
        }))
        reasoner = SessionReasoner(backend=mock, dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")
        decision = reasoner._reason(ctx)
        assert decision.input_text == ""

    def test_non_string_reasoning_defaults_empty(self):
        """Non-string reasoning should default to empty string."""
        mock = MockBackend(response=json.dumps({
            "action": "wait",
            "reasoning": ["list", "not", "string"],
            "confidence": 0.8,
        }))
        reasoner = SessionReasoner(backend=mock, dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")
        decision = reasoner._reason(ctx)
        assert decision.reasoning == ""

    def test_not_implemented_backend(self):
        """NotImplementedError from backend should return escalate."""
        class NotImplBackend:
            def complete(self, system_prompt, user_prompt):
                raise NotImplementedError("not implemented")

        reasoner = SessionReasoner(backend=NotImplBackend(), dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")
        decision = reasoner._reason(ctx)
        assert decision.action == "escalate"
        assert "not implemented" in decision.reasoning.lower()

    def test_public_reason_method(self):
        """Public reason() method delegates to _reason()."""
        mock = MockBackend(response=json.dumps({
            "action": "wait",
            "reasoning": "all good",
            "confidence": 0.9,
        }))
        reasoner = SessionReasoner(backend=mock, dry_run=True)
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1")
        decision = reasoner.reason(ctx)
        assert decision.action == "wait"

    def test_public_execute_decision_method(self):
        """Public execute_decision() delegates to _execute_decision()."""
        mock = MockBackend()
        reasoner = SessionReasoner(backend=mock, dry_run=False)
        decision = SessionDecision(
            session_name="sess-1",
            vm_name="vm-1",
            action="wait",
            confidence=0.9,
        )
        with patch("amplihack.fleet.fleet_session_reasoner.subprocess.run") as mock_run:
            reasoner.execute_decision(decision)
        # wait does nothing, so no subprocess call
        mock_run.assert_not_called()


class TestSessionContextPromptContext:
    """Additional tests for SessionContext.to_prompt_context."""

    def test_prompt_context_with_pr_url(self):
        ctx = SessionContext(
            vm_name="vm-1",
            session_name="sess-1",
            pr_url="https://github.com/org/repo/pull/42",
        )
        prompt = ctx.to_prompt_context()
        assert "PR: https://github.com/org/repo/pull/42" in prompt

    def test_prompt_context_with_files_modified(self):
        ctx = SessionContext(
            vm_name="vm-1",
            session_name="sess-1",
            files_modified=["a.py", "b.py"],
        )
        prompt = ctx.to_prompt_context()
        assert "a.py" in prompt
        assert "b.py" in prompt

    def test_prompt_context_empty_tmux(self):
        ctx = SessionContext(vm_name="vm-1", session_name="sess-1", tmux_capture="")
        prompt = ctx.to_prompt_context()
        assert "(empty)" in prompt


class TestLoadStrategyDictionary:
    """Tests for _load_strategy_dictionary."""

    def test_load_when_file_exists(self):
        from amplihack.fleet._system_prompt import _load_strategy_dictionary
        # This just tests the function runs without error
        result = _load_strategy_dictionary()
        assert isinstance(result, str)
