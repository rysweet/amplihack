"""Workflow checks mixin - checks for workflow compliance and completion."""

import json
import re
import sys

# Pre-compiled patterns for _check_next_steps (avoids re-compilation on every call)
_NEXT_STEPS_PATTERNS = [
    re.compile(
        r"(next steps?|remaining|todo|outstanding|still need to):\s*[\r\n]+\s*[-•*\d.]",
        re.IGNORECASE,
    ),
]
_NEGATION_PATTERNS = [
    re.compile(r"no\s+(next\s+steps?|remaining|outstanding|todo)", re.IGNORECASE),
    re.compile(
        r"(next\s+steps?|remaining|outstanding|todo)\s+(?:are\s+)?(?:none|empty|complete)",
        re.IGNORECASE,
    ),
    re.compile(r"all\s+(?:done|complete|finished)", re.IGNORECASE),
    re.compile(r"nothing\s+(?:left|remaining|outstanding)", re.IGNORECASE),
]

# Pre-compiled patterns for _check_next_steps handoff detection
_HANDOFF_PATTERNS = [
    re.compile(r"wait\s+for\s+(ci|review|approval|merge)"),
    re.compile(r"(user|you)\s+(should|can|may|need to)"),
    re.compile(r"filed\s+(as|in)\s+#"),
    re.compile(r"tracked\s+in\s+#"),
    re.compile(r"when\s+ci\s+passes"),
    re.compile(r"pr\s+ready\s+for\s+review"),
    re.compile(r"ready\s+for\s+(review|merge|approval)"),
    re.compile(r"waiting\s+for\s+(review|approval|ci|merge)"),
]


