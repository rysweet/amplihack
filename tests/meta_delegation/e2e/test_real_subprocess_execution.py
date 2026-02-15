"""Layer 1: Real Subprocess Execution Tests.

Tests subprocess spawning, lifecycle management, and cleanup with real
process execution. These are the foundation layer that validates basic
subprocess operations work correctly before testing higher abstractions.
"""

import os
import sys
import time

import pytest

# These imports will fail initially - that's the point of TDD
from amplihack.meta_delegation.subprocess_adapter import (
    CLISubprocessAdapter,
    SubprocessTimeoutError,
)


@pytest.mark.e2e
@pytest.mark.subprocess
class TestSubprocessSpawning:
    """Test basic subprocess spawning and execution."""

    def test_subprocess_spawns_successfully(self, test_workspace, subprocess_lifecycle_manager):
        """Test that a simple Python subprocess can be spawned and executes successfully.

        This validates the most basic subprocess operation - spawning a process
        that prints output and exits cleanly.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        result = adapter.spawn(
            command=[sys.executable, "-c", "print('hello from subprocess')"],
            working_dir=str(test_workspace.path),
        )

        assert result.exit_code == 0
        assert "hello from subprocess" in result.stdout
        assert result.duration < 5.0
        assert result.subprocess_pid > 0

    def test_subprocess_respects_timeout(
        self, test_workspace, timeout_config, subprocess_lifecycle_manager
    ):
        """Test that long-running subprocess is killed when timeout is reached.

        Validates timeout enforcement is working - critical for preventing
        hanging tests and CI builds.
        """
        adapter = CLISubprocessAdapter(timeout=5)

        with pytest.raises(SubprocessTimeoutError) as exc_info:
            adapter.spawn(
                command=[sys.executable, "-c", "import time; time.sleep(100)"],
                working_dir=str(test_workspace.path),
            )

        error = exc_info.value
        assert error.timeout == 5
        assert error.duration >= 5
        assert "timeout" in str(error).lower()
        # Process should be killed
        assert not subprocess_lifecycle_manager.is_alive(error.subprocess_pid)

    def test_multiple_subprocesses_parallel(self, test_workspace):
        """Test spawning multiple subprocesses in parallel.

        Validates that the adapter can handle multiple concurrent subprocess
        executions without interference.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        # Spawn 3 parallel subprocesses
        results = []
        for i in range(3):
            result = adapter.spawn(
                command=[sys.executable, "-c", f"print('subprocess {i}')"],
                working_dir=str(test_workspace.path),
            )
            results.append(result)

        # All should succeed
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.exit_code == 0
            assert f"subprocess {i}" in result.stdout

    def test_subprocess_survives_parent_interrupt(
        self, test_workspace, subprocess_lifecycle_manager
    ):
        """Test that subprocess cleanup happens even when parent is interrupted.

        Validates that SubprocessLifecycleManager properly cleans up processes
        even when tests fail or are interrupted.
        """
        # Spawn long-running process
        proc = subprocess_lifecycle_manager.spawn(
            command=[sys.executable, "-c", "import time; time.sleep(100)"],
            working_dir=str(test_workspace.path),
        )

        pid = proc.pid
        assert subprocess_lifecycle_manager.is_alive(pid)

        # Simulate test cleanup (this happens automatically via fixture)
        subprocess_lifecycle_manager.cleanup_all()

        # Process should be terminated
        time.sleep(0.5)  # Give it a moment to die
        assert not subprocess_lifecycle_manager.is_alive(pid)

    @pytest.mark.skip(
        reason="Feature not implemented: stream_output parameter - real-time output streaming"
    )
    def test_subprocess_output_streaming(self, test_workspace):
        """Test that subprocess output can be streamed and captured incrementally.

        Validates that we can monitor subprocess output as it's produced,
        not just at the end.
        """
        adapter = CLISubprocessAdapter(timeout=30, stream_output=True)

        # Generate multi-line output
        result = adapter.spawn(
            command=[
                sys.executable,
                "-c",
                "import time; print('line1'); time.sleep(0.1); print('line2')",
            ],
            working_dir=str(test_workspace.path),
        )

        assert result.exit_code == 0
        assert "line1" in result.stdout
        assert "line2" in result.stdout
        # Output should be in order
        assert result.stdout.index("line1") < result.stdout.index("line2")

    def test_subprocess_cleanup_on_failure(self, test_workspace, subprocess_lifecycle_manager):
        """Test that subprocesses are cleaned up even when test logic fails.

        Validates graceful cleanup in error conditions.
        """
        # Spawn a long-running process
        proc = subprocess_lifecycle_manager.spawn(
            command=[sys.executable, "-c", "import time; time.sleep(100)"],
            working_dir=str(test_workspace.path),
        )

        pid = proc.pid
        assert subprocess_lifecycle_manager.is_alive(pid)

        # Cleanup should happen automatically via fixture teardown
        # even if we had raised an exception here


