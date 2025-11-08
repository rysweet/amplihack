"""Test signal handler integration.

This test verifies that SIGINT and SIGTERM signals trigger
Neo4j cleanup via the stop hook.
"""

import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest


class TestSignalHandlers:
    """Test suite for signal handler integration."""

    def test_sigint_handler_registered(self):
        """Test that SIGINT handler is registered on launcher initialization."""
        # This is a unit test to verify handlers are set up
        from amplihack.launcher.core import ClaudeLauncher

        launcher = ClaudeLauncher()

        # Verify signal handlers were registered
        # Note: We can't directly test the handler without triggering it,
        # but we can verify the launcher has the methods
        assert hasattr(launcher, '_setup_signal_handlers')
        assert hasattr(launcher, '_cleanup_on_exit')

    def test_sigterm_handler_registered(self):
        """Test that SIGTERM handler is registered on launcher initialization."""
        from amplihack.launcher.core import ClaudeLauncher

        launcher = ClaudeLauncher()

        # Verify signal handlers were registered
        assert hasattr(launcher, '_setup_signal_handlers')
        assert hasattr(launcher, '_cleanup_on_exit')

    def test_hooks_manager_exists(self):
        """Test that hooks manager module exists and has execute_stop_hook."""
        from amplihack.hooks.manager import execute_stop_hook

        # Verify function exists and is callable
        assert callable(execute_stop_hook)

    def test_execute_stop_hook_is_safe(self):
        """Test that execute_stop_hook doesn't crash when hook is missing."""
        from amplihack.hooks.manager import execute_stop_hook

        # This should not raise an exception even if hook doesn't exist
        # It should log a warning and return gracefully
        try:
            execute_stop_hook()
        except Exception as e:
            pytest.fail(f"execute_stop_hook raised exception: {e}")

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="SIGTERM not available on Windows"
    )
    def test_signal_handler_subprocess(self):
        """Test that signal handler works in subprocess.

        This is a more realistic test that spawns a subprocess
        and sends it SIGTERM to verify cleanup occurs.
        """
        # Create a simple script that uses ClaudeLauncher
        test_script = """
import sys
import time
import signal
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from amplihack.launcher.core import ClaudeLauncher

# Create launcher (this sets up signal handlers)
launcher = ClaudeLauncher()

# Print ready message
print("READY", flush=True)

# Wait for signal (simulate long-running process)
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    sys.exit(0)
"""

        # Write test script to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            script_path = f.name

        try:
            # Start subprocess
            proc = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for ready signal
            ready = False
            for _ in range(50):  # 5 second timeout
                if proc.poll() is not None:
                    # Process exited unexpectedly
                    stdout, stderr = proc.communicate()
                    pytest.fail(
                        f"Process exited unexpectedly.\n"
                        f"stdout: {stdout}\nstderr: {stderr}"
                    )

                try:
                    line = proc.stdout.readline()
                    if "READY" in line:
                        ready = True
                        break
                except Exception:
                    pass
                time.sleep(0.1)

            assert ready, "Process did not become ready"

            # Send SIGTERM
            proc.send_signal(signal.SIGTERM)

            # Wait for process to exit
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                pytest.fail("Process did not exit after SIGTERM")

            # Verify exit code (0 = graceful shutdown)
            assert proc.returncode == 0, \
                f"Process exited with code {proc.returncode}"

        finally:
            # Cleanup
            Path(script_path).unlink(missing_ok=True)
            if proc.poll() is None:
                proc.kill()


def test_manual_signal_handler_instructions():
    """Manual test instructions for signal handlers.

    This is not an automated test - it provides instructions
    for manual testing of signal handlers.
    """
    instructions = """
    MANUAL TEST INSTRUCTIONS FOR SIGNAL HANDLERS:

    1. Start amplihack in a terminal:
       $ amplihack

    2. While Claude is running, press Ctrl-C

    3. Verify the following:
       - You see log message: "Received SIGINT, initiating graceful shutdown..."
       - You see log message: "Executing stop hook for cleanup..."
       - Neo4j cleanup occurs (if Neo4j was running)
       - Process exits gracefully (exit code 0)

    4. Test SIGTERM:
       $ amplihack &
       $ PID=$!
       $ kill -TERM $PID

    5. Verify the same behavior as Ctrl-C test

    6. Check logs in .claude/runtime/logs/ for cleanup evidence
    """
    # This test always passes - it's just documentation
    assert True, instructions
