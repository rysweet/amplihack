"""Fleet observer — detects agent state via tmux pane capture.

Uses tmux capture-pane to read agent output and classify state:
- RUNNING: agent producing output, no error indicators
- IDLE: tmux session exists but no agent running
- COMPLETED: agent finished (PR created, "complete" indicators)
- STUCK: no output change for N minutes
- ERROR: error messages detected in output
- WAITING_INPUT: agent waiting for user input

Public API:
    FleetObserver: Observes and classifies agent state in tmux sessions
"""

from __future__ import annotations

import logging
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime

from amplihack.fleet._constants import (
    CONFIDENCE_COMPLETION,
    CONFIDENCE_DEFAULT_RUNNING,
    CONFIDENCE_ERROR,
    CONFIDENCE_IDLE,
    CONFIDENCE_RUNNING,
    CONFIDENCE_UNKNOWN,
    DEFAULT_CAPTURE_LINES,
    DEFAULT_STUCK_THRESHOLD_SECONDS,
)
from amplihack.fleet._defaults import get_azlin_path
from amplihack.fleet._validation import validate_vm_name
from amplihack.fleet.fleet_state import AgentStatus, TmuxSessionInfo
from amplihack.utils.logging_utils import log_call

__all__ = ["FleetObserver", "ObservationResult"]

logger = logging.getLogger(__name__)

# Patterns that indicate specific agent states
COMPLETION_PATTERNS = [
    r"PR.*created",
    r"pull request.*created",
    r"GOAL_STATUS:\s*ACHIEVED",
    r"Workflow Complete",
    r"All \d+ steps completed",
    r"pushed to.*branch",
]

ERROR_PATTERNS = [
    r"(?:^|\n)\s*(?:ERROR|FATAL|CRITICAL):",
    r"Traceback \(most recent",
    r"panic:",
    r"GOAL_STATUS:\s*NOT_ACHIEVED",
    r"Permission denied",
    r"Authentication failed",
]

WAITING_PATTERNS = [
    r"[?]\s*\[Y/n\]",  # Y/n prompts
    r"[?]\s*\[y/N\]",
    r"\(yes/no\)",
    r"Press .* to continue",
    r"Do you want to",
    r"^Enter\s+\w+\s*:",
    r"waiting for.*input",
]

RUNNING_PATTERNS = [
    r"Step \d+",
    r"Task.*in_progress",
    r"Building",
    r"Implementing",
    r"Analyzing",
    r"Reading file",
    r"Writing file",
    r"Running tests",
    r"Creating.*commit",
]

# Shell prompt patterns indicating idle state (no agent running)
IDLE_PATTERNS = [
    r"\$\s*$",  # Bare shell prompt
    r"azureuser@.*:\~.*\$",
    r"❯\s*$",
]


@dataclass
class ObservationResult:
    """Result of observing a single tmux session."""

    session_name: str
    vm_name: str
    status: AgentStatus
    last_output_lines: list[str] = field(default_factory=list)
    confidence: float = 0.0
    matched_pattern: str = ""
    observed_at: datetime | None = None


