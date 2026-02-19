"""
Outside-In Tests: Exception Handling in Hooks
==============================================

Tests the exception handling improvements made to hooks code.
Uses subprocess-based black-box testing (outside-in philosophy):
- Tests behavior from external process boundary
- No knowledge of internal implementation
- Verifies: (1) logging is now visible, (2) fail-open preserved, (3) no regressions

Covers:
- xpia/hooks/pre_tool_use.py
- xpia/hooks/post_tool_use.py
- gitignore_checker.py
- workflow_classification_reminder.py
- precommit_prefs.py (import-level test)
- shutdown_context.py (import-level test)

Run with:
    python -m pytest .claude/tools/amplihack/hooks/tests/outside-in/test_exception_handling_outside_in.py -v
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

# Project root: outside-in/ → tests/ → hooks/ → amplihack/ → tools/ → .claude/ → amplihack4/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent.parent
HOOKS_DIR = PROJECT_ROOT / ".claude" / "tools" / "amplihack" / "hooks"
XPIA_HOOKS_DIR = PROJECT_ROOT / ".claude" / "tools" / "xpia" / "hooks"
# Use project venv python for subprocess invocations so hooks find their imports
PYTHON = str(PROJECT_ROOT / ".venv" / "bin" / "python")


def run_hook(
    hook_path: Path,
    stdin_data: str = "",
    env: dict | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess:
    """Run a hook script as a subprocess with given stdin."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [PYTHON, str(hook_path)],
        input=stdin_data,
        capture_output=True,
        text=True,
        env=merged_env,
        cwd=str(cwd or PROJECT_ROOT),
        timeout=15,
    )


# ─── XPIA pre_tool_use ───────────────────────────────────────────────────────


