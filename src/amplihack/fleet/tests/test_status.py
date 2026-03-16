"""Tests for fleet _status -- infer_agent_status().

Tests the tmux output classifier that determines agent state from
terminal text. Each test constructs realistic tmux output snippets
and verifies the correct status string is returned.

Testing pyramid:
- 100% unit tests (fast, no I/O)
"""

from __future__ import annotations

from amplihack.fleet._status import infer_agent_status
from amplihack.utils.logging_utils import log_call

# ---------------------------------------------------------------------------
# Thinking indicators
# ---------------------------------------------------------------------------


class TestThinkingStatus:
    """Tests for THINKING detection."""

    @log_call
    def test_spinner_dot_prefix(self):
        """Lines starting with middle-dot indicate active LLM processing."""
        text = "some context\n\u00b7 Analyzing code structure..."
        assert infer_agent_status(text) == "thinking"

    @log_call
    def test_filled_circle_tool_indicator(self):
        """Filled circle (non-Bash) indicates tool running."""
        text = "previous output\n\u25cf Read(/some/file.py)"
        assert infer_agent_status(text) == "thinking"

    @log_call
    def test_bottom_half_indicator(self):
        r"""Bottom-half character (\u23bf) means streaming in progress."""
        text = "output line\n\u23bf"
        assert infer_agent_status(text) == "thinking"

    @log_call
    def test_bash_tool_call_active(self):
        """Active Bash tool call with output means thinking."""
        text = "some output\n\u25cf Bash(ls -la)\nfile1.txt\nfile2.txt"
        assert infer_agent_status(text) == "thinking"

    @log_call
    def test_read_tool_call(self):
        """Read tool call indicates thinking."""
        text = "context\n\u25cf Read(/path/to/file)"
        assert infer_agent_status(text) == "thinking"

    @log_call
    def test_write_tool_call(self):
        """Write tool call indicates thinking."""
        text = "context\n\u25cf Write(/path/to/file)"
        assert infer_agent_status(text) == "thinking"

    @log_call
    def test_edit_tool_call(self):
        """Edit tool call indicates thinking."""
        text = "context\n\u25cf Edit(/path/to/file)"
        assert infer_agent_status(text) == "thinking"

    @log_call
    def test_copilot_thinking_text(self):
        """Copilot 'thinking...' text triggers thinking status."""
        text = "Copilot is thinking... please wait"
        assert infer_agent_status(text) == "thinking"

    @log_call
    def test_copilot_loading_text(self):
        """Copilot 'loading' text triggers thinking status."""
        text = "Loading model context..."
        assert infer_agent_status(text) == "thinking"

    @log_call
    def test_six_petalled_rosette_no_prompt(self):
        """Rosette without prompt means still processing."""
        text = "some output\n\u273b Done processing"
        assert infer_agent_status(text) == "thinking"

    @log_call
    def test_six_petalled_rosette_with_prompt_and_input(self):
        """Rosette + prompt + typed input means user submitted work."""
        text = "\u273b Finished\n\u276f implement auth"
        assert infer_agent_status(text) == "thinking"

    @log_call
    def test_prompt_with_user_input(self):
        """Claude prompt with typed text means agent processing user request."""
        text = "previous output\n\u276f refactor the module"
        assert infer_agent_status(text) == "thinking"


# ---------------------------------------------------------------------------
# Running indicators
# ---------------------------------------------------------------------------


class TestRunningStatus:
    """Tests for RUNNING detection."""

    @log_call
    def test_status_bar_running(self):
        """Status bar with (running) and play symbols indicates active run."""
        text = "output\n\u23f5\u23f5 session-1 (running) 14:32"
        assert infer_agent_status(text) == "running"

    @log_call
    def test_substantial_unrecognized_output(self):
        """More than 50 chars of unrecognized output defaults to running."""
        text = "x" * 60
        assert infer_agent_status(text) == "running"

    @log_call
    def test_moderate_unrecognized_output_still_running(self):
        """Output just above 50 chars threshold returns running."""
        text = "This is some output from the agent that is long enough to pass"
        assert len(text.strip()) > 50
        assert infer_agent_status(text) == "running"


# ---------------------------------------------------------------------------
# Idle detection
# ---------------------------------------------------------------------------


class TestIdleStatus:
    """Tests for IDLE detection."""

    @log_call
    def test_bare_shell_prompt_with_trailing_space(self):
        """Dollar-sign prompt = shell (agent dead/crashed)."""
        text = "last command output\nuser@host:~$ "
        assert infer_agent_status(text) == "shell"

    @log_call
    def test_bare_shell_prompt_no_trailing_space(self):
        """Dollar-sign prompt without trailing space = shell."""
        text = "output\nuser@host:~$"
        assert infer_agent_status(text) == "shell"

    @log_call
    def test_claude_prompt_empty(self):
        """Empty Claude prompt (no typed input) is idle."""
        text = "previous output\n\u276f "
        assert infer_agent_status(text) == "idle"

    @log_call
    def test_claude_prompt_bare(self):
        """Bare Claude prompt character is idle."""
        text = "previous output\n\u276f"
        assert infer_agent_status(text) == "idle"

    @log_call
    def test_rosette_with_empty_prompt(self):
        """Rosette followed by empty prompt means done and idle."""
        text = "\u273b Completed task\n\u276f "
        assert infer_agent_status(text) == "idle"


