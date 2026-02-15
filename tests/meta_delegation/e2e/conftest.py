"""Shared fixtures for end-to-end integration tests.

Provides test infrastructure for subprocess lifecycle management,
isolated workspaces, and CLI adapter testing.
"""

import os
import shutil
import signal
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import pytest


class SubprocessLifecycleManager:
    """Manages subprocess lifecycle with automatic cleanup.

    Tracks all spawned subprocesses and ensures they are terminated
    on test completion, even if the test fails.
    """

    def __init__(self):
        self.processes: list[subprocess.Popen] = []

    def spawn(
        self, command: list[str], working_dir: str, timeout: int = 30, **kwargs
    ) -> subprocess.Popen:
        """Spawn a subprocess and track it for cleanup.

        Args:
            command: Command and arguments to execute
            working_dir: Working directory for subprocess
            timeout: Timeout in seconds
            **kwargs: Additional arguments passed to subprocess.Popen

        Returns:
            subprocess.Popen: The spawned process
        """
        proc = subprocess.Popen(
            command, cwd=working_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs
        )
        self.processes.append(proc)
        return proc

    def is_alive(self, pid: int) -> bool:
        """Check if process is still running.

        Args:
            pid: Process ID to check

        Returns:
            bool: True if process is alive
        """
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def kill(self, pid: int, signal_num: int = signal.SIGTERM) -> None:
        """Terminate a specific process.

        Args:
            pid: Process ID to terminate
            signal_num: Signal to send (default: SIGTERM)
        """
        try:
            os.kill(pid, signal_num)
        except (OSError, ProcessLookupError):
            pass

    def cleanup_all(self) -> None:
        """Kill all tracked processes."""
        for proc in self.processes:
            if proc.poll() is None:  # Still running
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                except (ProcessLookupError, PermissionError):
                    # Process already dead or not accessible - acceptable
                    pass
                except Exception as e:
                    import warnings

                    warnings.warn(f"Unexpected cleanup error for PID {proc.pid}: {e}", stacklevel=2)
        self.processes.clear()


class TestWorkspaceFixture:
    """Isolated temporary workspace for each test.

    Provides methods to create test files, read outputs, and
    list generated files within an isolated directory.
    """

    def __init__(self, base_path: Path):
        self.path = base_path

    def setup(self) -> None:
        """Create the workspace directory."""
        self.path.mkdir(parents=True, exist_ok=True)

    def teardown(self) -> None:
        """Remove all workspace files."""
        if self.path.exists():
            shutil.rmtree(self.path)

    def write_file(self, relative_path: str, content: str) -> Path:
        """Write a file in the workspace.

        Args:
            relative_path: Path relative to workspace root
            content: File content

        Returns:
            Path: Absolute path to created file
        """
        file_path = self.path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return file_path

    def read_file(self, relative_path: str) -> str:
        """Read a file from the workspace.

        Args:
            relative_path: Path relative to workspace root

        Returns:
            str: File content
        """
        file_path = self.path / relative_path
        return file_path.read_text()

    def list_files(self, pattern: str = "*") -> list[Path]:
        """List files in workspace matching pattern.

        Args:
            pattern: Glob pattern (default: all files)

        Returns:
            List[Path]: Matching file paths
        """
        return list(self.path.glob(f"**/{pattern}"))

    def exists(self, relative_path: str) -> bool:
        """Check if file exists in workspace.

        Args:
            relative_path: Path relative to workspace root

        Returns:
            bool: True if file exists
        """
        return (self.path / relative_path).exists()


@pytest.fixture
def test_workspace(tmp_path) -> Generator[TestWorkspaceFixture, None, None]:
    """Provide isolated test workspace with automatic cleanup.

    Each test gets a unique temporary directory that is removed
    after test completion.

    Yields:
        TestWorkspaceFixture: Workspace manager
    """
    workspace = TestWorkspaceFixture(tmp_path / "workspace")
    workspace.setup()
    yield workspace
    workspace.teardown()


@pytest.fixture
def subprocess_lifecycle_manager() -> Generator[SubprocessLifecycleManager, None, None]:
    """Provide subprocess lifecycle manager with automatic cleanup.

    Ensures all spawned subprocesses are terminated when test completes,
    even on test failure.

    Yields:
        SubprocessLifecycleManager: Lifecycle manager
    """
    manager = SubprocessLifecycleManager()
    yield manager
    manager.cleanup_all()


@pytest.fixture
def timeout_config() -> dict:
    """Provide timeout configuration based on environment.

    CI environments use aggressive timeouts to prevent hanging builds.
    Local development uses more lenient timeouts.

    Returns:
        dict: Timeout configuration with 'subprocess' and 'test' keys
    """
    is_ci = os.getenv("CI", "false").lower() == "true"

    if is_ci:
        return {
            "subprocess": 30,  # 30 seconds in CI
            "test": 60,  # 1 minute per test
        }
    return {
        "subprocess": 60,  # 60 seconds locally
        "test": 120,  # 2 minutes per test
    }


@pytest.fixture
def cli_adapter():
    """Provide CLISubprocessAdapter instance for testing.

    This fixture will fail until CLISubprocessAdapter is implemented,
    which is the expected behavior for TDD.

    Returns:
        CLISubprocessAdapter: Adapter instance
    """
    # This will fail initially - that's expected for TDD
    from amplihack.meta_delegation.subprocess_adapter import CLISubprocessAdapter

    return CLISubprocessAdapter()


@contextmanager
def temp_env_var(key: str, value: str):
    """Context manager for temporarily setting an environment variable.

    Automatically restores the original value (or removes the variable if it
    didn't exist) when the context exits.

    Args:
        key: Environment variable name
        value: Environment variable value

    Yields:
        None

    Example:
        >>> with temp_env_var("CI", "true"):
        ...     print(os.environ["CI"])  # "true"
        >>> # CI is restored to original value or removed
    """
    old_value = os.environ.get(key)
    os.environ[key] = value
    try:
        yield
    finally:
        if old_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old_value
