"""Per-session reasoning loop — the admiral's brain for each agent session.

For each session, the admiral:
1. PERCEIVE: Capture tmux pane + read JSONL transcript
2. REASON: Use Anthropic SDK to decide what action to take
3. ACT: Inject keystrokes via tmux send-keys (or show in dry-run)
4. LEARN: Record the decision and its outcome

The key insight: the admiral doesn't just OBSERVE sessions — it DRIVES them
by typing into the TUI when agents need input, get stuck, or need redirection.

Public API:
    SessionReasoner: Per-session reasoning engine
    SessionContext: Gathered context for a single session
    SessionDecision: What the admiral decided to do
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol

from amplihack.fleet._validation import (
    DANGEROUS_PATTERNS,
    is_dangerous_input,
    validate_session_name,
    validate_vm_name,
)

__all__ = [
    "SessionReasoner",
    "SessionContext",
    "SessionDecision",
    "LLMBackend",
    "AnthropicBackend",
    "CopilotBackend",
    "LiteLLMBackend",
    "auto_detect_backend",
    "infer_agent_status",
]

# Re-export for backward compatibility
_is_dangerous_input = is_dangerous_input

# --- Safety: confidence thresholds (H4) ---
MIN_CONFIDENCE_SEND = 0.6
MIN_CONFIDENCE_RESTART = 0.8


class LLMBackend(Protocol):
    """Protocol for LLM backends."""

    def complete(self, system_prompt: str, user_prompt: str) -> str: ...


class AnthropicBackend:
    """Anthropic SDK backend."""

    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str = ""):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        block = response.content[0]
        return getattr(block, "text", "")


class CopilotBackend:
    """GitHub Copilot SDK backend.

    Requires: pip install copilot-sdk
    Requires: GitHub Copilot subscription + gh auth login
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        import asyncio

        return asyncio.run(self._async_complete(system_prompt, user_prompt))

    async def _async_complete(self, system_prompt: str, user_prompt: str) -> str:
        import asyncio

        from copilot import CopilotClient

        client = CopilotClient()
        await client.start()

        try:
            session = await client.create_session({"model": self.model})
            response_parts: list[str] = []
            done = asyncio.Event()

            def on_event(event):
                if event.type.value == "assistant.message":
                    response_parts.append(event.data.content)
                elif event.type.value == "session.idle":
                    done.set()

            session.on(on_event)
            await session.send({"prompt": f"{system_prompt}\n\n{user_prompt}"})

            try:
                await asyncio.wait_for(done.wait(), timeout=60)
            except TimeoutError:
                pass

            await session.destroy()
            return "".join(response_parts)
        finally:
            await client.stop()


class LiteLLMBackend:
    """LiteLLM backend -- supports 100+ LLM providers.

    Requires: pip install litellm
    Works with: OpenAI, Anthropic, Azure, Copilot, Ollama, etc.
    Set model via constructor: "gpt-4o", "claude-sonnet-4-20250514", "ollama/llama3", etc.
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        import litellm

        response = litellm.completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=500,
        )
        choices = getattr(response, "choices", [])
        if choices:
            msg = getattr(choices[0], "message", None)
            content = getattr(msg, "content", None) if msg else None
            return str(content) if content else ""
        return ""


def auto_detect_backend() -> LLMBackend:
    """Auto-detect the best available LLM backend.

    Priority:
    1. Anthropic (if ANTHROPIC_API_KEY set)
    2. LiteLLM (if installed -- supports many providers)
    3. Copilot SDK (if installed + gh auth)

    Raises RuntimeError if no backend available.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicBackend()

    try:
        import litellm  # noqa: F401

        return LiteLLMBackend()
    except ImportError:
        pass

    try:
        from copilot import CopilotClient  # noqa: F401

        return CopilotBackend()
    except ImportError:
        pass

    raise RuntimeError(
        "No LLM backend available. Set ANTHROPIC_API_KEY, "
        "or install litellm (pip install litellm), "
        "or install copilot-sdk (pip install copilot-sdk)"
    )