# ---------------------------------------------------------------------------
# Waiting input detection
# ---------------------------------------------------------------------------


class TestWaitingInputStatus:
    """Tests for WAITING_INPUT detection."""

    @log_call
    def test_yn_prompt_brackets(self):
        """[Y/n] prompt needs user input."""
        text = "Do you want to continue? [Y/n]"
        assert infer_agent_status(text) == "waiting_input"

    @log_call
    def test_yes_no_prompt(self):
        """(yes/no) prompt needs user input."""
        text = "Proceed with installation? (yes/no)"
        assert infer_agent_status(text) == "waiting_input"

    @log_call
    def test_permission_bypass_prompt(self):
        """Play symbols with bypass text = permission prompt."""
        text = "\u23f5\u23f5 Allow this action? bypass or deny"
        assert infer_agent_status(text) == "waiting_input"

    @log_call
    def test_permission_allow_prompt(self):
        """Play symbols with allow text = permission prompt."""
        text = "\u23f5\u23f5 Press enter to allow this operation"
        assert infer_agent_status(text) == "waiting_input"

    @log_call
    def test_question_mark_ending(self):
        """Line ending with question mark suggests waiting for input."""
        text = "What model would you like to use?"
        assert infer_agent_status(text) == "waiting_input"

    @log_call
    def test_tool_call_with_play_symbols(self):
        """Tool call line ending with play symbols = waiting for permission."""
        text = "\u25cf Bash(rm -rf /tmp/test)\n\u23f5\u23f5"
        assert infer_agent_status(text) == "waiting_input"


# ---------------------------------------------------------------------------
# Error detection
# ---------------------------------------------------------------------------


class TestErrorStatus:
    """Tests for ERROR detection."""

    @log_call
    def test_error_colon(self):
        """'error:' in output triggers error status."""
        text = "Compiling module...\nerror: cannot find module 'foo'"
        assert infer_agent_status(text) == "error"

    @log_call
    def test_traceback(self):
        """Python traceback triggers error status."""
        text = "Running tests...\nTraceback (most recent call last):\n  File..."
        assert infer_agent_status(text) == "error"

    @log_call
    def test_fatal_error(self):
        """'fatal:' triggers error status."""
        text = "git pull\nfatal: not a git repository"
        assert infer_agent_status(text) == "error"

    @log_call
    def test_panic_error(self):
        """'panic:' triggers error status."""
        text = "Starting service...\npanic: runtime error"
        assert infer_agent_status(text) == "error"

    @log_call
    def test_error_case_insensitive(self):
        """Error detection is case-insensitive."""
        text = "Build failed\nERROR: missing dependency"
        assert infer_agent_status(text) == "error"


# ---------------------------------------------------------------------------
# Completed detection
# ---------------------------------------------------------------------------


class TestCompletedStatus:
    """Tests for COMPLETED detection."""

    @log_call
    def test_goal_achieved(self):
        """GOAL_STATUS: ACHIEVED indicates completion."""
        text = "All tasks done.\nGOAL_STATUS: ACHIEVED"
        assert infer_agent_status(text) == "completed"

    @log_call
    def test_workflow_complete(self):
        """'Workflow Complete' indicates completion."""
        text = "Step 22 done.\nWorkflow Complete"
        assert infer_agent_status(text) == "completed"

    @log_call
    def test_pr_created(self):
        """'PR #' with 'created' indicates completion."""
        text = "gh pr create\nPR #42 created successfully"
        assert infer_agent_status(text) == "completed"

    @log_call
    def test_pull_request_opened(self):
        """'pull request' with 'opened' indicates completion."""
        text = "Created pull request\nPull request opened: https://..."
        assert infer_agent_status(text) == "completed"

    @log_call
    def test_pr_merged(self):
        """'PR #' with 'merged' indicates completion."""
        text = "gh pr merge\nPR #99 merged into main"
        assert infer_agent_status(text) == "completed"


# ---------------------------------------------------------------------------
# Unknown / edge cases
# ---------------------------------------------------------------------------


class TestUnknownStatus:
    """Tests for UNKNOWN and edge-case handling."""

    @log_call
    def test_empty_string(self):
        """Empty input returns unknown."""
        assert infer_agent_status("") == "unknown"

    @log_call
    def test_whitespace_only(self):
        """Whitespace-only input returns unknown."""
        assert infer_agent_status("   \n  \n  ") == "unknown"

    @log_call
    def test_short_unrecognized_output(self):
        """Short unrecognized output (<=50 chars) returns unknown."""
        text = "hello"
        assert len(text.strip()) <= 50
        assert infer_agent_status(text) == "unknown"

    @log_call
    def test_exactly_50_chars(self):
        """Exactly 50 chars of unrecognized output returns unknown (boundary)."""
        text = "x" * 50
        assert infer_agent_status(text) == "unknown"
