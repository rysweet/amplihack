"""Subprocess-based test harness fer outside-in plugin testin'.
import sys

Philosophy:
- Test from the outside in, as a user would
- Real subprocess execution (no mocking)
import sys
- Fast execution (< 5 minutes total)
- Clear failure messages
- Non-interactive (no user input)

Public API (the "studs"):
    PluginTestHarness: Plugin lifecycle testin'
    HookTestHarness: Hook protocol testin'
    LSPTestHarness: LSP detection testin'
    SubprocessResult: Result dataclass
"""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SubprocessResult:
    """Result from subprocess execution.

    Attributes:
        returncode: Process exit code
        stdout: Standard output as string
        stderr: Standard error as string
        success: True if returncode is 0
        command: Command that was executed
        duration: Execution time in seconds
    """

    returncode: int
    stdout: str
    stderr: str
    success: bool
    command: list[str]
    duration: float

    def assert_success(self, message: str | None = None) -> None:
        """Assert that the command succeeded.

        Args:
            message: Custom error message

        Raises:
            AssertionError: If command failed
        """
        msg = message or f"Command failed: {' '.join(self.command)}"
        assert self.success, f"{msg}\nstdout: {self.stdout}\nstderr: {self.stderr}"

    def assert_failure(self, message: str | None = None) -> None:
        """Assert that the command failed.

        Args:
            message: Custom error message

        Raises:
            AssertionError: If command succeeded
        """
        msg = message or f"Command unexpectedly succeeded: {' '.join(self.command)}"
        assert not self.success, f"{msg}\nstdout: {self.stdout}"

    def assert_in_stdout(self, text: str, message: str | None = None) -> None:
        """Assert text appears in stdout.

        Args:
            text: Text to search fer
            message: Custom error message

        Raises:
            AssertionError: If text not found
        """
        msg = message or f"Expected '{text}' in stdout"
        assert text in self.stdout, f"{msg}\nstdout: {self.stdout}"

    def assert_in_stderr(self, text: str, message: str | None = None) -> None:
        """Assert text appears in stderr.

        Args:
            text: Text to search fer
            message: Custom error message

        Raises:
            AssertionError: If text not found
        """
        msg = message or f"Expected '{text}' in stderr"
        assert text in self.stderr, f"{msg}\nstderr: {self.stderr}"