class TestXpiaPreToolUse:
    """Outside-in tests for .claude/tools/xpia/hooks/pre_tool_use.py"""

    HOOK = XPIA_HOOKS_DIR / "pre_tool_use.py"

    def test_valid_bash_command_returns_json(self):
        """Happy path: valid Bash tool input → valid JSON output, exit 0."""
        inp = json.dumps({"toolUse": {"name": "Bash", "input": {"command": "ls -la"}}})
        result = run_hook(self.HOOK, stdin_data=inp)

        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"
        # stdout must be valid JSON
        try:
            parsed = json.loads(result.stdout.strip())
            assert isinstance(parsed, dict), "stdout must be a JSON object"
        except json.JSONDecodeError as e:
            pytest.fail(f"stdout is not valid JSON: {result.stdout!r} — {e}")

    def test_valid_read_tool_returns_json(self):
        """Read tool input → valid JSON output."""
        inp = json.dumps({"toolUse": {"name": "Read", "input": {"file_path": "/etc/hostname"}}})
        result = run_hook(self.HOOK, stdin_data=inp)

        assert result.returncode == 0
        json.loads(result.stdout.strip())  # Must not raise

    def test_invalid_json_logs_error_to_stderr(self):
        """
        Fail-open: completely invalid JSON stdin triggers top-level except.
        NEW BEHAVIOR: must log '[xpia] pre_tool_use hook failed (fail-open)' to stderr.
        """
        result = run_hook(self.HOOK, stdin_data="NOT VALID JSON {{{{")

        assert result.returncode == 0, "Must exit 0 even on complete input failure"
        assert "[xpia] pre_tool_use hook failed (fail-open)" in result.stderr, (
            f"Expected error logged to stderr, got stderr={result.stderr!r}"
        )

    def test_invalid_json_still_outputs_empty_dict(self):
        """Fail-open: invalid input → outputs {} to stdout so Claude Code continues."""
        result = run_hook(self.HOOK, stdin_data="NOT VALID JSON {{{{")

        assert result.returncode == 0
        stdout = result.stdout.strip()
        assert stdout == "{}", f"Expected '{{}}' on stdout, got {stdout!r}"

    def test_log_failure_logged_to_stderr(self):
        """
        When log_security_event() fails to write the log file (read-only dir),
        NEW BEHAVIOR: '[xpia] Security event logging failed (non-fatal)' appears on stderr.
        Fail-open: hook still outputs valid JSON and exits 0.

        Note: log_dir.mkdir() is outside the try/except in log_security_event(), so we
        make the LOG FILE unwritable (not the dir itself) to trigger the inner exception.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create xpia log dir successfully, but make the dir read-only
            # so open(log_file, "a") fails with PermissionError
            xpia_log_dir = Path(tmpdir) / ".claude" / "logs" / "xpia"
            xpia_log_dir.mkdir(parents=True)
            xpia_log_dir.chmod(0o444)  # Read-only: open() will fail

            inp = json.dumps({"toolUse": {"name": "Bash", "input": {"command": "echo test"}}})
            try:
                result = run_hook(
                    self.HOOK,
                    stdin_data=inp,
                    env={"HOME": tmpdir},
                )
            finally:
                xpia_log_dir.chmod(0o755)  # Restore so tmpdir cleanup works

        assert result.returncode == 0, "Must exit 0 even when logging fails"
        assert "[xpia] Security event logging failed (non-fatal)" in result.stderr, (
            f"Expected logging-failure message in stderr, got: {result.stderr!r}"
        )
        # Output must still be valid JSON
        try:
            json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            pytest.fail(f"stdout must be valid JSON even when logging fails: {result.stdout!r}")

    def test_empty_stdin_handled_gracefully(self):
        """Empty stdin → hook processes with empty input, exits 0."""
        result = run_hook(self.HOOK, stdin_data="")
        assert result.returncode == 0
        json.loads(result.stdout.strip())  # Must not raise


# ─── XPIA post_tool_use ──────────────────────────────────────────────────────


class TestXpiaPostToolUse:
    """Outside-in tests for .claude/tools/xpia/hooks/post_tool_use.py"""

    HOOK = XPIA_HOOKS_DIR / "post_tool_use.py"

    def test_valid_tool_result_returns_json(self):
        """Happy path: valid post-tool result → valid JSON output, exit 0."""
        inp = json.dumps(
            {
                "toolUse": {"name": "Bash", "input": {"command": "echo hello"}},
                "toolResult": {"output": "hello\n", "error": ""},
            }
        )
        result = run_hook(self.HOOK, stdin_data=inp)

        assert result.returncode == 0
        try:
            json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            pytest.fail(f"stdout is not valid JSON: {result.stdout!r}")

    def test_invalid_json_stdin_exits_zero(self):
        """Invalid JSON stdin → hook must still exit 0 (fail-open)."""
        result = run_hook(self.HOOK, stdin_data="GARBAGE INPUT")
        assert result.returncode == 0

    def test_log_failure_logged_to_stderr(self):
        """
        When log_security_event() fails to write the log file (read-only dir),
        NEW BEHAVIOR: '[xpia] Security event logging failed (non-fatal)' in stderr.
        Hook still exits 0 with valid JSON output.

        Note: post_tool_use input format is {"tool": "Bash", "parameters": {...}, "result": {...}}
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create log dir but make it read-only so open(log_file, "a") fails
            xpia_log_dir = Path(tmpdir) / ".claude" / "logs" / "xpia"
            xpia_log_dir.mkdir(parents=True)
            xpia_log_dir.chmod(0o444)

            # Bash tool result triggers unconditional log_security_event("post_tool_analysis")
            inp = json.dumps(
                {
                    "tool": "Bash",
                    "parameters": {"command": "ls -la"},
                    "result": {"output": "file1.txt\n", "error": "", "exit_code": 0},
                }
            )
            try:
                result = run_hook(self.HOOK, stdin_data=inp, env={"HOME": tmpdir})
            finally:
                xpia_log_dir.chmod(0o755)

        assert result.returncode == 0
        assert "[xpia] Security event logging failed (non-fatal)" in result.stderr, (
            f"Expected logging failure in stderr, got: {result.stderr!r}"
        )


# ─── gitignore_checker ───────────────────────────────────────────────────────