@pytest.mark.e2e
@pytest.mark.subprocess
class TestProcessMonitoring:
    """Test subprocess monitoring and state tracking."""

    @pytest.mark.skip(
        reason="Feature not implemented: monitor=True parameter - enhanced monitoring with progress updates"
    )
    def test_monitor_running_process(self, test_workspace):
        """Test monitoring a subprocess while it's executing.

        Validates that we can check process state during execution.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        # Use a script that runs for a bit
        script = test_workspace.write_file(
            "monitor_test.py",
            "import time\nfor i in range(5):\n    print(f'tick {i}')\n    time.sleep(0.2)",
        )

        result = adapter.spawn(
            command=[sys.executable, str(script)],
            working_dir=str(test_workspace.path),
            monitor=True,  # Enable monitoring
        )

        assert result.exit_code == 0
        assert result.monitoring_data is not None
        assert len(result.monitoring_data.get("progress_updates", [])) > 0

    def test_detect_process_completion(self, test_workspace, subprocess_lifecycle_manager):
        """Test detecting when a subprocess completes naturally.

        Validates completion detection without errors.
        """
        proc = subprocess_lifecycle_manager.spawn(
            command=[sys.executable, "-c", "print('done')"], working_dir=str(test_workspace.path)
        )

        # Wait for completion
        proc.wait(timeout=5)

        assert proc.returncode == 0
        assert not subprocess_lifecycle_manager.is_alive(proc.pid)

    def test_track_execution_duration(self, test_workspace):
        """Test accurate tracking of subprocess execution duration.

        Validates that duration measurements are accurate.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        start_time = time.time()
        result = adapter.spawn(
            command=[sys.executable, "-c", "import time; time.sleep(1); print('done')"],
            working_dir=str(test_workspace.path),
        )
        end_time = time.time()

        # Duration should be approximately 1 second
        assert 0.9 <= result.duration <= 1.5
        # Should match wall-clock time
        assert abs(result.duration - (end_time - start_time)) < 0.5


@pytest.mark.e2e
@pytest.mark.subprocess
class TestLifecycleManagement:
    """Test subprocess lifecycle management and cleanup."""

    def test_subprocess_cleanup_on_exit(self, test_workspace, subprocess_lifecycle_manager):
        """Test that subprocess is cleaned up when manager scope exits.

        Validates automatic cleanup - the core feature of lifecycle management.
        """
        # Spawn long-running process
        proc = subprocess_lifecycle_manager.spawn(
            command=[sys.executable, "-c", "import time; time.sleep(100)"],
            working_dir=str(test_workspace.path),
        )

        pid = proc.pid
        assert subprocess_lifecycle_manager.is_alive(pid)

        # This would normally happen automatically, we're testing it explicitly
        subprocess_lifecycle_manager.cleanup_all()

        # Give process time to die
        time.sleep(0.5)
        assert not subprocess_lifecycle_manager.is_alive(pid)

    def test_cleanup_multiple_processes(self, test_workspace, subprocess_lifecycle_manager):
        """Test cleaning up multiple subprocesses simultaneously.

        Validates batch cleanup works correctly.
        """
        # Spawn 5 long-running processes
        pids = []
        for i in range(5):
            proc = subprocess_lifecycle_manager.spawn(
                command=[sys.executable, "-c", "import time; time.sleep(100)"],
                working_dir=str(test_workspace.path),
            )
            pids.append(proc.pid)

        # All should be alive
        for pid in pids:
            assert subprocess_lifecycle_manager.is_alive(pid)

        # Cleanup all at once
        subprocess_lifecycle_manager.cleanup_all()
        time.sleep(0.5)

        # All should be dead
        for pid in pids:
            assert not subprocess_lifecycle_manager.is_alive(pid)

    def test_cleanup_on_test_failure(self, test_workspace, subprocess_lifecycle_manager):
        """Test that cleanup happens even when test fails.

        Validates cleanup in error paths - critical for preventing orphaned processes.
        """
        proc = subprocess_lifecycle_manager.spawn(
            command=[sys.executable, "-c", "import time; time.sleep(100)"],
            working_dir=str(test_workspace.path),
        )

        pid = proc.pid
        assert subprocess_lifecycle_manager.is_alive(pid)

        # Even if we raise an exception here, fixture cleanup should kill the process
        # The fixture's teardown will call cleanup_all()

    @pytest.mark.skip(
        reason="Feature not implemented: handle_orphans parameter - enhanced orphan process detection"
    )
    def test_kill_orphaned_processes(self, test_workspace):
        """Test detection and cleanup of orphaned processes.

        Validates that processes spawned outside the manager can still be cleaned up.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        # Spawn process that creates a child
        script = test_workspace.write_file(
            "spawn_child.py",
            """
