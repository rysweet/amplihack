"""Regression tests for issues #3010 and #3011.

Issue #3010: dev-orchestrator must allow report_intent in parallel with the
Bash launch call, not hard-require Bash as the *only* next tool call.

Issue #3011: dev-orchestrator must provide shell-policy-safe tmux restart
guidance that does not rely on ``tmux kill-session``.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_ORCHESTRATOR_SKILL = REPO_ROOT / ".claude" / "skills" / "dev-orchestrator" / "SKILL.md"


class TestIssue3010ReportIntentCompatibility:
    """The skill must not hard-require Bash as the sole next tool call."""

    def setup_method(self):
        self.content = DEV_ORCHESTRATOR_SKILL.read_text()

    def test_no_hard_must_be_a_bash_tool_call(self):
        """The old phrasing 'MUST be a Bash tool call' is replaced."""
        assert "MUST be a Bash tool call that" not in self.content

    def test_allows_report_intent_in_parallel(self):
        """The skill explicitly mentions report_intent as acceptable."""
        assert "report_intent" in self.content

    def test_must_include_bash_launch(self):
        """The skill still requires a Bash launch — just not as the *sole* call."""
        assert "MUST include a Bash tool call" in self.content

    def test_next_tool_calls_plural_form(self):
        """The follow-up instruction uses the plural 'tool call(s)'."""
        assert "next tool call(s)" in self.content


class TestIssue3011TmuxRestartGuidance:
    """The skill must provide shell-policy-safe tmux restart alternatives."""

    def setup_method(self):
        self.content = DEV_ORCHESTRATOR_SKILL.read_text()

    def test_no_kill_session_as_primary_instruction(self):
        """The skill must not recommend ``tmux kill-session`` as the restart path."""
        assert "tmux kill-session -t recipe-runner" not in self.content

    def test_unique_session_name_option(self):
        """Option A: unique session name per run."""
        assert "recipe-$(date +%s)" in self.content

    def test_numeric_pid_option(self):
        """Option B: numeric PID termination."""
        assert "#{pid}" in self.content

    def test_send_exit_option(self):
        """Option C: send exit to panes."""
        assert 'send-keys -t recipe-runner "exit"' in self.content

    def test_shell_policy_safe_section_exists(self):
        """A dedicated section on restarting stale tmux sessions exists."""
        assert "Restarting a stale tmux session" in self.content