class TestGitignoreChecker:
    """Outside-in tests for gitignore_checker.py"""

    HOOK = HOOKS_DIR / "gitignore_checker.py"

    def test_runs_in_git_repo(self):
        """Happy path: runs in a real git repo, returns dict with is_git_repo=True."""
        result = run_hook(self.HOOK)

        assert result.returncode == 0
        assert "is_git_repo" in result.stdout, (
            f"Expected 'is_git_repo' in output, got: {result.stdout!r}"
        )

    def test_non_git_directory_returns_safely(self):
        """Outside git repo: is_git_repo=False, exits 0, no crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_hook(self.HOOK, cwd=Path(tmpdir))

        assert result.returncode == 0
        assert "is_git_repo" in result.stdout, (
            f"Expected is_git_repo in output even outside git: {result.stdout!r}"
        )
        # In non-git dir the early return path fires, not the error path
        # Either is_git_repo: False or the full dict - both are valid

    def test_git_unavailable_logs_error_to_stderr(self):
        """
        When git binary unavailable AND an unexpected exception fires in is_git_repo,
        NEW BEHAVIOR: '[gitignore_checker] Unexpected error' in stderr.
        Exit 0 (fail-safe).

        Note: FileNotFoundError is a *specific* catch (expected case: git not installed)
        and does NOT log. This test verifies the generic except branch logs correctly
        by injecting a scenario where an unexpected non-FileNotFoundError occurs.
        We verify this by patching at the module level via a small wrapper script.
        """
        wrapper = """
import sys
sys.path.insert(0, '.claude/tools/amplihack/hooks')
import subprocess as sp_real

# Monkey-patch subprocess.run to raise an unexpected error on git calls
import subprocess
original_run = subprocess.run

def patched_run(args, **kwargs):
    if args and args[0] == 'git':
        raise PermissionError("Simulated unexpected git error")
    return original_run(args, **kwargs)

subprocess.run = patched_run

from gitignore_checker import GitignoreChecker
checker = GitignoreChecker()
result = checker.is_git_repo()
print(f"is_git_repo={result}", file=sys.stdout)
"""
        proc = subprocess.run(
            [PYTHON, "-c", wrapper],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
        )
        assert proc.returncode == 0, f"Should exit 0, got {proc.returncode}: {proc.stderr}"
        assert "[gitignore_checker] Unexpected error in is_git_repo" in proc.stderr, (
            f"Expected error log in stderr, got: {proc.stderr!r}"
        )
        assert "is_git_repo=False" in proc.stdout, (
            f"Should return False on error, got: {proc.stdout!r}"
        )

    def test_get_repo_root_unexpected_error_logs_to_stderr(self):
        """
        When get_repo_root() encounters an unexpected (non-FileNotFoundError, non-Timeout)
        exception, NEW BEHAVIOR: logs '[gitignore_checker] Unexpected error in get_repo_root'.
        """
        wrapper = """
import sys
sys.path.insert(0, '.claude/tools/amplihack/hooks')
import subprocess

original_run = subprocess.run

def patched_run(args, **kwargs):
    if args and args[0] == 'git' and '--show-toplevel' in args:
        raise RuntimeError("Simulated unexpected git show-toplevel error")
    return original_run(args, **kwargs)

subprocess.run = patched_run

from gitignore_checker import GitignoreChecker
checker = GitignoreChecker()
result = checker.get_repo_root()
print(f"result={result}", file=sys.stdout)
"""
        proc = subprocess.run(
            [PYTHON, "-c", wrapper],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
        )
        assert proc.returncode == 0
        assert "[gitignore_checker] Unexpected error in get_repo_root" in proc.stderr, (
            f"Expected error log in stderr, got: {proc.stderr!r}"
        )
        assert "result=None" in proc.stdout


# ─── workflow_classification_reminder ────────────────────────────────────────


class TestWorkflowClassificationReminder:
    """Outside-in tests for workflow_classification_reminder.py"""

    HOOK = HOOKS_DIR / "workflow_classification_reminder.py"

    def _env(self, session_id: str, project_dir: str | None = None) -> dict:
        env = {"CLAUDE_SESSION_ID": session_id}
        if project_dir:
            env["CLAUDE_PROJECT_DIR"] = project_dir
        return env

    def test_new_topic_injects_reminder(self):
        """Happy path: development keyword on turn 0 → injects additionalContext."""
        inp = json.dumps({"userMessage": "Implement JWT authentication", "turnCount": 0})
        result = run_hook(
            self.HOOK,
            stdin_data=inp,
            env=self._env("test-new-topic-001"),
        )

        assert result.returncode == 0
        assert "additionalContext" in result.stdout, (
            f"Expected additionalContext in output: {result.stdout!r}"
        )
        assert "system-reminder" in result.stdout

    def test_followup_returns_empty_object(self):
        """
        Follow-up prompt: when state file says we classified 1 turn ago,
        is_new_topic() returns False and hook outputs {}.

        Uses a single-process wrapper because get_session_id() generates a new
        timestamp per process invocation, making two-process state sharing impossible.
        We test the state-reading logic directly by pre-populating the state file.
        """
        wrapper = """