class PluginTestHarness:
    """Test harness fer plugin lifecycle testin'.

    Tests plugin installation, configuration, and uninstallation
    from outside-in perspective.

    Example:
        >>> harness = PluginTestHarness()
        >>> result = harness.install_plugin("git+https://github.com/user/plugin")
        >>> result.assert_success()
        >>> harness.verify_plugin_installed("my-plugin")
    """

    def __init__(self, plugin_dir: Path | None = None, timeout: int = 60):
        """Initialize plugin test harness.

        Args:
            plugin_dir: Directory fer plugin installation (default: temp dir)
            timeout: Timeout in seconds fer commands (default: 60)
        """
        self.plugin_dir = plugin_dir or Path(tempfile.mkdtemp(prefix="plugin_test_"))
        self.timeout = timeout
        self.installed_plugins: list[str] = []

    def install_plugin(
        self, source: str, force: bool = False, extra_args: list[str] | None = None
    ) -> SubprocessResult:
        """Install plugin from source.

        Args:
            source: Plugin source (git URL or local path)
            force: Force reinstall if already installed
            extra_args: Additional command-line args

        Returns:
            SubprocessResult with installation output
        """
        import time

        cmd = [sys.executable, "-m", "amplihack.cli", "plugin", "install", source]
        cmd.append(f"--plugin-dir={self.plugin_dir}")

        if force:
            cmd.append("--force")

        if extra_args:
            cmd.extend(extra_args)

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.plugin_dir,
            )
            duration = time.time() - start_time

            # Track installed plugins
            if result.returncode == 0:
                plugin_name = self._extract_plugin_name(result.stdout)
                if plugin_name:
                    self.installed_plugins.append(plugin_name)

            return SubprocessResult(
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=result.returncode == 0,
                command=cmd,
                duration=duration,
            )
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return SubprocessResult(
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {self.timeout} seconds",
                success=False,
                command=cmd,
                duration=duration,
            )

    def uninstall_plugin(
        self,
        plugin_name: str,
        purge: bool = False,
    ) -> SubprocessResult:
        """Uninstall plugin.

        Args:
            plugin_name: Name of plugin to uninstall
            purge: Remove all plugin data

        Returns:
            SubprocessResult with uninstallation output
        """
        import time

        cmd = [sys.executable, "-m", "amplihack.cli", "plugin", "uninstall", plugin_name]
        cmd.append(f"--plugin-dir={self.plugin_dir}")

        if purge:
            cmd.append("--purge")

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.plugin_dir,
            )
            duration = time.time() - start_time

            # Remove from tracking
            if result.returncode == 0 and plugin_name in self.installed_plugins:
                self.installed_plugins.remove(plugin_name)

            return SubprocessResult(
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=result.returncode == 0,
                command=cmd,
                duration=duration,
            )
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return SubprocessResult(
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {self.timeout} seconds",
                success=False,
                command=cmd,
                duration=duration,
            )

    def list_plugins(self) -> SubprocessResult:
        """List installed plugins.

        Returns:
            SubprocessResult with plugin list
        """
        import time

        cmd = [sys.executable, "-m", "amplihack.cli", "plugin", "list"]
        cmd.append(f"--plugin-dir={self.plugin_dir}")

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.plugin_dir,
            )
            duration = time.time() - start_time

            return SubprocessResult(
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=result.returncode == 0,
                command=cmd,
                duration=duration,
            )
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return SubprocessResult(
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {self.timeout} seconds",
                success=False,
                command=cmd,
                duration=duration,
            )

    def verify_plugin_installed(self, plugin_name: str) -> bool:
        """Verify plugin is installed.

        Args:
            plugin_name: Plugin name to check

        Returns:
            True if plugin is installed
        """
        result = self.list_plugins()
        return result.success and plugin_name in result.stdout

    def verify_settings_json_exists(self) -> bool:
        """Verify settings.json was created.

        Returns:
            True if settings.json exists
        """
        settings_path = self.plugin_dir / ".claude-plugin" / "settings.json"
        return settings_path.exists()

    def read_settings_json(self) -> dict:
        """Read settings.json content.

        Returns:
            Parsed JSON content

        Raises:
            FileNotFoundError: If settings.json doesn't exist
        """
        import json

        settings_path = self.plugin_dir / ".claude-plugin" / "settings.json"
        if not settings_path.exists():
            raise FileNotFoundError(f"settings.json not found at {settings_path}")

        with open(settings_path) as f:
            return json.load(f)

    def cleanup(self) -> None:
        """Clean up test environment."""
        import shutil

        # Uninstall any remaining plugins
        for plugin_name in list(self.installed_plugins):
            self.uninstall_plugin(plugin_name, purge=True)

        # Remove temp directory
        if self.plugin_dir.exists() and "plugin_test_" in str(self.plugin_dir):
            shutil.rmtree(self.plugin_dir)

    def _extract_plugin_name(self, stdout: str) -> str | None:
        """Extract plugin name from install output.

        Args:
            stdout: Command output

        Returns:
            Plugin name if found
        """
        # Look fer lines like "Installed plugin: my-plugin"
        for line in stdout.split("\n"):
            if "installed plugin:" in line.lower():
                parts = line.split(":")
                if len(parts) >= 2:
                    return parts[-1].strip()
        return None


class HookTestHarness:
    """Test harness fer hook protocol testin'.

    Tests hook execution, error handlin', and lifecycle from
    outside-in perspective.

    Example:
        >>> harness = HookTestHarness()
        >>> result = harness.trigger_hook("pre_commit")
        >>> result.assert_success()
    """

    def __init__(self, project_dir: Path | None = None, timeout: int = 30):
        """Initialize hook test harness.

        Args:
            project_dir: Project directory (default: temp dir)
            timeout: Timeout in seconds fer commands (default: 30)
        """
        self.project_dir = project_dir or Path(tempfile.mkdtemp(prefix="hook_test_"))
        self.timeout = timeout
        self.hooks_dir = self.project_dir / ".claude-plugin" / "hooks"
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

    def create_hook(self, hook_name: str, script_content: str, language: str = "python") -> Path:
        """Create a test hook script.

        Args:
            hook_name: Name of the hook (e.g., "pre_commit")
            script_content: Hook script content
            language: Script language (python, bash, etc.)

        Returns:
            Path to created hook script
        """
        if language == "python":
            extension = ".py"
            shebang = "#!/usr/bin/env python3\n"
        elif language == "bash":
            extension = ".sh"
            shebang = "#!/bin/bash\n"
        else:
            raise ValueError(f"Unsupported language: {language}")

        hook_path = self.hooks_dir / f"{hook_name}{extension}"
        hook_path.write_text(shebang + script_content)
        hook_path.chmod(0o755)  # Make executable

        return hook_path

    def trigger_hook(self, hook_name: str, extra_args: list[str] | None = None) -> SubprocessResult:
        """Trigger a hook.

        Args:
            hook_name: Name of hook to trigger
            extra_args: Additional args to pass to hook

        Returns:
            SubprocessResult with hook execution output
        """
        import time

        cmd = ["amplihack", "hooks", "trigger", hook_name]
        cmd.append(f"--project-dir={self.project_dir}")

        if extra_args:
            cmd.extend(extra_args)

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.project_dir,
            )
            duration = time.time() - start_time

            return SubprocessResult(
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=result.returncode == 0,
                command=cmd,
                duration=duration,
            )
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return SubprocessResult(
                returncode=-1,
                stdout="",
                stderr=f"Hook timed out after {self.timeout} seconds",
                success=False,
                command=cmd,
                duration=duration,
            )

    def list_hooks(self) -> SubprocessResult:
        """List available hooks.

        Returns:
            SubprocessResult with hook list
        """
        import time

        cmd = ["amplihack", "hooks", "list"]
        cmd.append(f"--project-dir={self.project_dir}")

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.project_dir,
            )
            duration = time.time() - start_time

            return SubprocessResult(
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=result.returncode == 0,
                command=cmd,
                duration=duration,
            )
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return SubprocessResult(
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {self.timeout} seconds",
                success=False,
                command=cmd,
                duration=duration,
            )

    def verify_hook_exists(self, hook_name: str) -> bool:
        """Verify hook exists.

        Args:
            hook_name: Hook name to check

        Returns:
            True if hook exists
        """
        result = self.list_hooks()
        return result.success and hook_name in result.stdout

    def cleanup(self) -> None:
        """Clean up test environment."""
        import shutil

        if self.project_dir.exists() and "hook_test_" in str(self.project_dir):
            shutil.rmtree(self.project_dir)


