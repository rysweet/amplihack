"""Per-session reasoning loop -- the admiral's brain for each agent session.

For each session, the admiral:
1. PERCEIVE: Capture tmux pane + read JSONL transcript
2. REASON: Use Anthropic SDK to decide what action to take
3. ACT: Inject keystrokes via tmux send-keys (or show in dry-run)
4. LEARN: Record the decision and its outcome

The key insight: the admiral doesn't just OBSERVE sessions -- it DRIVES them
by typing into the TUI when agents need input, get stuck, or need redirection.

Public API:
    SessionReasoner: Per-session reasoning engine
    SessionContext: Gathered context for a single session
    SessionDecision: What the admiral decided to do
"""

from __future__ import annotations

import json
import logging
import shlex
import subprocess
from dataclasses import dataclass, field

from amplihack.fleet._backends import (
    AnthropicBackend,
    CopilotBackend,
    LiteLLMBackend,
    LLMBackend,
    auto_detect_backend,
)
from amplihack.fleet._constants import MIN_CONFIDENCE_RESTART, MIN_CONFIDENCE_SEND
from amplihack.fleet._defaults import get_azlin_path
from amplihack.fleet._session_context import SessionContext, SessionDecision
from amplihack.fleet._session_gather import gather_context
from amplihack.fleet._status import infer_agent_status
from amplihack.fleet._system_prompt import SYSTEM_PROMPT
from amplihack.fleet._validation import (
    is_dangerous_input,
    validate_session_name,
    validate_vm_name,
)

logger = logging.getLogger(__name__)

__all__ = [
    "SessionReasoner",
    "SessionContext",
    "SessionDecision",
    # Re-exported for backward compatibility
    "LLMBackend",
    "AnthropicBackend",
    "CopilotBackend",
    "LiteLLMBackend",
    "auto_detect_backend",
    "infer_agent_status",
]


@dataclass
class SessionReasoner:
    """Per-session reasoning engine -- SDK-agnostic.

    Uses an LLMBackend protocol that supports both Claude and Copilot SDKs.
    Gathers context for a session, calls the LLM to decide what to do,
    then either acts (live mode) or shows the decision (dry-run mode).
    """

    azlin_path: str = field(default_factory=get_azlin_path)
    backend: LLMBackend | None = None
    dry_run: bool = False
    _decisions: list[SessionDecision] = field(default_factory=list)

    def __post_init__(self):
        if self.backend is None:
            self.backend = auto_detect_backend()

    def reason_about_session(
        self,
        vm_name: str,
        session_name: str,
        task_prompt: str = "",
        project_priorities: str = "",
    ) -> SessionDecision:
        """Full reasoning loop for a single session."""
        # 1. PERCEIVE
        context = self._gather_context(vm_name, session_name, task_prompt, project_priorities)

        # 2. REASON -- fast-path: skip LLM call if agent is actively thinking
        if context.agent_status == "thinking":
            decision = SessionDecision(
                session_name=session_name,
                vm_name=vm_name,
                action="wait",
                reasoning="Agent is actively thinking/processing -- do not interrupt",
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
        """Reason about multiple sessions."""
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

    # Delegation methods for backward compatibility (used by tests)
    def _gather_context(self, vm_name, session_name, task_prompt, project_priorities):
        """Delegate to standalone gather_context."""
        return gather_context(self.azlin_path, vm_name, session_name, task_prompt, project_priorities)

    def _parse_context_output(self, output, context):
        """Delegate to standalone parse_context_output."""
        from amplihack.fleet._session_gather import parse_context_output as _parse
        _parse(output, context)

    def _infer_status(self, tmux_text):
        """Delegate to module-level infer_agent_status."""
        return infer_agent_status(tmux_text)

    def reason(self, context: SessionContext) -> SessionDecision:
        """Public entry point for LLM-based reasoning about a session context."""
        return self._reason(context)

    def _reason(self, context: SessionContext) -> SessionDecision:
        """REASON: Call LLM backend to decide what to do."""
        prompt_text = context.to_prompt_context()

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

    def execute_decision(self, decision: SessionDecision) -> None:
        """Public API: Execute the decision on the remote session."""
        self._execute_decision(decision)

    def _execute_decision(self, decision: SessionDecision) -> None:
        """ACT: Execute the decision on the remote session (internal)."""
        validate_vm_name(decision.vm_name)
        validate_session_name(decision.session_name)

        # H4: Confidence threshold -- reject low-confidence actions
        if decision.action == "send_input" and decision.confidence < MIN_CONFIDENCE_SEND:
            logger.info(
                "Suppressed send_input (confidence %.2f < %.2f)",
                decision.confidence,
                MIN_CONFIDENCE_SEND,
            )
            return
        if decision.action == "restart" and decision.confidence < MIN_CONFIDENCE_RESTART:
            return

        # H10: Dangerous input blocklist -- block before sending
        if decision.action == "send_input" and decision.input_text:
            if is_dangerous_input(decision.input_text):
                decision.action = "escalate"
                decision.reasoning = f"BLOCKED: Input contains dangerous pattern. Original: {decision.input_text[:100]}"
                return

        if decision.action == "send_input" and decision.input_text:
            safe_session = shlex.quote(decision.session_name)
            for line in decision.input_text.split("\n"):
                cmd = f"tmux send-keys -t {safe_session} {shlex.quote(line)} Enter"
                try:
                    subprocess.run(
                        [self.azlin_path, "connect", decision.vm_name, "--no-tmux", "--", cmd],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
                    logger.warning(
                        "send_input failed for %s/%s: %s",
                        decision.vm_name,
                        decision.session_name,
                        exc,
                    )

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
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
                logger.warning(
                    "restart failed for %s/%s: %s",
                    decision.vm_name,
                    decision.session_name,
                    exc,
                )

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
            f"Fleet Admiral Dry Run -- {len(self._decisions)} sessions analyzed",
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