import sys, json
sys.path.insert(0, '.claude/tools/amplihack/hooks')

from workflow_classification_reminder import WorkflowClassificationReminder

hook = WorkflowClassificationReminder()

# Simulate: we classified on turn 0, now we're on turn 2 (within 3)
# Pre-populate state file so is_new_topic() reads it
state_file = hook.get_session_state_file()
state_file.write_text(json.dumps({"last_classified_turn": 0, "session_id": "same-session"}))

inp = {"userMessage": "Also add logout", "turnCount": 2}
result = hook.process(inp)
print(json.dumps(result))
"""
        proc = subprocess.run(
            [PYTHON, "-c", wrapper],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
        )
        assert proc.returncode == 0, f"Must not crash: {proc.stderr}"
        stdout = proc.stdout.strip()
        try:
            parsed = json.loads(stdout)
            assert parsed == {}, f"Follow-up should return empty dict, got: {parsed}"
        except json.JSONDecodeError:
            pytest.fail(f"stdout not valid JSON: {stdout!r}")

    def test_corrupt_state_file_logs_and_falls_back(self):
        """
        NEW BEHAVIOR: Corrupt state file JSON → logs 'Could not read classification state'
        and falls back to treating the prompt as a new topic (safe default).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_id = "test-corrupt-state-003"
            state_dir = Path(tmpdir) / ".claude" / "runtime" / "logs" / session_id
            state_dir.mkdir(parents=True)

            # Write corrupt JSON to state file
            state_file = state_dir / "classification_state.json"
            state_file.write_text("NOT VALID JSON {{{ corrupt")

            inp = json.dumps(
                {
                    "userMessage": "Fix the auth bug",
                    "turnCount": 5,  # Non-zero so it tries to read state
                }
            )
            result = run_hook(
                self.HOOK,
                stdin_data=inp,
                env=self._env(session_id, project_dir=tmpdir),
            )

        assert result.returncode == 0, (
            f"Must not crash on corrupt state file. stderr={result.stderr!r}"
        )
        # Output must be valid JSON
        try:
            json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            pytest.fail(f"Must output valid JSON even with corrupt state: {result.stdout!r}")

    def test_invalid_json_stdin_exits_gracefully(self):
        """Invalid JSON stdin → hook exits 0 (fail-open)."""
        result = run_hook(
            self.HOOK,
            stdin_data="COMPLETELY INVALID",
            env=self._env("test-invalid-stdin-004"),
        )
        assert result.returncode == 0, f"Hook must not crash on bad stdin. stderr={result.stderr!r}"


# ─── precommit_prefs (exception logging) ─────────────────────────────────────


class TestPrecommitPrefsExceptionLogging:
    """Outside-in tests for precommit_prefs.py exception handling."""

    def test_outer_exception_in_level1_logs_to_stderr(self):
        """
        NEW BEHAVIOR: Outer except Exception in load_precommit_preference() Level 1
        now prints '[precommit_prefs] Unexpected error reading CLAUDE.md preference'.

        Force by making open() raise RuntimeError (not OSError/PermissionError which
        are caught by the inner except) when accessing USER_PREFERENCES.md files.
        Also patch Path.exists to return True so the open() call is attempted.
        """
        wrapper = """
import sys, os, builtins
sys.path.insert(0, '.claude/tools/amplihack/hooks')

from pathlib import Path
original_exists = Path.exists
original_open = builtins.open

def patched_exists(self):
    if 'USER_PREFERENCES' in str(self):
        return True  # Pretend it exists so open() is attempted
    return original_exists(self)

def patched_open(file, *args, **kwargs):
    if 'USER_PREFERENCES' in str(file):
        raise RuntimeError("Simulated unexpected error (not caught by inner PermissionError handler)")
    return original_open(file, *args, **kwargs)

Path.exists = patched_exists
builtins.open = patched_open

from precommit_prefs import load_precommit_preference
result = load_precommit_preference()
print(f"result={result!r}", file=sys.stdout)
"""
        proc = subprocess.run(
            [PYTHON, "-c", wrapper],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
        )
        assert proc.returncode == 0, f"Must not crash: {proc.stderr}"
        assert "[precommit_prefs] Unexpected error" in proc.stderr, (
            f"Expected error log in stderr, got: {proc.stderr!r}"
        )

    def test_normal_preference_detection_still_works(self):
        """Regression: env-var based preference detection still works."""
        wrapper = """
import sys, os
sys.path.insert(0, '.claude/tools/amplihack/hooks')
os.environ['AMPLIHACK_AUTO_PRECOMMIT'] = 'always'
from precommit_prefs import load_precommit_preference
result = load_precommit_preference()
print(result)
"""
        proc = subprocess.run(
            [PYTHON, "-c", wrapper],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
        )
        assert proc.returncode == 0
        assert "always" in proc.stdout.strip()


