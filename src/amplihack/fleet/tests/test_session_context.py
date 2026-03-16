"""Tests for fleet _session_context -- SessionContext and SessionDecision.

Tests the dataclass construction, validation, prompt formatting, and
decision summary rendering.

Testing pyramid:
- 100% unit tests (fast, no I/O)
"""

from __future__ import annotations

from datetime import datetime

import pytest

from amplihack.fleet._session_context import SessionContext, SessionDecision

# ---------------------------------------------------------------------------
# SessionContext construction
# ---------------------------------------------------------------------------


class TestSessionContextConstruction:
    """Tests for SessionContext dataclass creation and validation."""

    def test_minimal_construction(self):
        """Construct with only required fields (vm_name, session_name)."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        assert ctx.vm_name == "devy"
        assert ctx.session_name == "task-1"
        assert ctx.tmux_capture == ""
        assert ctx.agent_status == ""
        assert ctx.files_modified == []

    def test_full_construction(self):
        """Construct with all fields populated."""
        ctx = SessionContext(
            vm_name="devo",
            session_name="build-auth",
            tmux_capture="$ pytest\nall passed",
            transcript_summary="Agent ran tests",
            working_directory="/home/user/project",
            git_branch="feat/auth",
            repo_url="https://github.com/org/repo",
            agent_status="running",
            files_modified=["auth.py", "test_auth.py"],
            pr_url="https://github.com/org/repo/pull/42",
            task_prompt="Implement authentication",
            project_priorities="Security first",
        )
        assert ctx.vm_name == "devo"
        assert ctx.git_branch == "feat/auth"
        assert ctx.files_modified == ["auth.py", "test_auth.py"]
        assert ctx.pr_url == "https://github.com/org/repo/pull/42"

    def test_rejects_invalid_vm_name(self):
        """vm_name validation rejects shell-unsafe characters."""
        with pytest.raises(ValueError, match="Invalid VM name"):
            SessionContext(vm_name="bad name!", session_name="ok-session")

    def test_rejects_invalid_session_name(self):
        """session_name validation rejects shell-unsafe characters."""
        with pytest.raises(ValueError, match="Invalid session name"):
            SessionContext(vm_name="devy", session_name="bad session!")

    def test_rejects_empty_vm_name(self):
        """Empty vm_name is rejected by validation."""
        with pytest.raises(ValueError, match="Invalid VM name"):
            SessionContext(vm_name="", session_name="task-1")

    def test_files_modified_default_is_independent(self):
        """Each instance gets its own files_modified list (no shared default)."""
        ctx1 = SessionContext(vm_name="devy", session_name="s1")
        ctx2 = SessionContext(vm_name="devy", session_name="s2")
        ctx1.files_modified.append("file.py")
        assert ctx2.files_modified == []

    def test_project_fields_default(self):
        """project_name and project_objectives default to empty."""
        ctx = SessionContext(vm_name="devy", session_name="s1")
        assert ctx.project_name == ""
        assert ctx.project_objectives == []

    def test_project_fields_populated(self):
        """project_name and project_objectives can be set."""
        ctx = SessionContext(
            vm_name="devy",
            session_name="s1",
            project_name="myapp",
            project_objectives=[
                {"number": 1, "title": "Add auth", "state": "open"},
                {"number": 2, "title": "Fix bug", "state": "closed"},
            ],
        )
        assert ctx.project_name == "myapp"
        assert len(ctx.project_objectives) == 2

    def test_project_objectives_default_independent(self):
        """Each instance gets its own project_objectives list."""
        ctx1 = SessionContext(vm_name="devy", session_name="s1")
        ctx2 = SessionContext(vm_name="devy", session_name="s2")
        ctx1.project_objectives.append({"number": 1, "title": "X", "state": "open"})
        assert ctx2.project_objectives == []


# ---------------------------------------------------------------------------
# SessionContext.to_prompt_context
# ---------------------------------------------------------------------------


class TestSessionContextToPromptContext:
    """Tests for to_prompt_context formatting."""

    def test_includes_vm_and_session(self):
        """Output always contains VM and session identifiers."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = ctx.to_prompt_context()
        assert "VM: devy" in output
        assert "Session: task-1" in output

    def test_includes_status(self):
        """Output always contains the agent status line."""
        ctx = SessionContext(vm_name="devy", session_name="task-1", agent_status="running")
        output = ctx.to_prompt_context()
        assert "Status: running" in output

    def test_includes_all_populated_fields(self):
        """When all fields are set, all appear in the output."""
        ctx = SessionContext(
            vm_name="devo",
            session_name="build-auth",
            tmux_capture="$ pytest\nOK",
            transcript_summary="Tests passed",
            working_directory="/home/user/project",
            git_branch="feat/auth",
            repo_url="https://github.com/org/repo",
            agent_status="idle",
            files_modified=["auth.py", "views.py"],
            pr_url="https://github.com/org/repo/pull/5",
            task_prompt="Build auth module",
            project_priorities="Ship fast",
        )
        output = ctx.to_prompt_context()
        assert "Repo: https://github.com/org/repo" in output
        assert "Branch: feat/auth" in output
        assert "Original task: Build auth module" in output
        assert "PR: https://github.com/org/repo/pull/5" in output
        assert "auth.py" in output
        assert "views.py" in output
        assert "Tests passed" in output
        assert "$ pytest" in output
        assert "Ship fast" in output

    def test_handles_empty_fields_gracefully(self):
        """When optional fields are empty, they are omitted (not blank lines)."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = ctx.to_prompt_context()
        # These should NOT appear when empty
        assert "Repo:" not in output
        assert "Branch:" not in output
        assert "Original task:" not in output
        assert "PR:" not in output
        assert "Files modified:" not in output
        assert "Transcript summary:" not in output
        assert "Project priorities:" not in output

    def test_empty_tmux_shows_placeholder(self):
        """When tmux_capture is empty, output shows '(empty)' placeholder."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = ctx.to_prompt_context()
        assert "(empty)" in output

    def test_nonempty_tmux_shows_capture(self):
        """When tmux_capture has content, it appears instead of placeholder."""
        ctx = SessionContext(vm_name="devy", session_name="task-1", tmux_capture="hello world")
        output = ctx.to_prompt_context()
        assert "hello world" in output
        assert "(empty)" not in output

    def test_includes_project_and_objectives(self):
        """When project_name and objectives are set, they appear in output."""
        ctx = SessionContext(
            vm_name="devy",
            session_name="task-1",
            project_name="myapp",
            project_objectives=[
                {"number": 1, "title": "Add auth", "state": "open"},
                {"number": 2, "title": "Done task", "state": "closed"},
            ],
        )
        output = ctx.to_prompt_context()
        assert "Project: myapp" in output
        assert "#1: Add auth" in output
        # Closed objectives should NOT appear under "Open objectives"
        assert "#2: Done task" not in output

    def test_no_project_omits_section(self):
        """When project_name is empty, project section is omitted."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = ctx.to_prompt_context()
        assert "Project:" not in output
        assert "Open objectives:" not in output


# ---------------------------------------------------------------------------
# SessionDecision
# ---------------------------------------------------------------------------


class TestSessionDecision:
    """Tests for SessionDecision dataclass and summary()."""

    def test_construction(self):
        """Construct a decision with all fields."""
        decision = SessionDecision(
            session_name="task-1",
            vm_name="devy",
            action="send_input",
            input_text="yes",
            reasoning="Agent asked Y/n",
            confidence=0.95,
        )
        assert decision.action == "send_input"
        assert decision.input_text == "yes"
        assert decision.confidence == 0.95
        assert isinstance(decision.timestamp, datetime)

    def test_summary_with_input_text(self):
        """summary() includes input text when action is send_input."""
        decision = SessionDecision(
            session_name="task-1",
            vm_name="devy",
            action="send_input",
            input_text="yes\nplease continue",
            reasoning="Agent waiting for approval",
            confidence=0.85,
        )
        result = decision.summary()
        assert "Session: devy/task-1" in result
        assert "Action: send_input" in result
        assert "85%" in result
        assert "Agent waiting for approval" in result
        assert 'Input: "yes\\nplease continue"' in result

    def test_summary_without_input_text(self):
        """summary() omits input line when input_text is empty."""
        decision = SessionDecision(
            session_name="build-auth",
            vm_name="devo",
            action="wait",
            reasoning="Agent is thinking",
            confidence=0.70,
        )
        result = decision.summary()
        assert "Session: devo/build-auth" in result
        assert "Action: wait" in result
        assert "70%" in result
        assert "Input:" not in result

    def test_summary_truncates_long_input(self):
        """summary() truncates input_text to 100 characters for display."""
        long_input = "x" * 200
        decision = SessionDecision(
            session_name="task-1",
            vm_name="devy",
            action="send_input",
            input_text=long_input,
            reasoning="Sending long input",
            confidence=0.60,
        )
        result = decision.summary()
        # The displayed input should be at most 100 chars (from truncation)
        for line in result.split("\n"):
            if line.strip().startswith("Input:"):
                # The quoted content between " and " should be <= 100 chars
                quoted = line.split('"')[1]
                assert len(quoted) <= 100

    def test_summary_replaces_newlines_in_input(self):
        """summary() replaces newlines with \\n for single-line display."""
        decision = SessionDecision(
            session_name="task-1",
            vm_name="devy",
            action="send_input",
            input_text="line1\nline2\nline3",
            reasoning="Multi-line input",
            confidence=0.90,
        )
        result = decision.summary()
        assert "line1\\nline2\\nline3" in result