@dataclass
class FleetObserver:
    """Observes agent state by capturing tmux pane content.

    Uses tmux capture-pane to read the visible terminal output and
    classifies the agent's state using pattern matching.
    """

    azlin_path: str = field(default_factory=get_azlin_path)
    capture_lines: int = DEFAULT_CAPTURE_LINES
    _previous_captures: dict[str, str] = field(default_factory=dict)
    _last_change_time: dict[str, float] = field(default_factory=dict)
    stuck_threshold_seconds: float = DEFAULT_STUCK_THRESHOLD_SECONDS

    @log_call
    def observe_session(self, vm_name: str, session_name: str) -> ObservationResult:
        """Observe a single tmux session and classify agent state.

        Args:
            vm_name: VM hosting the session
            session_name: tmux session name

        Returns:
            ObservationResult with classified status
        """
        pane_content = self._capture_pane(vm_name, session_name)

        if pane_content is None:
            return ObservationResult(
                session_name=session_name,
                vm_name=vm_name,
                status=AgentStatus.UNKNOWN,
                confidence=0.0,
                observed_at=datetime.now(),
            )

        lines = pane_content.strip().split("\n")
        non_empty_lines = [l for l in lines if l.strip()]

        status, confidence, pattern = self._classify_output(non_empty_lines, vm_name, session_name)

        return ObservationResult(
            session_name=session_name,
            vm_name=vm_name,
            status=status,
            last_output_lines=non_empty_lines,
            confidence=confidence,
            matched_pattern=pattern,
            observed_at=datetime.now(),
        )

    @log_call
    def observe_all(
        self,
        sessions: list[TmuxSessionInfo],
    ) -> list[ObservationResult]:
        """Observe multiple sessions and return classified results."""
        results = []
        for sess in sessions:
            result = self.observe_session(sess.vm_name, sess.session_name)
            results.append(result)
        return results

    @log_call
    def _capture_pane(self, vm_name: str, session_name: str) -> str | None:
        """Capture tmux pane content from a remote VM."""
        import shlex

        validate_vm_name(vm_name)
        # shlex.quote handles safety for the session name in the SSH command.
        # Don't use validate_session_name here — tmux reports names like "(none)"
        # that are valid but don't match our strict regex.
        if not session_name:
            return None

        cmd = f"tmux capture-pane -t {shlex.quote(session_name)} -p -S -{self.capture_lines} 2>/dev/null"
        try:
            result = subprocess.run(
                [self.azlin_path, "connect", vm_name, "--no-tmux", "--", cmd],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
            logger.warning("Capture pane failed for %s/%s: %s", vm_name, session_name, exc)
        return None

    @log_call
    def _classify_output(
        self,
        lines: list[str],
        vm_name: str,
        session_name: str,
    ) -> tuple[AgentStatus, float, str]:
        """Classify agent state from recent output lines.

        Returns (status, confidence, matched_pattern).
        """
        if not lines:
            return AgentStatus.UNKNOWN, 0.0, ""

        combined = "\n".join(lines)
        key = f"{vm_name}:{session_name}"

        # Check patterns in priority order (most specific first)

        # 1. Completion patterns
        for pattern in COMPLETION_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return AgentStatus.COMPLETED, CONFIDENCE_COMPLETION, pattern

        # 2. Error patterns
        for pattern in ERROR_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return AgentStatus.ERROR, CONFIDENCE_ERROR, pattern

        # 3. Running patterns (checked BEFORE stuck so active work isn't
        #    misclassified as stuck when output hasn't changed yet)
        for pattern in RUNNING_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                # Update change tracking so running sessions reset the timer
                self._last_change_time[key] = time.monotonic()
                self._previous_captures[key] = combined
                return AgentStatus.RUNNING, CONFIDENCE_RUNNING, pattern

        # 4. Waiting for input (checked BEFORE stuck — more specific)
        for pattern in WAITING_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE | re.MULTILINE):
                return AgentStatus.WAITING_INPUT, CONFIDENCE_RUNNING, pattern

        # 5. Check for stuck (no output change) — after running and waiting
        now = time.monotonic()
        prev = self._previous_captures.get(key, "")
        if combined == prev:
            last_change = self._last_change_time.get(key, now)
            if now - last_change > self.stuck_threshold_seconds:
                self._previous_captures[key] = combined
                return AgentStatus.STUCK, CONFIDENCE_RUNNING, "no_output_change"
        else:
            self._last_change_time[key] = now
        self._previous_captures[key] = combined

        # 6. Idle (shell prompt, no agent)
        last_line = lines[-1].strip() if lines else ""
        for pattern in IDLE_PATTERNS:
            if re.search(pattern, last_line):
                return AgentStatus.IDLE, CONFIDENCE_IDLE, pattern

        # Default: if there's recent output, assume running
        if len(combined.strip()) > 50:
            return AgentStatus.RUNNING, CONFIDENCE_DEFAULT_RUNNING, "has_output"

        return AgentStatus.UNKNOWN, CONFIDENCE_UNKNOWN, ""