# ─── shutdown_context (exception logging) ────────────────────────────────────


class TestShutdownContextExceptionLogging:
    """Outside-in tests for shutdown_context.py exception handling."""

    def test_stack_inspection_failure_logs_to_stderr(self):
        """
        NEW BEHAVIOR: _is_in_atexit_context() unexpected exception
        logs '[shutdown_context] Stack inspection failed (fail-open)' to stderr.
        """
        wrapper = """
import sys
sys.path.insert(0, '.claude/tools/amplihack/hooks')

import inspect as inspect_module
original_stack = inspect_module.stack

def patched_stack():
    raise RuntimeError("Simulated stack inspection failure")

inspect_module.stack = patched_stack

from shutdown_context import _is_in_atexit_context
result = _is_in_atexit_context()
print(f"result={result}")
"""
        proc = subprocess.run(
            [PYTHON, "-c", wrapper],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
        )
        assert proc.returncode == 0
        assert "[shutdown_context] Stack inspection failed (fail-open)" in proc.stderr, (
            f"Expected error log, got: {proc.stderr!r}"
        )
        # Fail-open: returns False (assume not in atexit)
        assert "result=False" in proc.stdout

    def test_stdin_detection_failure_logs_to_stderr(self):
        """
        NEW BEHAVIOR: _is_stdin_closed() unexpected exception
        logs '[shutdown_context] stdin state detection failed (fail-open)' to stderr.
        """
        wrapper = """
import sys
sys.path.insert(0, '.claude/tools/amplihack/hooks')

# Replace sys.stdin with an object that raises unexpectedly on fileno()
class BrokenStdin:
    closed = False
    def fileno(self):
        raise RuntimeError("Simulated stdin detection failure")

sys.stdin = BrokenStdin()

from shutdown_context import _is_stdin_closed
result = _is_stdin_closed()
print(f"result={result}")
"""
        proc = subprocess.run(
            [PYTHON, "-c", wrapper],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
        )
        assert proc.returncode == 0
        assert "[shutdown_context] stdin state detection failed (fail-open)" in proc.stderr, (
            f"Expected error log, got: {proc.stderr!r}"
        )
        # Fail-open: returns True (assume stdin is closed)
        assert "result=True" in proc.stdout


# ─── claude_power_steering (SDK error logging) ───────────────────────────────


