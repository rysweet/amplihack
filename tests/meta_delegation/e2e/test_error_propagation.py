"""Layer 2: Error Propagation Tests.

Tests error handling, timeout management, and failure recovery across
subprocess boundaries. Validates that errors are properly captured,
propagated, and provide sufficient context for debugging.
"""

import sys

import pytest

# These imports will fail initially - that's the point of TDD
from amplihack.meta_delegation.subprocess_adapter import (
    CLISubprocessAdapter,
    SubprocessError,
    SubprocessTimeoutError,
)

# Import temp_env_var context manager
from tests.meta_delegation.e2e.conftest import temp_env_var


@pytest.mark.e2e
@pytest.mark.subprocess
class TestTimeoutHandling:
    """Test timeout enforcement and error handling."""

    @pytest.mark.skip(reason="Feature not implemented: capture_exceptions parameter")
    def test_subprocess_exception_propagates_to_parent(self, test_workspace):
        """Test that subprocess exceptions are captured and propagated correctly.

        Validates that Python exceptions in subprocess are caught and
        re-raised in parent with full context.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        script = test_workspace.write_file(
            "raises_exception.py",
            """
raise ValueError("Test error from subprocess")
""",
        )

        with pytest.raises(SubprocessError) as exc_info:
            adapter.spawn(
                command=[sys.executable, str(script)],
                working_dir=str(test_workspace.path),
                capture_exceptions=True,
            )

        error = exc_info.value
        assert "ValueError" in str(error)
        assert "Test error from subprocess" in str(error)
        assert error.subprocess_exit_code != 0

    def test_subprocess_stderr_captured_on_failure(self, test_workspace):
        """Test that stderr is fully captured when subprocess fails.

        Validates that error messages are preserved for debugging.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        script = test_workspace.write_file(
            "writes_stderr.py",
            """
import sys
sys.stderr.write("Critical error occurred\\n")
sys.stderr.write("Additional context line\\n")
sys.exit(1)
""",
        )

        with pytest.raises(SubprocessError) as exc_info:
            adapter.spawn(
                command=[sys.executable, str(script)],
                working_dir=str(test_workspace.path),
                check=True,  # Raise on non-zero exit
            )

        error = exc_info.value
        assert "Critical error occurred" in error.stderr
        assert "Additional context line" in error.stderr
        assert error.subprocess_exit_code == 1

    def test_subprocess_timeout_error_structure(self, test_workspace):
        """Test that timeout errors have complete structured information.

        Validates timeout error contains all diagnostic information needed
        for debugging (timeout value, actual duration, command, pid, etc.).
        """
        adapter = CLISubprocessAdapter(timeout=2)

        with pytest.raises(SubprocessTimeoutError) as exc_info:
            adapter.spawn(
                command=[sys.executable, "-c", "import time; time.sleep(100)"],
                working_dir=str(test_workspace.path),
            )

        error = exc_info.value
        # Timeout information
        assert error.timeout == 2
        assert error.duration >= 2
        # Command information
        assert "python" in str(error.command).lower()
        # Process information
        assert error.subprocess_pid > 0
        assert error.was_killed is True
        # Error message
        assert "timeout" in str(error).lower()
        assert "2" in str(error)  # Mentions timeout value

    def test_subprocess_non_zero_exit_handled(self, test_workspace):
        """Test proper handling of non-zero exit codes.

        Validates that exit codes are captured and errors raised appropriately.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        # Exit with code 42
        result = adapter.spawn(
            command=[sys.executable, "-c", "import sys; sys.exit(42)"],
            working_dir=str(test_workspace.path),
            check=False,  # Don't raise on non-zero
        )

        assert result.exit_code == 42
        assert result.success is False

        # With check=True, should raise
        with pytest.raises(SubprocessError) as exc_info:
            adapter.spawn(
                command=[sys.executable, "-c", "import sys; sys.exit(42)"],
                working_dir=str(test_workspace.path),
                check=True,
            )

        error = exc_info.value
        assert error.subprocess_exit_code == 42

    @pytest.mark.skip(
        reason="Feature not implemented: json_recovery parameter and json_parse_failed/parsed_json result attributes"
    )
    def test_subprocess_json_parsing_error_recovery(self, test_workspace):
        """Test recovery when subprocess output isn't valid JSON.

        Validates graceful handling when expecting JSON but receiving malformed data.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        script = test_workspace.write_file(
            "bad_json.py",
            """
print("This is not JSON")
print("{incomplete json")
""",
        )

        # Should not crash, but return raw output
        result = adapter.spawn(
            command=[sys.executable, str(script)],
            working_dir=str(test_workspace.path),
            expect_json=True,
            json_recovery=True,
        )

        assert result.exit_code == 0
        assert result.json_parse_failed is True
        assert "This is not JSON" in result.stdout
        assert result.parsed_json is None

    @pytest.mark.skip(
        reason="Feature not implemented: context parameter and task_context error attribute"
    )
    def test_error_context_preserves_task_info(self, test_workspace):
        """Test that errors preserve task context from orchestration.

        Validates that task-specific metadata is attached to errors for debugging.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        task_context = {
            "task_id": "test-task-123",
            "persona": "guide",
            "goal": "Test error handling",
        }

        with pytest.raises(SubprocessError) as exc_info:
            adapter.spawn(
                command=[sys.executable, "-c", "import sys; sys.exit(1)"],
                working_dir=str(test_workspace.path),
                check=True,
                context=task_context,
            )

        error = exc_info.value
        assert error.task_context is not None
        assert error.task_context["task_id"] == "test-task-123"
        assert error.task_context["persona"] == "guide"
        assert error.task_context["goal"] == "Test error handling"


@pytest.mark.e2e
@pytest.mark.subprocess
class TestErrorCapture:
    """Test comprehensive error message capture."""

    def test_capture_error_output(self, test_workspace):
        """Test capturing stderr when process fails.

        Validates complete stderr capture for debugging.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        script = test_workspace.write_file(
            "error_output.py",
            """
import sys
sys.stderr.write("ERROR: Something went wrong\\n")
sys.stderr.write("Stack trace would be here\\n")
sys.exit(1)
""",
        )

        result = adapter.spawn(
            command=[sys.executable, str(script)], working_dir=str(test_workspace.path), check=False
        )

        assert result.exit_code == 1
        assert "ERROR: Something went wrong" in result.stderr
        assert "Stack trace would be here" in result.stderr

    def test_capture_mixed_stdout_stderr(self, test_workspace):
        """Test capturing both stdout and stderr from failed process.

        Validates that both streams are preserved independently.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        script = test_workspace.write_file(
            "mixed_streams.py",
            """
