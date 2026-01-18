#!/usr/bin/env python3
"""
TDD Tests for Stop Hook Integration (INTEGRATION TESTS - 30%)

Tests the complete stop hook flow with shutdown context, verifying that
hooks exit quickly during cleanup while functioning normally otherwise.

Testing Philosophy:
- Ruthlessly Simple: Focus on critical integration paths
- Zero-BS: All tests work, no stubs
- Fail-Open: Shutdown always allows clean exit

Test Coverage:
- Stop hook exits quickly during cleanup
- Stop hook works normally without cleanup
- Multiple hooks during cleanup
- Signal handling during cleanup
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def stop_hook_script(tmp_path):
    """Create a minimal stop hook script for testing.

    This simulates the actual stop hook behavior with shutdown detection.
    """
    script_path = tmp_path / "stop_hook_test.py"
    script_content = """#!/usr/bin/env python3
import json
import os
import sys

# Simulate stop hook behavior
if os.environ.get("AMPLIHACK_SHUTDOWN_IN_PROGRESS") == "1":
    # During shutdown: return immediately without reading stdin
    json.dump({}, sys.stdout)
    sys.stdout.write("\\n")
    sys.exit(0)

# Normal operation: read stdin and process
input_data = sys.stdin.read()
if input_data.strip():
    data = json.loads(input_data)
    # Stop hook decision logic here
    json.dump({}, sys.stdout)
else:
    json.dump({}, sys.stdout)