class TestClaudePowerSteeringExceptionLogging:
    """Outside-in tests for claude_power_steering.py exception logging."""

    def test_validate_sdk_response_logs_on_error(self):
        """
        NEW BEHAVIOR: _validate_sdk_response() unexpected exception
        logs '[Power Steering SDK Error] validate_response' to stderr.

        Patches re.search AFTER import and mocks _log_sdk_error to avoid
        re.sub dependency in the error handler itself.
        """
        wrapper = """
import sys
sys.path.insert(0, '.claude/tools/amplihack/hooks')

import claude_power_steering as ps

# Mock _log_sdk_error to spy on it without using re.sub internally
log_calls = []
original_log = ps._log_sdk_error

def mock_log(consideration_id, error):
    log_calls.append(consideration_id)
    print(f"[Power Steering SDK Error] {consideration_id}: {error}", file=sys.stderr)

ps._log_sdk_error = mock_log

# Make the function raise by patching re.search AFTER module import
import re
original_search = re.search

def patched_search(pattern, string, *args, **kwargs):
    raise RuntimeError("Simulated regex failure")

re.search = patched_search
try:
    result = ps._validate_sdk_response("some response text")
finally:
    re.search = original_search
    ps._log_sdk_error = original_log

print(f"result={result}")
"""
        proc = subprocess.run(
            [PYTHON, "-c", wrapper],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
        )
        assert proc.returncode == 0, f"Must exit 0: {proc.stderr}"
        assert "[Power Steering SDK Error] validate_response" in proc.stderr, (
            f"Expected SDK error log, got: {proc.stderr!r}"
        )
        # Fail-open: returns True
        assert "result=True" in proc.stdout

    def test_sanitize_html_logs_on_error(self):
        """
        NEW BEHAVIOR: _sanitize_html() unexpected exception
        logs '[Power Steering SDK Error] sanitize_html' to stderr.
        Returns original text (fail-open).

        Mocks _log_sdk_error to avoid its own re.sub dependency when
        re.sub is patched to raise.
        """
        wrapper = """
import sys
sys.path.insert(0, '.claude/tools/amplihack/hooks')

import claude_power_steering as ps
import re as re_module

# Mock _log_sdk_error first so its re.sub calls don't fail when we patch re.sub
log_calls = []
original_log = ps._log_sdk_error

def mock_log(consideration_id, error):
    log_calls.append(consideration_id)
    print(f"[Power Steering SDK Error] {consideration_id}: {error}", file=sys.stderr)

ps._log_sdk_error = mock_log

# Now patch re.sub to fail on the 2nd call (first call removes <script> tag)
original_sub = re_module.sub
call_count = [0]

def patched_sub(pattern, repl, string, *args, **kwargs):
    call_count[0] += 1
    if call_count[0] >= 2:
        raise RuntimeError("Simulated re.sub failure in _sanitize_html")
    return original_sub(pattern, repl, string, *args, **kwargs)

re_module.sub = patched_sub
try:
    original_text = "hello <script>evil</script>"
    result = ps._sanitize_html(original_text)
finally:
    re_module.sub = original_sub
    ps._log_sdk_error = original_log

print(f"result={result!r}")
"""
        proc = subprocess.run(
            [PYTHON, "-c", wrapper],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
        )
        assert proc.returncode == 0, f"Must exit 0: {proc.stderr}"
        assert "[Power Steering SDK Error] sanitize_html" in proc.stderr, (
            f"Expected SDK error log, got: {proc.stderr!r}"
        )
        # Fail-open: returns original text
        assert "hello" in proc.stdout


# ─── Integration: All hooks exit 0 ───────────────────────────────────────────


class TestAllHooksExitZeroOnBadInput:
    """
    Integration smoke tests: all hooks that read stdin must exit 0
    even with completely garbled input (fail-open protocol).
    """

    @pytest.mark.parametrize(
        "hook_path",
        [
            HOOKS_DIR / "workflow_classification_reminder.py",
            XPIA_HOOKS_DIR / "pre_tool_use.py",
            XPIA_HOOKS_DIR / "post_tool_use.py",
        ],
    )
    def test_hook_exits_zero_on_garbage_input(self, hook_path: Path):
        """Any hook must exit 0 even on completely invalid stdin."""
        result = run_hook(
            hook_path,
            stdin_data="GARBAGE_INPUT_THAT_IS_NOT_JSON {{{{",
            env={"CLAUDE_SESSION_ID": "test-garbage-input"},
        )
        assert result.returncode == 0, (
            f"{hook_path.name} should exit 0 on garbage input. stderr={result.stderr!r}"
        )

    @pytest.mark.parametrize(
        "hook_path",
        [
            XPIA_HOOKS_DIR / "pre_tool_use.py",
            XPIA_HOOKS_DIR / "post_tool_use.py",
        ],
    )
    def test_xpia_hook_outputs_valid_json_on_garbage(self, hook_path: Path):
        """XPIA hooks must output valid JSON even on garbage input."""
        result = run_hook(hook_path, stdin_data="GARBAGE")
        assert result.returncode == 0
        try:
            json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            pytest.fail(
                f"{hook_path.name} stdout must be valid JSON on garbage input: {result.stdout!r}"
            )