@dataclass
class SessionContext:
    """Everything the admiral knows about a session at reasoning time."""

    vm_name: str
    session_name: str
    tmux_capture: str = ""  # Raw tmux pane content
    transcript_summary: str = ""  # From JSONL log analysis
    working_directory: str = ""
    git_branch: str = ""
    repo_url: str = ""
    agent_status: str = ""  # running, idle, stuck, waiting_input, error, completed
    files_modified: list[str] = field(default_factory=list)
    pr_url: str = ""
    task_prompt: str = ""  # Original task assigned to this session
    project_priorities: str = ""  # Fleet-level priorities

    def __post_init__(self):
        validate_vm_name(self.vm_name)

    def to_prompt_context(self) -> str:
        """Format context for the reasoning LLM call."""
        parts = []
        parts.append(f"VM: {self.vm_name}, Session: {self.session_name}")
        parts.append(f"Status: {self.agent_status}")

        if self.repo_url:
            parts.append(f"Repo: {self.repo_url}")
        if self.git_branch:
            parts.append(f"Branch: {self.git_branch}")
        if self.task_prompt:
            parts.append(f"Original task: {self.task_prompt}")
        if self.pr_url:
            parts.append(f"PR: {self.pr_url}")
        if self.files_modified:
            parts.append(f"Files modified: {', '.join(self.files_modified[:10])}")
        if self.transcript_summary:
            parts.append(f"\nTranscript summary:\n{self.transcript_summary}")

        parts.append("\nCurrent terminal output (last lines):")
        parts.append(self.tmux_capture[-2000:] if self.tmux_capture else "(empty)")

        if self.project_priorities:
            parts.append(f"\nProject priorities: {self.project_priorities}")

        return "\n".join(parts)


@dataclass
class SessionDecision:
    """What the admiral decided to do for a session."""

    session_name: str
    vm_name: str
    action: str  # "send_input", "wait", "escalate", "mark_complete", "restart"
    input_text: str = ""  # Text to type into the session (if action=send_input)
    reasoning: str = ""  # Why the admiral made this decision
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def summary(self) -> str:
        """Human-readable decision summary."""
        lines = [
            f"  Session: {self.vm_name}/{self.session_name}",
            f"  Action: {self.action}",
            f"  Confidence: {self.confidence:.0%}",
            f"  Reasoning: {self.reasoning}",
        ]
        if self.input_text:
            # Show the input but truncate for display
            display = self.input_text.replace("\n", "\\n")[:100]
            lines.append(f'  Input: "{display}"')
        return "\n".join(lines)


def _load_strategy_dictionary() -> str:
    """Load the strategy dictionary if available."""
    strategy_path = Path(__file__).parent / "STRATEGY_DICTIONARY.md"
    if strategy_path.exists():
        content = strategy_path.read_text()
        # Extract just the strategy index and decision quick-reference (not full details)
        lines = content.split("\n")
        index_section = []
        in_index = False
        in_quick_ref = False
        for line in lines:
            if "STRATEGY INDEX" in line:
                in_index = True
            elif "## STRATEGIES" in line:
                in_index = False
            elif "DECISION QUICK-REFERENCE" in line:
                in_quick_ref = True

            if in_index or in_quick_ref:
                index_section.append(line)

        if index_section:
            return "\n".join(index_section)
    return ""


SYSTEM_PROMPT_BASE = """You are a Fleet Admiral managing coding agent sessions across multiple VMs.

For each session, you analyze the current terminal output and transcript to decide what to do.

Your options:
1. SEND_INPUT: Type text into the session to answer a question, provide guidance, or continue work
2. WAIT: The agent is working fine or actively thinking — no intervention needed
3. ESCALATE: The situation needs human attention (complex decision, credentials needed, etc.)
4. MARK_COMPLETE: The agent has finished its task (PR created, tests passing)
5. RESTART: The agent is genuinely stuck or errored after multiple attempts

Respond in this exact JSON format:
{
  "action": "send_input|wait|escalate|mark_complete|restart",
  "input_text": "text to type (only for send_input)",
  "reasoning": "why you chose this action",
  "confidence": 0.0 to 1.0
}

CRITICAL — Thinking Detection:
- If status is "thinking", the agent is actively processing (LLM call or tool running). ALWAYS choose WAIT.
- Claude Code shows "●" for active tool calls, "✻" for processing time, streaming "⎿" for output.
- Copilot shows "Thinking..." or "Running:" for active work.
- DO NOT interrupt a thinking agent. DO NOT mark a thinking agent as stuck.
- A thinking agent may appear to have no new output for minutes — this is normal for complex reasoning.

Amplihack Strategy Awareness:
- Verify agents follow DEFAULT_WORKFLOW (22 steps). If steps skipped, remind them.
- Outside-in testing is MANDATORY before marking complete. Check PR for test results.
- Use philosophy-guardian to enforce ruthless simplicity.
- For complex tasks, agents should use architect-first design, then builder.
- For important PRs, invoke multi-agent review (reviewer + security + philosophy).
- Lock mode (/amplihack:lock) protects deep work sessions from interruption.
- Quality-audit-workflow finds issues CI cannot.
- Pre-commit-diagnostic auto-fixes formatting/linting failures.
- CI-diagnostic-workflow iterates fixes until PR is mergeable.
- When confidence < 0.6, default to WAIT or ESCALATE, not SEND_INPUT.

Guidelines:
- If the agent is asking a question, answer it based on the task and project priorities
- If the agent is waiting for permission (Y/n prompts), approve unless it's destructive
- If the agent produced a PR and tests pass, mark as complete
- If you need more context or the decision has high stakes, escalate to the human
- NEVER approve destructive operations (force push, drop database, delete production data)
- Prefer the simplest answer that keeps the agent moving forward
- For coding questions, prefer quality over speed"""