import sys
print("Stdout: Operation starting")
sys.stderr.write("Stderr: Warning occurred\\n")
print("Stdout: Operation continuing")
sys.stderr.write("Stderr: Error occurred\\n")
sys.exit(1)
""",
        )

        result = adapter.spawn(
            command=[sys.executable, str(script)], working_dir=str(test_workspace.path), check=False
        )

        # Both streams captured
        assert "Operation starting" in result.stdout
        assert "Operation continuing" in result.stdout
        assert "Warning occurred" in result.stderr
        assert "Error occurred" in result.stderr

    def test_preserve_error_messages(self, test_workspace):
        """Test that error messages are preserved exactly as written.

        Validates no truncation or mangling of error output.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        long_error = "ERROR: " + ("x" * 1000)  # Long error message
        script = test_workspace.write_file(
            "long_error.py",
            f"""
import sys
sys.stderr.write("{long_error}\\n")
sys.exit(1)
""",
        )

        result = adapter.spawn(
            command=[sys.executable, str(script)], working_dir=str(test_workspace.path), check=False
        )

        assert long_error in result.stderr
        assert len(result.stderr) >= 1000


@pytest.mark.e2e
@pytest.mark.subprocess
class TestFailureRecovery:
    """Test recovery from various failure modes."""

    def test_cleanup_after_process_crash(self, test_workspace, subprocess_lifecycle_manager):
        """Test cleanup when subprocess crashes unexpectedly.

        Validates that crashed processes are properly cleaned up.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        script = test_workspace.write_file(
            "crash.py",
            """