class LSPTestHarness:
    """Test harness fer LSP detection testin'.

    Tests language detection and LSP configuration generation
    from outside-in perspective.

    Example:
        >>> harness = LSPTestHarness()
        >>> harness.create_python_project()
        >>> result = harness.detect_languages()
        >>> result.assert_in_stdout("python")
    """

    def __init__(self, project_dir: Path | None = None, timeout: int = 30):
        """Initialize LSP test harness.

        Args:
            project_dir: Project directory (default: temp dir)
            timeout: Timeout in seconds fer commands (default: 30)
        """
        self.project_dir = project_dir or Path(tempfile.mkdtemp(prefix="lsp_test_"))
        self.timeout = timeout

    def create_python_project(self) -> None:
        """Create a Python project fer testin'."""
        (self.project_dir / "main.py").write_text("print('Hello, World!')")
        (self.project_dir / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'")

    def create_typescript_project(self) -> None:
        """Create a TypeScript project fer testin'."""
        (self.project_dir / "index.ts").write_text("const x: string = 'test';")
        (self.project_dir / "tsconfig.json").write_text('{"compilerOptions": {}}')

    def create_rust_project(self) -> None:
        """Create a Rust project fer testin'."""
        src_dir = self.project_dir / "src"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "main.rs").write_text('fn main() { println!("Hello"); }')
        (self.project_dir / "Cargo.toml").write_text('[package]\nname = "test"')

    def create_multi_language_project(self) -> None:
        """Create a multi-language project fer testin'."""
        self.create_python_project()
        self.create_typescript_project()
        self.create_rust_project()

    def detect_languages(self) -> SubprocessResult:
        """Detect languages in project.

        Returns:
            SubprocessResult with detected languages
        """
        import time

        cmd = ["amplihack", "lsp", "detect"]
        cmd.append(f"--project-dir={self.project_dir}")

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.project_dir,
            )
            duration = time.time() - start_time

            return SubprocessResult(
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=result.returncode == 0,
                command=cmd,
                duration=duration,
            )
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return SubprocessResult(
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {self.timeout} seconds",
                success=False,
                command=cmd,
                duration=duration,
            )

    def configure_lsp(self, languages: list[str] | None = None) -> SubprocessResult:
        """Configure LSP fer detected languages.

        Args:
            languages: Specific languages to configure (default: auto-detect)

        Returns:
            SubprocessResult with configuration output
        """
        import time

        cmd = ["amplihack", "lsp", "configure"]
        cmd.append(f"--project-dir={self.project_dir}")

        if languages:
            cmd.extend(["--languages", ",".join(languages)])

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.project_dir,
            )
            duration = time.time() - start_time

            return SubprocessResult(
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=result.returncode == 0,
                command=cmd,
                duration=duration,
            )
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return SubprocessResult(
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {self.timeout} seconds",
                success=False,
                command=cmd,
                duration=duration,
            )

    def verify_lsp_config_exists(self, language: str) -> bool:
        """Verify LSP config was created fer language.

        Args:
            language: Language name

        Returns:
            True if config exists
        """
        config_path = self.project_dir / ".claude-plugin" / "lsp" / f"{language}.json"
        return config_path.exists()

    def cleanup(self) -> None:
        """Clean up test environment."""
        import shutil

        if self.project_dir.exists() and "lsp_test_" in str(self.project_dir):
            shutil.rmtree(self.project_dir)


__all__ = [
    "PluginTestHarness",
    "HookTestHarness",
    "LSPTestHarness",
    "SubprocessResult",
]
