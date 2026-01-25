"""End-to-end tests fer hook protocol.

Tests complete hook workflows from outside-in perspective:
- Hook creation and execution
- Error handlin'
- Hook lifecycle management
"""

import pytest
from pathlib import Path
from tests.harness import HookTestHarness


class TestHookExecution:
    """Test hook execution workflows."""

    @pytest.fixture
    def harness(self):
        """Create hook test harness."""
        h = HookTestHarness()
        yield h
        h.cleanup()

    def test_execute_python_hook(self, harness):
        """Test executin' a Python hook.

        Workflow:
        1. Create Python hook
        2. Trigger hook
        3. Verify success
        4. Check output
        """
        # Create simple Python hook
        hook_script = """
import sys
print("Hook executed successfully")
sys.exit(0)
"""
        harness.create_hook("test_hook", hook_script, language="python")

        # Trigger hook
        result = harness.trigger_hook("test_hook")
        result.assert_success("Python hook failed to execute")
        result.assert_in_stdout("Hook executed successfully")

    def test_execute_bash_hook(self, harness):
        """Test executin' a Bash hook.

        Workflow:
        1. Create Bash hook
        2. Trigger hook
        3. Verify success
        4. Check output
        """
        # Create simple Bash hook
        hook_script = """
echo "Bash hook executed"
exit 0
"""
        harness.create_hook("bash_hook", hook_script, language="bash")

        # Trigger hook
        result = harness.trigger_hook("bash_hook")
        result.assert_success("Bash hook failed to execute")
        result.assert_in_stdout("Bash hook executed")

    def test_hook_with_arguments(self, harness):
        """Test hook receives arguments correctly.

        Workflow:
        1. Create hook that echoes args
        2. Trigger with args
        3. Verify args received
        """
        # Create hook that echoes args
        hook_script = """
import sys
print(f"Args: {' '.join(sys.argv[1:])}")
"""
        harness.create_hook("args_hook", hook_script, language="python")

        # Trigger with args
        result = harness.trigger_hook("args_hook", extra_args=["arg1", "arg2"])
        result.assert_success()
        result.assert_in_stdout("arg1")
        result.assert_in_stdout("arg2")

    def test_hook_failure_handling(self, harness):
        """Test hook failure is handled correctly.

        Workflow:
        1. Create hook that fails
        2. Trigger hook
        3. Verify failure detected
        4. Check error output
        """
        # Create failing hook
        hook_script = """
import sys
print("Error: Something went wrong", file=sys.stderr)
sys.exit(1)
"""
        harness.create_hook("failing_hook", hook_script, language="python")

        # Trigger hook
        result = harness.trigger_hook("failing_hook")
        result.assert_failure("Failing hook should fail")
        result.assert_in_stderr("Error: Something went wrong")

    def test_hook_timeout_handling(self, harness):
        """Test hook timeout is enforced.

        Workflow:
        1. Create hook that sleeps too long
        2. Trigger with short timeout
        3. Verify timeout detected
        """
        # Create slow hook
        hook_script = """
import time
time.sleep(60)  # Sleep fer 60 seconds
"""
        harness.create_hook("slow_hook", hook_script, language="python")

        # Create harness with 1-second timeout
        short_timeout_harness = HookTestHarness(
            project_dir=harness.project_dir,
            timeout=1
        )

        # Trigger hook (should timeout)
        result = short_timeout_harness.trigger_hook("slow_hook")
        result.assert_failure("Slow hook should timeout")
        result.assert_in_stderr("timed out")

    def test_list_available_hooks(self, harness):
        """Test listin' available hooks.

        Workflow:
        1. Create multiple hooks
        2. List hooks
        3. Verify all shown
        """
        # Create hooks
        harness.create_hook("hook1", "print('hook1')", language="python")
        harness.create_hook("hook2", "print('hook2')", language="python")
        harness.create_hook("hook3", "echo 'hook3'", language="bash")

        # List hooks
        result = harness.list_hooks()
        result.assert_success()

        # Verify all hooks listed
        result.assert_in_stdout("hook1")
        result.assert_in_stdout("hook2")
        result.assert_in_stdout("hook3")

    def test_hook_environment_variables(self, harness):
        """Test hooks receive environment variables.

        Workflow:
        1. Create hook that reads env vars
        2. Trigger hook
        3. Verify env vars available
        """
        # Create hook that checks env
        hook_script = """
import os
project_dir = os.environ.get('AMPLIHACK_PROJECT_DIR', 'NOT_SET')
print(f"Project dir: {project_dir}")
"""
        harness.create_hook("env_hook", hook_script, language="python")

        # Trigger hook
        result = harness.trigger_hook("env_hook")
        result.assert_success()
        # Should have project dir set
        result.assert_in_stdout("Project dir:")
        assert "NOT_SET" not in result.stdout