class ChecksWorkflowMixin:
    """Mixin with workflow compliance check methods."""

    def _check_todos_complete(self, transcript: list[dict], session_id: str) -> bool:
        """Check if all TODO items completed.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if all TODOs completed, False otherwise
        """
        last_todo_write = self._find_last_todo_write(transcript)
        if not last_todo_write:
            return True  # No todos to check

        todos = last_todo_write.get("todos", [])
        return all(todo.get("status") == "completed" for todo in todos)

    def _check_workflow_invocation(self, transcript: list[dict], session_id: str) -> bool:
        """Check if workflow was properly invoked using Claude SDK analysis.

        Uses context-aware AI analysis to detect workflow invocation patterns:
        - Explicit Skill tool invocation
        - Explicit Read tool invocation
        - Implicit step-by-step workflow following
        - Async completion (PR created for review, CI running)

        Issue #2040: Enforce workflow invocation compliance

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if workflow properly invoked or not required, False otherwise
        """
        try:
            # Import SDK analysis function
            from claude_power_steering import analyze_workflow_invocation_sync

            # Determine session type from state if available
            session_type = "DEVELOPMENT"  # Default
            try:
                state_file = self.runtime_dir / session_id / "turn_state.json"
                if state_file.exists():
                    state = json.loads(state_file.read_text())
                    session_type = state.get("session_type", "DEVELOPMENT")
            except Exception as e:
                self._log(
                    f"Could not load session type from state file, using default: {e}",
                    "WARNING",
                    exc_info=True,
                )

            # Use SDK analysis for workflow invocation validation
            valid, reason = analyze_workflow_invocation_sync(
                transcript, session_type, self.project_root
            )

            if not valid:
                # Log violation details
                self._log_violation(
                    "workflow_invocation",
                    {
                        "reason": reason or "Workflow not properly invoked",
                        "session_type": session_type,
                    },
                    session_id,
                )

            return valid

        except ImportError:
            # SDK not available - fail open
            sys.stderr.write(
                "[Power Steering] claude_power_steering not available, skipping workflow check\n"
            )
            return True
        except Exception as e:
            # Fail-open on errors
            sys.stderr.write(f"[Power Steering] Error in _check_workflow_invocation: {e}\n")
            self._log(f"Error in _check_workflow_invocation: {e}", "WARNING", exc_info=True)
            return True

    def _check_skill_invocation(self, transcript: list[dict], session_id: str) -> bool:
        """Check if a requested skill was actually invoked.

        If the session was started with a slash command (indicated by a
        <command-name> tag in the transcript), verify the Skill tool was
        called for that skill. If no command-name tag exists, the check
        is automatically satisfied (no skill was requested). (Issue #2914)

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no skill was requested or if the requested skill was invoked
        """
        # Find <command-name> tag in user messages
        requested_skill = None
        for msg in transcript:
            if msg.get("type") != "user":
                continue
            content_str = str(msg.get("message", {}).get("content", ""))
            match = re.search(r"<command-name>/?([\w:.-]+)</command-name>", content_str)
            if match:
                requested_skill = match.group(1)
                break

        if not requested_skill:
            return True  # No skill requested — check not applicable

        # Check if the Skill tool was called for this skill
        for msg in transcript:
            if msg.get("type") != "assistant":
                continue
            content = msg.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                if block.get("name") == "Skill":
                    invoked = block.get("input", {}).get("skill", "")
                    if invoked == requested_skill:
                        self._log(f"Skill '{requested_skill}' was invoked", "DEBUG")
                        return True

        self._log(f"Skill '{requested_skill}' was requested but not invoked", "WARNING")
        return False

    def _check_no_direct_main_commit(self, transcript: list[dict], session_id: str) -> bool:
        """Check that the agent did not commit directly to main.

        Verifies the mandatory user preference that all code changes go through
        a feature branch and PR, never committing directly to main/master.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no direct-to-main commits detected, False otherwise
        """
        for i, msg in enumerate(transcript):
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Bash":
                                command = block.get("input", {}).get("command", "")
                                # Detect git commit on main/master
                                if "git commit" in command:
                                    # Check NEARBY messages for branch context
                                    if self._is_on_main_branch_near(transcript, i):
                                        return False
                                # Detect git push to main/master (explicit or bare)
                                if "git push" in command:
                                    if "origin main" in command or "origin master" in command:
                                        return False
                                    # Bare git push (no branch specified) while on main
                                    if (
                                        "origin main" not in command
                                        and "origin master" not in command
                                    ):
                                        # Only flag if no branch is specified at all
                                        # (git push, git push origin, git push -u origin)
                                        parts = command.strip().split()
                                        # If command is just "git push" or "git push origin"
                                        # (no branch arg), check if we're on main
                                        has_branch_arg = len(parts) > 3 or any(
                                            p.startswith("feat/")
                                            or p.startswith("fix/")
                                            or p.startswith("docs/")
                                            for p in parts
                                        )
                                        if not has_branch_arg and self._is_on_main_branch_near(
                                            transcript, i
                                        ):
                                            return False
        return True

    def _is_on_main_branch_near(self, transcript: list[dict], commit_index: int) -> bool:
        """Check if git context NEAR a commit command shows we're on main/master.

        Searches within 10 messages before the commit for the most recent
        branch indicator. This avoids false positives where the session started
        on main but switched to a feature branch before committing.

        Args:
            transcript: List of message dictionaries
            commit_index: Index of the message containing the git commit

        Returns:
            True if nearest branch evidence shows main/master
        """
        # Search the 10 messages before the commit for branch context
        start = max(0, commit_index - 10)
        # Also check the most recent branch indicator, not just any indicator
        for msg in reversed(transcript[start:commit_index]):
            if msg.get("type") == "tool_result":
                output = str(msg.get("message", {}).get("content", "")).lower()
                # If we find a feature branch indicator, we're NOT on main
                if (
                    "on branch " in output
                    and "on branch main" not in output
                    and "on branch master" not in output
                ):
                    return False
                # If we find main/master indicator, we ARE on main
                if "on branch main" in output or "on branch master" in output:
                    return True
                if "* main" in output or "* master" in output:
                    return True
        # No branch context found nearby — fail-open (assume not on main)
        return False

    def _check_dev_workflow_complete(self, transcript: list[dict], session_id: str) -> bool:
        """Check if full DEFAULT_WORKFLOW followed.

        Heuristics:
        - Look for multiple agent invocations (architect, builder, reviewer)
        - Check for test execution
        - Verify git operations (commit, push)

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if workflow complete, False otherwise
        """
        # Single-pass: collect file ops and test commands simultaneously
        has_file_ops = False
        has_tests = False
        direct_patterns = self.TEST_COMMAND_PATTERNS + self.VALIDATION_COMMAND_PATTERNS
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict) or block.get("type") != "tool_use":
                            continue
                        tool_name = block.get("name", "")
                        if tool_name in ("Edit", "Write"):
                            has_file_ops = True
                        elif tool_name == "Bash" and not has_tests:
                            command = block.get("input", {}).get("command", "")
                            if any(p in command for p in direct_patterns):
                                has_tests = True
                            elif any(
                                p in command for p in self.INLINE_VALIDATION_PATTERNS
                            ) and self._is_meaningful_validation(command):
                                has_tests = True
            # Early exit once both flags are set
            if has_file_ops and has_tests:
                break

        # If no file operations, likely not a development task
        if not has_file_ops:
            return True

        if not has_tests:
            return False

        return True

    def _check_next_steps(self, transcript: list[dict], session_id: str) -> bool:
        """Check that work is complete with NO remaining next steps.

        INVERTED LOGIC: If the agent mentions "next steps", "remaining work", or
        similar phrases in their final messages, that means they're acknowledging
        there's MORE work to do. This check FAILS when next steps are found,
        prompting the agent to continue working until no next steps remain.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if NO next steps found (work is complete)
            False if next steps ARE found (work is incomplete - should continue)
        """
        # Keywords that indicate incomplete work
        incomplete_work_keywords = [
            "next steps",
            "next step",
            "follow-up",
            "follow up",
            "future work",
            "remaining work",
            "remaining tasks",
            "still need to",
            "still needs to",
            "todo",
            "to-do",
            "to do",
            "left to do",
            "more to do",
            "additional work",
            "further work",
            "outstanding",
            "not yet complete",
            "not yet done",
            "incomplete",
            "pending",
            "planned for later",
            "deferred",
        ]

        # Check RECENT assistant messages (last 10) for incomplete work indicators
        # These are where the agent would summarize before stopping
        recent_messages = [m for m in transcript[-20:] if m.get("type") == "assistant"][-10:]

        for msg in reversed(recent_messages):
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = str(block.get("text", "")).lower()
                        for keyword in incomplete_work_keywords:
                            if keyword in text:
                                self._log(
                                    f"Incomplete work indicator found: '{keyword}' - agent should continue",
                                    "INFO",
                                )
                                return False  # Work is INCOMPLETE

        # No incomplete work indicators found - work is complete
        return True