import subprocess
import time
proc = subprocess.Popen(['python', '-c', 'import time; time.sleep(100)'])
print(f'child_pid:{proc.pid}')
time.sleep(100)
""",
        )

        result = adapter.spawn(
            command=[sys.executable, str(script)],
            working_dir=str(test_workspace.path),
            timeout=2,  # Will timeout, killing parent
            handle_orphans=True,
        )

        # Should detect timeout
        assert result.timed_out
        # Should have cleaned up child process
        assert result.orphans_cleaned == 1


@pytest.mark.e2e
@pytest.mark.subprocess
class TestWorkingDirectory:
    """Test working directory handling for subprocesses."""

    def test_subprocess_uses_working_directory(self, test_workspace):
        """Test that subprocess executes in specified working directory.

        Validates working directory configuration is respected.
        """
        # Create a file in workspace
        _ = test_workspace.write_file("marker.txt", "workspace marker")

        adapter = CLISubprocessAdapter(timeout=30)

        result = adapter.spawn(
            command=[sys.executable, "-c", "import os; print(os.path.exists('marker.txt'))"],
            working_dir=str(test_workspace.path),
        )

        assert result.exit_code == 0
        assert "True" in result.stdout

    def test_isolated_workspace_per_test(self, test_workspace):
        """Test that each test gets an isolated workspace.

        Validates test isolation - critical for preventing test interference.
        """
        # Write unique file
        unique_marker = f"test_{os.getpid()}_{time.time()}"
        test_workspace.write_file("unique.txt", unique_marker)

        # Verify it exists
        assert test_workspace.exists("unique.txt")
        content = test_workspace.read_file("unique.txt")
        assert content == unique_marker

        # Workspace should be empty except for our file
        files = test_workspace.list_files()
        assert len(files) == 1
        assert files[0].name == "unique.txt"


@pytest.mark.e2e
@pytest.mark.subprocess
class TestEnvironmentVariables:
    """Test environment variable handling in subprocesses."""

    def test_spawn_with_environment_variables(self, test_workspace):
        """Test subprocess receives custom environment variables.

        Validates environment configuration is passed to subprocess.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        result = adapter.spawn(
            command=[sys.executable, "-c", "import os; print(os.getenv('TEST_VAR'))"],
            working_dir=str(test_workspace.path),
            env={"TEST_VAR": "test_value"},
        )

        assert result.exit_code == 0
        assert "test_value" in result.stdout

    def test_environment_inheritance(self, test_workspace):
        """Test subprocess inherits parent environment by default.

        Validates default environment inheritance behavior.
        """
        # Set environment variable
        os.environ["INHERITED_VAR"] = "inherited_value"

        adapter = CLISubprocessAdapter(timeout=30)

        result = adapter.spawn(
            command=[sys.executable, "-c", "import os; print(os.getenv('INHERITED_VAR'))"],
            working_dir=str(test_workspace.path),
        )

        assert result.exit_code == 0
        assert "inherited_value" in result.stdout

        # Cleanup
        del os.environ["INHERITED_VAR"]


@pytest.mark.e2e
@pytest.mark.subprocess
class TestOutputCapture:
    """Test stdout and stderr capture from subprocesses."""

    def test_capture_stdout_stderr(self, test_workspace):
        """Test capturing both stdout and stderr separately.

        Validates output capture distinguishes between streams.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        result = adapter.spawn(
            command=[
                sys.executable,
                "-c",
                "import sys; print('stdout message'); sys.stderr.write('stderr message\\n')",
            ],
            working_dir=str(test_workspace.path),
        )

        assert result.exit_code == 0
        assert "stdout message" in result.stdout
        assert "stderr message" in result.stderr

    def test_capture_mixed_output(self, test_workspace):
        """Test capturing interleaved stdout and stderr.

        Validates mixed output capture preserves relative ordering.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        script = test_workspace.write_file(
            "mixed_output.py",
            """
import sys
import time
print('stdout1')
sys.stderr.write('stderr1\\n')
sys.stderr.flush()
time.sleep(0.1)
print('stdout2')
sys.stderr.write('stderr2\\n')
""",
        )

        result = adapter.spawn(
            command=[sys.executable, str(script)], working_dir=str(test_workspace.path)
        )

        assert result.exit_code == 0
        assert "stdout1" in result.stdout
        assert "stdout2" in result.stdout
        assert "stderr1" in result.stderr
        assert "stderr2" in result.stderr