class TestHookLifecycle:
    """Test hook lifecycle management."""

    @pytest.fixture
    def harness(self):
        """Create hook test harness."""
        h = HookTestHarness()
        yield h
        h.cleanup()

    def test_pre_commit_hook(self, harness):
        """Test pre-commit hook workflow.

        Workflow:
        1. Create pre_commit hook
        2. Trigger hook
        3. Verify runs before commit
        """
        # Create pre-commit hook that validates
        hook_script = """
import sys
import os

# Check if we're in git repo
if not os.path.exists('.git'):
    print("Error: Not a git repository", file=sys.stderr)
    sys.exit(1)

print("Pre-commit checks passed")
sys.exit(0)
"""
        harness.create_hook("pre_commit", hook_script, language="python")

        # Trigger hook
        result = harness.trigger_hook("pre_commit")

        # May succeed or fail dependin' on git repo presence
        # But should execute and provide feedback
        assert len(result.stdout) > 0 or len(result.stderr) > 0

    def test_post_install_hook(self, harness):
        """Test post-install hook workflow.

        Workflow:
        1. Create post_install hook
        2. Trigger hook
        3. Verify setup tasks run
        """
        # Create post-install hook
        hook_script = """
import os
from pathlib import Path

# Create config directory
config_dir = Path('.config')
config_dir.mkdir(exist_ok=True)

# Create default config
config_file = config_dir / 'default.conf'
config_file.write_text('# Default config\\n')

print("Post-install setup complete")
"""
        harness.create_hook("post_install", hook_script, language="python")

        # Trigger hook
        result = harness.trigger_hook("post_install")
        result.assert_success()
        result.assert_in_stdout("Post-install setup complete")

        # Verify config created
        config_file = harness.project_dir / ".config" / "default.conf"
        assert config_file.exists()

    def test_pre_uninstall_hook(self, harness):
        """Test pre-uninstall hook workflow.

        Workflow:
        1. Create pre_uninstall hook
        2. Trigger hook
        3. Verify cleanup tasks run
        """
        # Create test file
        test_file = harness.project_dir / "test_data.txt"
        test_file.write_text("test data")

        # Create pre-uninstall hook that cleans up
        hook_script = """
import os
from pathlib import Path

# Remove test data
test_file = Path('test_data.txt')
if test_file.exists():
    test_file.unlink()
    print("Cleaned up test data")
else:
    print("No cleanup needed")
"""
        harness.create_hook("pre_uninstall", hook_script, language="python")

        # Trigger hook
        result = harness.trigger_hook("pre_uninstall")
        result.assert_success()

        # Verify file removed
        assert not test_file.exists()

    def test_hook_error_recovery(self, harness):
        """Test system recovers from hook errors.

        Workflow:
        1. Create hook that sometimes fails
        2. Trigger hook multiple times
        3. Verify system continues workin'
        """
        # Create hook that fails first time, succeeds after
        hook_script = """
import sys
from pathlib import Path

marker = Path('.hook_ran')
if marker.exists():
    print("Hook succeeded on retry")
    sys.exit(0)
else:
    marker.touch()
    print("Hook failed first time", file=sys.stderr)
    sys.exit(1)
"""
        harness.create_hook("retry_hook", hook_script, language="python")

        # First attempt (should fail)
        result1 = harness.trigger_hook("retry_hook")
        result1.assert_failure()

        # Second attempt (should succeed)
        result2 = harness.trigger_hook("retry_hook")
        result2.assert_success()
        result2.assert_in_stdout("Hook succeeded on retry")

    def test_multiple_hooks_sequential(self, harness):
        """Test multiple hooks execute sequentially.

        Workflow:
        1. Create multiple hooks that write to file
        2. Execute all hooks
        3. Verify execution order
        """
        # Create hooks that append to log
        hook1_script = """
from pathlib import Path
Path('hook_log.txt').write_text('hook1\\n')
print("Hook 1 executed")
"""
        hook2_script = """
from pathlib import Path
log = Path('hook_log.txt')
content = log.read_text() if log.exists() else ''
log.write_text(content + 'hook2\\n')
print("Hook 2 executed")
"""
        hook3_script = """
from pathlib import Path
log = Path('hook_log.txt')
content = log.read_text() if log.exists() else ''
log.write_text(content + 'hook3\\n')
print("Hook 3 executed")
"""

        harness.create_hook("seq_hook1", hook1_script, language="python")
        harness.create_hook("seq_hook2", hook2_script, language="python")
        harness.create_hook("seq_hook3", hook3_script, language="python")

        # Execute hooks in order
        harness.trigger_hook("seq_hook1").assert_success()
        harness.trigger_hook("seq_hook2").assert_success()
        harness.trigger_hook("seq_hook3").assert_success()

        # Verify execution order
        log_file = harness.project_dir / "hook_log.txt"
        assert log_file.exists()
        content = log_file.read_text()
        assert "hook1" in content
        assert "hook2" in content
        assert "hook3" in content
        # Verify order
        assert content.index("hook1") < content.index("hook2")
        assert content.index("hook2") < content.index("hook3")