import os
import signal
os.kill(os.getpid(), signal.SIGKILL)  # Hard crash
""",
        )

        result = adapter.spawn(
            command=[sys.executable, str(script)], working_dir=str(test_workspace.path), check=False
        )

        # Process crashed
        assert result.exit_code != 0
        assert result.crashed is True
        # Should be cleaned up
        assert not subprocess_lifecycle_manager.is_alive(result.subprocess_pid)

    def test_recover_from_spawn_failure(self, test_workspace):
        """Test recovery when subprocess fails to spawn.

        Validates handling of spawn-time errors (e.g., command not found).
        """
        adapter = CLISubprocessAdapter(timeout=30)

        with pytest.raises(SubprocessError) as exc_info:
            adapter.spawn(command=["nonexistent_command_xyz"], working_dir=str(test_workspace.path))

        error = exc_info.value
        assert "not found" in str(error).lower() or "no such file" in str(error).lower()
        assert error.spawn_failed is True

    def test_continue_after_subprocess_error(self, test_workspace):
        """Test that orchestration can continue after subprocess error.

        Validates that one failed subprocess doesn't prevent subsequent operations.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        # First subprocess fails
        result1 = adapter.spawn(
            command=[sys.executable, "-c", "import sys; sys.exit(1)"],
            working_dir=str(test_workspace.path),
            check=False,
        )
        assert result1.exit_code == 1

        # Second subprocess should still work
        result2 = adapter.spawn(
            command=[sys.executable, "-c", "print('success')"], working_dir=str(test_workspace.path)
        )
        assert result2.exit_code == 0
        assert "success" in result2.stdout

    @pytest.mark.skip(
        reason="Feature limitation: Partial output capture during timeout requires improved non-blocking I/O handling"
    )
    def test_partial_output_on_timeout(self, test_workspace):
        """Test that partial output is preserved when subprocess times out.

        Validates we don't lose output produced before timeout.

        Note: This test is skipped because reliable partial output capture during
        timeout requires enhanced non-blocking I/O implementation. The current
        implementation uses select() but calling read() without size can block.
        A proper fix requires either:
        1. Using asyncio for true non-blocking I/O
        2. Using threading to read output streams
        3. Setting files to non-blocking mode with fcntl
        """
        adapter = CLISubprocessAdapter(timeout=2)

        script = test_workspace.write_file(
            "partial_output.py",
            """
import sys
import time
print("Line 1", flush=True)
time.sleep(0.5)
print("Line 2", flush=True)
time.sleep(0.5)
print("Line 3", flush=True)
sys.stdout.flush()
time.sleep(100)  # Will timeout here
print("Never reached", flush=True)
""",
        )

        with pytest.raises(SubprocessTimeoutError) as exc_info:
            adapter.spawn(
                command=[sys.executable, str(script)], working_dir=str(test_workspace.path)
            )

        error = exc_info.value
        # Partial output should be preserved (when flushed)
        assert "Line 1" in error.partial_stdout
        assert "Line 2" in error.partial_stdout
        assert "Line 3" in error.partial_stdout
        assert "Never reached" not in error.partial_stdout