sys.stdout.write("\\n")
"""
    script_path.write_text(script_content)
    script_path.chmod(0o755)
    return script_path


# =============================================================================
# INTEGRATION TESTS - Stop Hook Cleanup Flow
# =============================================================================


class TestStopHookDuringCleanup:
    """Integration tests for stop hook during cleanup/shutdown."""

    def test_stop_hook_exits_within_one_second_during_shutdown(self, stop_hook_script):
        """Stop hook should exit in <1s when AMPLIHACK_SHUTDOWN_IN_PROGRESS=1"""
        # ARRANGE
        env = os.environ.copy()
        env["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        # ACT
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, str(stop_hook_script)],
            input='{"conversation": []}',
            capture_output=True,
            text=True,
            timeout=2,  # Fail if takes longer than 2s
            env=env,
        )
        elapsed = time.time() - start_time

        # ASSERT
        assert result.returncode == 0, f"Hook should exit cleanly: {result.stderr}"
        assert elapsed < 1.0, f"Hook took {elapsed:.2f}s, should be <1.0s"
        assert result.stdout.strip() == "{}", "Should return empty response"

    def test_stop_hook_does_not_read_stdin_during_shutdown(self, stop_hook_script):
        """Stop hook should not wait for stdin during shutdown"""
        # ARRANGE
        env = os.environ.copy()
        env["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        # ACT - Don't provide stdin input
        result = subprocess.run(
            [sys.executable, str(stop_hook_script)],
            stdin=subprocess.DEVNULL,  # No input provided
            capture_output=True,
            text=True,
            timeout=2,
            env=env,
        )

        # ASSERT
        assert result.returncode == 0, "Should exit even without stdin during shutdown"
        assert result.stdout.strip() == "{}", "Should return empty response"

    def test_stop_hook_multiple_rapid_calls_during_shutdown(self, stop_hook_script):
        """Multiple stop hook calls during shutdown should all exit quickly"""
        # ARRANGE
        env = os.environ.copy()
        env["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        # ACT - Call hook 5 times rapidly
        start_time = time.time()
        for _ in range(5):
            result = subprocess.run(
                [sys.executable, str(stop_hook_script)],
                input='{"conversation": []}',
                capture_output=True,
                text=True,
                timeout=2,
                env=env,
            )
            assert result.returncode == 0

        elapsed = time.time() - start_time

        # ASSERT
        assert elapsed < 2.0, f"5 hook calls took {elapsed:.2f}s, should be <2.0s total"


# =============================================================================
# INTEGRATION TESTS - Stop Hook Normal Operation
# =============================================================================


class TestStopHookNormalOperation:
    """Integration tests for stop hook during normal operation."""

    def test_stop_hook_processes_input_normally(self, stop_hook_script):
        """Stop hook should process input during normal operation"""
        # ARRANGE - ensure NOT shutting down
        env = os.environ.copy()
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in env:
            del env["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        input_data = json.dumps({"conversation": [{"role": "user", "content": "Test"}]})

        # ACT
        result = subprocess.run(
            [sys.executable, str(stop_hook_script)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )

        # ASSERT
        assert result.returncode == 0
        output = json.loads(result.stdout.strip())
        assert isinstance(output, dict), "Should return valid JSON response"

    def test_stop_hook_waits_for_stdin_normally(self, stop_hook_script):
        """Stop hook should wait for stdin during normal operation"""
        # ARRANGE - ensure NOT shutting down
        env = os.environ.copy()
        if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in env:
            del env["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]

        # ACT - Provide stdin with slight delay
        proc = subprocess.Popen(
            [sys.executable, str(stop_hook_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        time.sleep(0.1)  # Simulate slight delay
        stdout, stderr = proc.communicate(input='{"conversation": []}', timeout=5)

        # ASSERT
        assert proc.returncode == 0, f"Should complete successfully: {stderr}"
        assert stdout.strip() == "{}", "Should return valid response"


# =============================================================================
# INTEGRATION TESTS - Multiple Hooks During Cleanup
# =============================================================================


class TestMultipleHooksDuringCleanup:
    """Integration tests for multiple hooks executing during cleanup."""

    def test_multiple_hooks_all_exit_quickly_during_shutdown(self, stop_hook_script, tmp_path):
        """All hooks should exit quickly when shutdown is in progress"""
        # ARRANGE - Create 3 hook scripts
        hooks = [stop_hook_script]
        for i in range(2):
            hook_path = tmp_path / f"hook_{i}.py"
            hook_path.write_text(stop_hook_script.read_text())
            hook_path.chmod(0o755)
            hooks.append(hook_path)

        env = os.environ.copy()
        env["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        # ACT - Run all hooks concurrently
        import concurrent.futures

        start_time = time.time()

        def run_hook(hook_path):
            return subprocess.run(
                [sys.executable, str(hook_path)],
                input='{"conversation": []}',
                capture_output=True,
                text=True,
                timeout=2,
                env=env,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(run_hook, hooks))

        elapsed = time.time() - start_time

        # ASSERT
        for result in results:
            assert result.returncode == 0, "All hooks should exit cleanly"

        assert elapsed < 1.5, f"3 hooks took {elapsed:.2f}s, should be <1.5s (concurrent)"


# =============================================================================
# INTEGRATION TESTS - Signal Handling During Cleanup
# =============================================================================


class TestSignalHandlingDuringCleanup:
    """Integration tests for signal handling during cleanup."""

    @pytest.mark.skipif(sys.platform == "win32", reason="SIGTERM not available on Windows")
    def test_hook_exits_cleanly_on_sigterm_during_shutdown(self, stop_hook_script):
        """Hook should exit cleanly when receiving SIGTERM during shutdown"""
        # ARRANGE
        env = os.environ.copy()
        env["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        # ACT - Start hook process
        proc = subprocess.Popen(
            [sys.executable, str(stop_hook_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        time.sleep(0.1)  # Let it start

        # Send SIGTERM
        proc.send_signal(signal.SIGTERM)

        try:
            stdout, stderr = proc.communicate(timeout=1)
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("Hook did not exit within 1s after SIGTERM")

        # ASSERT
        assert returncode in (
            0,
            -signal.SIGTERM,
        ), "Should exit cleanly on SIGTERM"

    @pytest.mark.skipif(sys.platform == "win32", reason="SIGINT not available on Windows")
    def test_hook_exits_cleanly_on_sigint_during_shutdown(self, stop_hook_script):
        """Hook should exit cleanly when receiving SIGINT (Ctrl-C) during shutdown"""
        # ARRANGE
        env = os.environ.copy()
        env["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        # ACT
        proc = subprocess.Popen(
            [sys.executable, str(stop_hook_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        time.sleep(0.1)

        # Send SIGINT (Ctrl-C)
        proc.send_signal(signal.SIGINT)

        try:
            stdout, stderr = proc.communicate(timeout=1)
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("Hook did not exit within 1s after SIGINT")

        # ASSERT
        assert returncode in (0, -signal.SIGINT), "Should exit cleanly on SIGINT"


# =============================================================================
# INTEGRATION TESTS - Edge Cases
# =============================================================================


class TestStopHookEdgeCases:
    """Integration tests for stop hook edge cases."""

    def test_hook_handles_stdin_closed_during_shutdown(self, stop_hook_script):
        """Hook should handle stdin being closed during shutdown"""
        # ARRANGE
        env = os.environ.copy()
        env["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        # ACT - Close stdin immediately
        result = subprocess.run(
            [sys.executable, str(stop_hook_script)],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=2,
            env=env,
        )

        # ASSERT
        assert result.returncode == 0, "Should handle closed stdin during shutdown"

    def test_hook_handles_stdout_closed_during_shutdown(self, stop_hook_script):
        """Hook should handle stdout being closed during shutdown"""
        # ARRANGE
        env = os.environ.copy()
        env["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

        # ACT - Close stdout (simulates pipe closure)
        result = subprocess.run(
            [sys.executable, str(stop_hook_script)],
            input='{"conversation": []}',
            stdout=subprocess.DEVNULL,  # Discard output
            stderr=subprocess.PIPE,
            text=True,
            timeout=2,
            env=env,
        )

        # ASSERT
        assert result.returncode == 0, "Should handle closed stdout during shutdown"


# =============================================================================
# TEST CONFIGURATION
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_env_var():
    """Ensure AMPLIHACK_SHUTDOWN_IN_PROGRESS is cleaned up after each test."""
    yield
    if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
        del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]


def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


# Import json at module level for stop hook tests
import json