# Build full system prompt with strategy dictionary at module load time
_strategy_ref = _load_strategy_dictionary()
SYSTEM_PROMPT = SYSTEM_PROMPT_BASE + ("\n\n" + _strategy_ref if _strategy_ref else "")


def infer_agent_status(tmux_text: str) -> str:
    """Infer agent status from tmux/terminal output.

    Critically distinguishes between:
    - THINKING: Agent is actively processing (LLM call in flight, tool running)
    - WAITING_INPUT: Agent needs user input to proceed
    - IDLE: No agent running (bare shell prompt), or agent at prompt with no input
    - RUNNING: Agent actively producing output (or status bar says "(running)")
    - ERROR/COMPLETED: Terminal states
    """
    last_lines = tmux_text.strip().split("\n")[-10:]
    combined = "\n".join(last_lines)
    combined_lower = combined.lower()
    last_line = last_lines[-1].strip() if last_lines else ""
    last_line_lower = last_line.lower()

    # Helper: find the prompt line and check if user typed input
    prompt_line_text = ""
    has_prompt = False
    for line in reversed(last_lines):
        stripped = line.strip()
        if stripped.startswith("❯"):
            has_prompt = True
            prompt_line_text = stripped[len("❯") :].strip()
            break

    # STATUS BAR "(running)" detection (high priority)
    for line in last_lines:
        if "(running)" in line and "⏵⏵" in line:
            return "running"

    # THINKING/WORKING detection (highest priority)
    for line in last_lines:
        stripped = line.strip()
        if stripped.startswith("\u00b7 ") or stripped.startswith("· "):
            return "thinking"

    # Check last non-empty line for tool/streaming indicators
    for line in reversed(last_lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("●") and not stripped.startswith("● Bash("):
            return "thinking"
        if stripped.startswith("⎿"):
            return "thinking"
        break

    # "✻" = JUST FINISHED thinking
    has_finished_indicator = False
    for line in last_lines:
        stripped = line.strip()
        if "✻" in stripped:
            has_finished_indicator = True
            break

    if has_finished_indicator and has_prompt:
        if prompt_line_text:
            return "thinking"
        return "idle"
    if has_finished_indicator and not has_prompt:
        return "thinking"

    # Copilot: explicit thinking indicators
    if any(p in combined_lower for p in ["thinking...", "running:", "loading"]):
        return "thinking"

    # Claude Code actively streaming (tool call with output)
    if (
        "● Bash(" in combined
        or "● Read(" in combined
        or "● Write(" in combined
        or "● Edit(" in combined
    ):
        if "⏵⏵" in last_line:
            return "waiting_input"
        return "thinking"

    # PROMPT with user input = agent processing
    if has_prompt and prompt_line_text:
        return "thinking"

    # IDLE detection for bare prompts
    if has_prompt and not prompt_line_text:
        return "idle"
    if last_line_lower.endswith("$ ") or last_line_lower.endswith("$"):
        return "idle"

    # WAITING_INPUT detection
    if any(p in combined_lower for p in ["y/n]", "yes/no", "[y/n", "(yes/no)"]):
        return "waiting_input"
    if "⏵⏵" in combined and ("bypass" in combined_lower or "allow" in combined_lower):
        return "waiting_input"
    if last_line_lower.endswith("?"):
        return "waiting_input"

    # ERROR detection
    if any(p in combined_lower for p in ["error:", "traceback", "fatal:", "panic:"]):
        return "error"

    # COMPLETED detection
    if any(p in combined for p in ["GOAL_STATUS: ACHIEVED", "Workflow Complete"]):
        return "completed"
    if any(p in combined for p in ["gh pr create", "PR #", "pull request"]):
        if any(p in combined_lower for p in ["created", "opened", "merged"]):
            return "completed"

    # Default: assume running if substantial output
    if len(combined.strip()) > 50:
        return "running"

    return "unknown"


@dataclass
class SessionReasoner:
    """Per-session reasoning engine — SDK-agnostic.

    Uses an LLMBackend protocol that supports both Claude and Copilot SDKs.
    Gathers context for a session, calls the LLM to decide what to do,
    then either acts (live mode) or shows the decision (dry-run mode).
    """

    azlin_path: str = "/home/azureuser/src/azlin/.venv/bin/azlin"
    backend: LLMBackend | None = None
    dry_run: bool = False
    _decisions: list[SessionDecision] = field(default_factory=list)

    def __post_init__(self):
        if self.backend is None:
            try:
                self.backend = auto_detect_backend()
            except RuntimeError:
                # Will fail at reasoning time with a clear error
                self.backend = AnthropicBackend()

    def reason_about_session(
        self,
        vm_name: str,
        session_name: str,
        task_prompt: str = "",
        project_priorities: str = "",
    ) -> SessionDecision:
        """Full reasoning loop for a single session.

        1. PERCEIVE: Gather context
        2. REASON: Call LLM to decide
        3. ACT: Execute decision (or show in dry-run)
        4. LEARN: Record decision

        Returns the decision made.
        """
        # 1. PERCEIVE
        context = self._gather_context(vm_name, session_name, task_prompt, project_priorities)

        # 2. REASON — fast-path: skip LLM call if agent is actively thinking
        if context.agent_status == "thinking":
            decision = SessionDecision(
                session_name=session_name,
                vm_name=vm_name,
                action="wait",
                reasoning="Agent is actively thinking/processing — do not interrupt",
                confidence=1.0,
            )
        else:
            decision = self._reason(context)

        # 3. ACT
        if self.dry_run:
            self._show_decision(decision, context)
        else:
            self._execute_decision(decision)

        # 4. LEARN
        self._decisions.append(decision)

        return decision

    def reason_about_all(
        self,
        sessions: list[dict],
        project_priorities: str = "",
    ) -> list[SessionDecision]:
        """Reason about multiple sessions.

        Args:
            sessions: List of {"vm_name": str, "session_name": str, "task_prompt": str}
            project_priorities: Fleet-level priorities
        """
        decisions = []
        for sess in sessions:
            decision = self.reason_about_session(
                vm_name=sess["vm_name"],
                session_name=sess["session_name"],
                task_prompt=sess.get("task_prompt", ""),
                project_priorities=project_priorities,
            )
            decisions.append(decision)
        return decisions

    def _gather_context(
        self,
        vm_name: str,
        session_name: str,
        task_prompt: str,
        project_priorities: str,
    ) -> SessionContext:
        """PERCEIVE: Gather all context for a session in minimal SSH calls."""
        context = SessionContext(
            vm_name=vm_name,
            session_name=session_name,
            task_prompt=task_prompt,
            project_priorities=project_priorities,
        )

        # Single compound SSH command for everything
        gather_cmd = f"""
# Capture tmux pane
echo '===TMUX==='
tmux capture-pane -t {shlex.quote(session_name)} -p -S -40 2>/dev/null || echo 'NO_SESSION'

# Get session's working directory and git info
echo '===CWD==='
CWD=$(tmux display-message -t {shlex.quote(session_name)} -p '#{{pane_current_path}}' 2>/dev/null)
echo "$CWD"

echo '===GIT==='
if [ -n "$CWD" ] && [ -d "$CWD/.git" ]; then
    cd "$CWD"
    echo "BRANCH:$(git branch --show-current 2>/dev/null)"
    echo "REMOTE:$(git remote get-url origin 2>/dev/null)"
    echo "MODIFIED:$(git diff --name-only HEAD 2>/dev/null | head -10 | tr '\\n' ',')"
fi

# Check for JSONL transcript (last few meaningful entries)
echo '===TRANSCRIPT==='
if [ -n "$CWD" ]; then
    PROJECT_KEY=$(echo "$CWD" | sed 's|/|-|g')
    JSONL=$(ls -t ~/.claude/projects/$PROJECT_KEY/*.jsonl 2>/dev/null | head -1)
    if [ -n "$JSONL" ]; then
        # Get last few assistant messages for context
        tail -100 "$JSONL" 2>/dev/null | python3 -c "
import sys, json
msgs = []
for line in sys.stdin:
    try:
        obj = json.loads(line)
        if obj.get('type') == 'assistant':
            msg = obj.get('message',{{}})
            content = msg.get('content','')
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get('type') == 'text':
                        text = c.get('text','')[:200]
                        if text: msgs.append(text)
            elif isinstance(content, str) and content:
                msgs.append(content[:200])
        elif obj.get('type') == 'pr-link':
            msgs.append('PR_CREATED:' + obj.get('url',''))
    except Exception: pass
# Print last 5 messages
for m in msgs[-5:]:
    print(m)
" 2>/dev/null
    fi
fi
echo '===END==='
"""

        try:
            result = subprocess.run(
                [self.azlin_path, "connect", vm_name, "--no-tmux", "--", gather_cmd],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                self._parse_context_output(result.stdout, context)

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            context.agent_status = "unreachable"

        return context

    def _parse_context_output(self, output: str, context: SessionContext) -> None:
        """Parse the compound SSH output into SessionContext."""
        sections = output.split("===")

        for i, section in enumerate(sections):
            label = section.strip()

            if label == "TMUX" and i + 1 < len(sections):
                tmux_text = sections[i + 1].strip()
                if tmux_text == "NO_SESSION":
                    context.agent_status = "no_session"
                else:
                    context.tmux_capture = tmux_text
                    context.agent_status = self._infer_status(tmux_text)

            elif label == "CWD" and i + 1 < len(sections):
                context.working_directory = sections[i + 1].strip()

            elif label == "GIT" and i + 1 < len(sections):
                for line in sections[i + 1].strip().split("\n"):
                    if line.startswith("BRANCH:"):
                        context.git_branch = line[7:]
                    elif line.startswith("REMOTE:"):
                        context.repo_url = line[7:]
                    elif line.startswith("MODIFIED:"):
                        files = [f.strip() for f in line[9:].split(",") if f.strip()]
                        context.files_modified = files

            elif label == "TRANSCRIPT" and i + 1 < len(sections):
                transcript = sections[i + 1].strip()
                if transcript:
                    context.transcript_summary = transcript
                    # Check for PR link in transcript
                    for line in transcript.split("\n"):
                        if line.startswith("PR_CREATED:"):
                            context.pr_url = line[11:]

    def _infer_status(self, tmux_text: str) -> str:
        """Infer agent status from tmux capture. Delegates to module-level function."""
        return infer_agent_status(tmux_text)

    def reason(self, context: SessionContext) -> SessionDecision:
        """Public entry point for LLM-based reasoning about a session context.

        Delegates to the internal _reason implementation.
        """
        return self._reason(context)

    def _reason(self, context: SessionContext) -> SessionDecision:
        """REASON: Call LLM backend to decide what to do.

        Uses the LLMBackend protocol — works with Claude SDK, Copilot SDK,
        or any other LLM that implements the complete() method.
        """
        prompt_text = context.to_prompt_context()

        if self.backend is None:
            raise RuntimeError("No LLM backend configured")

        try:
            response_text = self.backend.complete(SYSTEM_PROMPT, prompt_text)

            # Parse JSON from response (may have markdown wrapping)
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                decision_data = json.loads(response_text[json_start:json_end])
            else:
                decision_data = {
                    "action": "wait",
                    "reasoning": "Could not parse LLM response",
                    "confidence": 0.3,
                }

            # Validate field types from untrusted LLM output
            valid_actions = {"send_input", "wait", "escalate", "mark_complete", "restart"}
            action = decision_data.get("action", "")
            if not isinstance(action, str) or action not in valid_actions:
                decision_data["action"] = "wait"
            if "confidence" in decision_data:
                try:
                    decision_data["confidence"] = max(
                        0.0, min(1.0, float(decision_data["confidence"]))
                    )
                except (TypeError, ValueError):
                    decision_data["confidence"] = 0.5
            if not isinstance(decision_data.get("input_text", ""), str):
                decision_data["input_text"] = ""
            if not isinstance(decision_data.get("reasoning", ""), str):
                decision_data["reasoning"] = ""

            return SessionDecision(
                session_name=context.session_name,
                vm_name=context.vm_name,
                action=decision_data.get("action", "wait"),
                input_text=decision_data.get("input_text", ""),
                reasoning=decision_data.get("reasoning", ""),
                confidence=decision_data.get("confidence", 0.5),
            )

        except NotImplementedError:
            return SessionDecision(
                session_name=context.session_name,
                vm_name=context.vm_name,
                action="escalate",
                reasoning="LLM backend not implemented",
                confidence=0.0,
            )
        except Exception as e:
            return SessionDecision(
                session_name=context.session_name,
                vm_name=context.vm_name,
                action="escalate",
                reasoning=f"LLM call failed: {e}",
                confidence=0.0,
            )

    def _execute_decision(self, decision: SessionDecision) -> None:
        """ACT: Execute the decision on the remote session."""
        # Validate names before subprocess use
        validate_vm_name(decision.vm_name)
        validate_session_name(decision.session_name)

        # H4: Confidence threshold -- reject low-confidence actions
        if decision.action == "send_input" and decision.confidence < MIN_CONFIDENCE_SEND:
            import logging as _log

            _log.getLogger(__name__).info(
                "Suppressed send_input (confidence %.2f < %.2f)",
                decision.confidence,
                MIN_CONFIDENCE_SEND,
            )
            return
        if decision.action == "restart" and decision.confidence < MIN_CONFIDENCE_RESTART:
            return  # Too low confidence for restart

        # H10: Dangerous input blocklist -- block before sending
        if decision.action == "send_input" and decision.input_text:
            if is_dangerous_input(decision.input_text):
                decision.action = "escalate"
                decision.reasoning = f"BLOCKED: Input contains dangerous pattern. Original: {decision.input_text[:100]}"
                return

        if decision.action == "send_input" and decision.input_text:
            safe_session = shlex.quote(decision.session_name)
            # Use tmux send-keys to inject the input
            for line in decision.input_text.split("\n"):
                cmd = f"tmux send-keys -t {safe_session} {shlex.quote(line)} Enter"
                try:
                    subprocess.run(
                        [self.azlin_path, "connect", decision.vm_name, "--no-tmux", "--", cmd],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                    pass

        elif decision.action == "restart":
            safe_session = shlex.quote(decision.session_name)
            cmd = (
                f"tmux send-keys -t {safe_session} C-c C-c && sleep 1 && tmux send-keys -t {safe_session} '!!'"
                + " Enter"
            )
            try:
                subprocess.run(
                    [self.azlin_path, "connect", decision.vm_name, "--no-tmux", "--", cmd],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                pass

    def _show_decision(self, decision: SessionDecision, context: SessionContext) -> None:
        """DRY-RUN: Print what the admiral would do without acting."""
        print(f"\n{'=' * 60}")
        print(f"DRY RUN: {decision.vm_name}/{decision.session_name}")
        print(f"{'=' * 60}")
        print(f"Status: {context.agent_status}")
        if context.git_branch:
            print(f"Branch: {context.git_branch}")
        if context.repo_url:
            print(f"Repo: {context.repo_url}")
        print("\nTerminal (last 10 lines):")
        for line in context.tmux_capture.strip().split("\n")[-10:]:
            print(f"  | {line[:120]}")
        if context.transcript_summary:
            print("\nTranscript context:")
            for line in context.transcript_summary.strip().split("\n")[-5:]:
                print(f"  > {line[:120]}")
        print("\nDecision:")
        print(decision.summary())
        print(f"{'=' * 60}")

    def dry_run_report(self) -> str:
        """Summary of all decisions from dry-run mode."""
        if not self._decisions:
            return "No decisions made yet."

        lines = [
            f"Fleet Admiral Dry Run — {len(self._decisions)} sessions analyzed",
            "",
        ]

        action_counts = {}
        for d in self._decisions:
            action_counts[d.action] = action_counts.get(d.action, 0) + 1

        lines.append("Summary:")
        for action, count in sorted(action_counts.items()):
            lines.append(f"  {action}: {count}")
        lines.append("")

        for d in self._decisions:
            lines.append(d.summary())
            lines.append("")

        return "\n".join(lines)