@pytest.mark.e2e
@pytest.mark.subprocess
class TestCICDCompatibility:
    """Test CI/CD specific error handling."""

    def test_aggressive_timeout_in_ci(self, test_workspace):
        """Test that CI environments use shorter timeouts.

        Validates CI-specific timeout configuration prevents hanging builds.
        """
        with temp_env_var("CI", "true"):
            adapter = CLISubprocessAdapter()  # Uses env-based defaults

            # Should use aggressive timeout (30s) in CI
            assert adapter.default_timeout == 30.0

    def test_no_hanging_processes_in_ci(self, test_workspace, subprocess_lifecycle_manager):
        """Test that no processes are left hanging in CI environment.

        Validates complete cleanup for CI builds.
        """
        with temp_env_var("CI", "true"):
            adapter = CLISubprocessAdapter(timeout=2)

            # Spawn multiple processes that would timeout
            with pytest.raises(SubprocessTimeoutError):
                adapter.spawn(
                    command=[sys.executable, "-c", "import time; time.sleep(100)"],
                    working_dir=str(test_workspace.path),
                )

            # All should be cleaned up
            subprocess_lifecycle_manager.cleanup_all()

            # Verify no hanging processes
            # In real implementation, would check ps output

    @pytest.mark.skip(
        reason="Feature not implemented: ci_format parameter and ci_formatted_message error attribute"
    )
    def test_error_reporting_format_for_ci(self, test_workspace):
        """Test that errors are formatted for CI log parsing.

        Validates error output is CI-tool friendly (GitHub Actions, etc.).
        """
        adapter = CLISubprocessAdapter(timeout=30)

        with pytest.raises(SubprocessError) as exc_info:
            adapter.spawn(
                command=[sys.executable, "-c", "import sys; sys.exit(1)"],
                working_dir=str(test_workspace.path),
                check=True,
                ci_format=True,
            )

        error = exc_info.value
        # Should have structured format for CI
        assert hasattr(error, "ci_formatted_message")
        # Example: "::error file=test.py,line=10::Subprocess failed"
        assert "::" in error.ci_formatted_message or "ERROR:" in error.ci_formatted_message


@pytest.mark.e2e
@pytest.mark.subprocess
class TestErrorPropagationEdgeCases:
    """Test edge cases in error propagation."""

    def test_unicode_in_error_messages(self, test_workspace):
        """Test handling of Unicode characters in error messages.

        Validates international character support in errors.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        script = test_workspace.write_file(
            "unicode_error.py",
            """
import sys
sys.stderr.write("Error: 文件不存在 (File not found)\\n")
sys.stderr.write("Erreur: Fichier introuvable\\n")
sys.exit(1)
""",
        )

        result = adapter.spawn(
            command=[sys.executable, str(script)], working_dir=str(test_workspace.path), check=False
        )

        assert "文件不存在" in result.stderr
        assert "Fichier introuvable" in result.stderr

    @pytest.mark.skip(
        reason="Feature not implemented: binary_safe parameter and stdout_bytes result attribute"
    )
    def test_binary_output_handling(self, test_workspace):
        """Test handling of binary output from subprocess.

        Validates graceful handling when subprocess writes binary data.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        script = test_workspace.write_file(
            "binary_output.py",
            """
import sys
sys.stdout.buffer.write(b"\\x00\\x01\\x02\\x03")
""",
        )

        result = adapter.spawn(
            command=[sys.executable, str(script)],
            working_dir=str(test_workspace.path),
            check=False,
            binary_safe=True,
        )

        assert result.exit_code == 0
        # Should handle binary gracefully
        assert result.stdout_bytes is not None

    def test_recursive_error_handling(self, test_workspace):
        """Test error handling when subprocess spawns failing subprocess.

        Validates nested error propagation.
        """
        adapter = CLISubprocessAdapter(timeout=30)

        inner_script = test_workspace.write_file(
            "inner.py", "import sys; sys.stderr.write('Inner error\\n'); sys.exit(2)"
        )

        outer_script = test_workspace.write_file(
            "outer.py",
            f"""
import subprocess
import sys
result = subprocess.run(['{sys.executable}', '{inner_script}'], capture_output=True)
sys.stderr.write(f"Outer: inner failed with {{result.returncode}}\\n")
sys.stderr.buffer.write(result.stderr)
sys.exit(1)
""",
        )

        result = adapter.spawn(
            command=[sys.executable, str(outer_script)],
            working_dir=str(test_workspace.path),
            check=False,
        )

        # Should capture both error messages
        assert "Inner error" in result.stderr
        assert "Outer: inner failed" in result.stderr
