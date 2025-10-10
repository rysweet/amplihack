"""Core launcher functionality for Claude Code."""

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from ..proxy.manager import ProxyManager
from ..utils.claude_cli import get_claude_cli_path
from ..utils.claude_trace import get_claude_command
from ..utils.prerequisites import check_prerequisites
from ..uvx.manager import UVXManager
from .detector import ClaudeDirectoryDetector
from .repo_checkout import checkout_repository


class ClaudeLauncher:
    """Launches Claude Code with proper configuration and performance optimization.

    This class manages the complete Claude Code launch process including:
    - Repository checkout and directory management
    - UVX environment detection and --add-dir integration
    - Proxy management for Azure integration
    - Performance optimization through intelligent caching

    Performance Optimizations:
        - Path resolution caching: Avoids repeated resolve() operations
        - UVX decision caching: Prevents expensive environment checks
        - Directory comparison caching: Optimizes same-directory detection

    Caching Behavior:
        - Path cache: Maps string paths to resolved Path objects
        - UVX cache: Stores single boolean decision for --add-dir usage
        - Cache lifetime: Lives for the duration of the launcher instance
        - Cache invalidation: Available through explicit methods

    Thread Safety:
        Not thread-safe. Use separate instances for concurrent launches.
    """

    def __init__(
        self,
        proxy_manager: Optional[ProxyManager] = None,
        append_system_prompt: Optional[Path] = None,
        force_staging: bool = False,
        checkout_repo: Optional[str] = None,
        claude_args: Optional[List[str]] = None,
    ):
        """Initialize Claude launcher.

        Args:
            proxy_manager: Optional proxy manager for Azure integration.
            append_system_prompt: Optional path to system prompt to append.
            force_staging: If True, force staging approach instead of --add-dir.
            checkout_repo: Optional GitHub repository URI to clone and use as working directory.
            claude_args: Additional arguments to forward to Claude.
        """
        self.proxy_manager = proxy_manager
        self.append_system_prompt = append_system_prompt
        self.detector = ClaudeDirectoryDetector()
        self.uvx_manager = UVXManager(force_staging=force_staging)
        self.checkout_repo = checkout_repo
        self.claude_args = claude_args or []
        self.claude_process: Optional[subprocess.Popen] = None

        # Cached computation results for performance optimization
        self._cached_resolved_paths = {}  # Cache for path resolution results
        self._cached_uvx_decision = None  # Cache for UVX --add-dir decision
        self._target_directory = None  # Target directory for --add-dir

    def prepare_launch(self) -> bool:
        """Prepare environment for launching Claude.

        Returns:
            True if preparation successful, False otherwise.
        """
        # 1. Check prerequisites first - fail fast with helpful guidance
        if not check_prerequisites():
            return False

        # 2. Handle repository checkout if needed
        if self.checkout_repo:
            if not self._handle_repo_checkout():
                return False

        # 3. Find and validate target directory
        target_dir = self._find_target_directory()
        if not target_dir:
            print("Failed to determine target directory")
            return False

        # 4. Handle directory change if needed (unless UVX with --add-dir)
        if not self._handle_directory_change(target_dir):
            return False

        # 5. Start proxy if needed
        return self._start_proxy_if_needed()

    def _handle_repo_checkout(self) -> bool:
        """Handle repository checkout.

        Returns:
            True if successful, False otherwise.
        """
        if not self.checkout_repo:
            print("No repository specified for checkout")
            return False

        try:
            repo_path = checkout_repository(self.checkout_repo)
            if not repo_path:
                print(f"Failed to checkout repository: {self.checkout_repo}")
                return False

            repo_path_obj = Path(repo_path)
            if not repo_path_obj.exists() or not repo_path_obj.is_dir():
                print(f"Checked out repository path is not accessible: {repo_path}")
                return False

            print(f"Successfully checked out repository to: {repo_path}")
            return True
        except Exception as e:
            print(f"Repository checkout failed: {e!s}")
            return False

    def _find_target_directory(self) -> Optional[Path]:
        """Find the target directory for execution.

        Returns:
            Target directory path, or None if not found.
        """
        # If we did a repo checkout, use current directory (where repo was checked out)
        if self.checkout_repo:
            return Path.cwd()

        # Find .claude directory in current or parent directories
        claude_dir = self.detector.find_claude_directory()
        if claude_dir:
            # Found .claude directory - use project root
            project_root = self.detector.get_project_root(claude_dir)
            if project_root.exists() and project_root.is_dir():
                return project_root
            print(f"Project root is not accessible: {project_root}")
            return None
        # No .claude directory found - use current directory
        return Path.cwd()

    def _handle_directory_change(self, target_dir: Path) -> bool:
        """Handle directory change based on execution mode.

        Args:
            target_dir: Target directory to change to

        Returns:
            True if successful, False otherwise.
        """
        current_dir = Path.cwd()

        # Check if we need to change directories (optimized comparison)
        try:
            same_dir = os.path.samefile(current_dir, target_dir)
        except (OSError, FileNotFoundError):
            # Fallback using cached resolved paths for efficiency
            same_dir = self._paths_are_same_with_cache(current_dir, target_dir)

        if same_dir:
            # Already in correct directory
            return True

        # In UVX mode, we've already changed to the temp directory in CLI
        # So we don't need to change directories again here

        # Standard directory change
        try:
            if not target_dir.exists() or not target_dir.is_dir():
                print(f"Target directory is not accessible: {target_dir}")
                return False

            os.chdir(target_dir)
            print(f"Changed directory to: {target_dir}")
            return True
        except OSError as e:
            print(f"Failed to change directory to {target_dir}: {e}")
            return False

    def _start_proxy_if_needed(self) -> bool:
        """Start proxy if configured.

        Returns:
            True if proxy started successfully or not needed, False otherwise.
        """
        if self.proxy_manager:
            print("Starting proxy and waiting for readiness...")
            if not self.proxy_manager.start_proxy():
                print("Failed to start proxy")
                return False

            # Verify proxy is actually ready before proceeding
            if not self.proxy_manager.is_running():
                print("Proxy is not running after startup")
                return False

            print(f"Proxy running at: {self.proxy_manager.get_proxy_url()}")

        return True

    def build_claude_command(self) -> List[str]:
        """Build the Claude command with arguments.

        Note: Prerequisites have already been validated before this is called,
        so Claude CLI is guaranteed to be available.

        Returns:
            List of command arguments for subprocess.
        """
        # Use claude-trace if requested and available, otherwise use claude
        claude_binary = get_claude_command()

        if claude_binary == "claude-trace":
            # claude-trace requires --run-with before Claude arguments
            cmd = [claude_binary]

            # Get claude binary path (already validated by prerequisites check)
            claude_path = get_claude_cli_path(auto_install=False)

            # Add --claude-path if we have a claude binary
            if claude_path:
                cmd.extend(["--claude-path", claude_path])

            claude_args = ["--dangerously-skip-permissions"]

            # Add system prompt if provided
            if self.append_system_prompt and self.append_system_prompt.exists():
                claude_args.extend(["--append-system-prompt", str(self.append_system_prompt)])

            # Add --add-dir arguments if UVX mode and we have a target directory
            # Use cached decision to avoid re-checking
            if self._target_directory and self._cached_uvx_decision:
                claude_args.extend(["--add-dir", str(self._target_directory)])

            # Add forwarded Claude arguments
            if self.claude_args:
                claude_args.extend(self.claude_args)

            # Add --run-with followed by all Claude arguments
            if claude_args:
                cmd.extend(["--run-with"] + claude_args)

            return cmd
        # Standard claude command
        cmd = [claude_binary, "--dangerously-skip-permissions"]

        # Add system prompt if provided
        if self.append_system_prompt and self.append_system_prompt.exists():
            cmd.extend(["--append-system-prompt", str(self.append_system_prompt)])

        # Add --add-dir arguments if UVX mode and we have a target directory
        # Use cached decision to avoid re-checking
        if self._target_directory and self._cached_uvx_decision:
            cmd.extend(["--add-dir", str(self._target_directory)])

        # Add forwarded Claude arguments
        if self.claude_args:
            cmd.extend(self.claude_args)

        return cmd

    def launch(self) -> int:
        """Launch Claude Code with configuration.

        Returns:
            Exit code from Claude process.
        """
        if not self.prepare_launch():
            return 1

        try:
            cmd = self.build_claude_command()
            print(f"Launching Claude with command: {' '.join(cmd)}")

            # Set up signal handling for graceful shutdown
            def signal_handler(sig, frame):
                print("\nReceived interrupt signal. Shutting down...")
                if self.claude_process:
                    self.claude_process.terminate()
                if self.proxy_manager:
                    self.proxy_manager.stop_proxy()
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)
            if sys.platform != "win32":
                signal.signal(signal.SIGTERM, signal_handler)

            # Set environment variables for UVX mode
            env = os.environ.copy()
            if self._target_directory:
                env.update(self.uvx_manager.get_environment_variables())
            # Pass through CLAUDE_PROJECT_DIR if set (for UVX temp environments)
            if "CLAUDE_PROJECT_DIR" in os.environ:
                env["CLAUDE_PROJECT_DIR"] = os.environ["CLAUDE_PROJECT_DIR"]

            # Include proxy environment variables if proxy is configured
            if self.proxy_manager and self.proxy_manager.is_running():
                proxy_env = self.proxy_manager.env_manager.get_proxy_env(
                    proxy_port=self.proxy_manager.proxy_port,
                    config=self.proxy_manager.proxy_config.to_env_dict()
                    if self.proxy_manager.proxy_config
                    else None,
                )
                # Update env with proxy settings, especially ANTHROPIC_BASE_URL
                if proxy_env.get("ANTHROPIC_BASE_URL"):
                    env["ANTHROPIC_BASE_URL"] = proxy_env["ANTHROPIC_BASE_URL"]
                    print(f"✓ Configured Claude to use proxy at {proxy_env['ANTHROPIC_BASE_URL']}")
                if proxy_env.get("ANTHROPIC_API_KEY"):
                    env["ANTHROPIC_API_KEY"] = proxy_env["ANTHROPIC_API_KEY"]

            # Launch Claude
            self.claude_process = subprocess.Popen(cmd, env=env)

            # Wait for Claude to finish
            exit_code = self.claude_process.wait()

            return exit_code

        except Exception as e:
            print(f"Error launching Claude: {e}")
            return 1
        finally:
            # Clean up proxy
            if self.proxy_manager:
                self.proxy_manager.stop_proxy()

    def launch_interactive(self) -> int:
        """Launch Claude in interactive mode with live output.

        Returns:
            Exit code from Claude process.
        """
        import time

        from .settings_manager import SettingsManager

        settings_manager = SettingsManager(
            settings_path=Path.home() / ".claude" / "settings.json",
            session_id=f"launch_{int(time.time())}",
            non_interactive=False,
        )

        if not self.prepare_launch():
            return 1

        try:
            cmd = self.build_claude_command()
            print(f"Launching Claude with command: {' '.join(cmd)}")

            # Set up signal handling for graceful shutdown
            def signal_handler(sig, frame):
                print("\nReceived interrupt signal. Shutting down...")
                if self.proxy_manager:
                    self.proxy_manager.stop_proxy()
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)
            if sys.platform != "win32":
                signal.signal(signal.SIGTERM, signal_handler)

            # Set environment variables for UVX mode
            env = os.environ.copy()
            if self._target_directory:
                env.update(self.uvx_manager.get_environment_variables())
            # Pass through CLAUDE_PROJECT_DIR if set (for UVX temp environments)
            if "CLAUDE_PROJECT_DIR" in os.environ:
                env["CLAUDE_PROJECT_DIR"] = os.environ["CLAUDE_PROJECT_DIR"]

            # Include proxy environment variables if proxy is configured
            if self.proxy_manager and self.proxy_manager.is_running():
                proxy_env = self.proxy_manager.env_manager.get_proxy_env(
                    proxy_port=self.proxy_manager.proxy_port,
                    config=self.proxy_manager.proxy_config.to_env_dict()
                    if self.proxy_manager.proxy_config
                    else None,
                )
                # Update env with proxy settings, especially ANTHROPIC_BASE_URL
                if proxy_env.get("ANTHROPIC_BASE_URL"):
                    env["ANTHROPIC_BASE_URL"] = proxy_env["ANTHROPIC_BASE_URL"]
                    print(f"✓ Configured Claude to use proxy at {proxy_env['ANTHROPIC_BASE_URL']}")
                if proxy_env.get("ANTHROPIC_API_KEY"):
                    env["ANTHROPIC_API_KEY"] = proxy_env["ANTHROPIC_API_KEY"]

            # Launch Claude with direct I/O (interactive mode)
            print("Starting Claude...")
            print(
                f"If Claude appears to hang, check proxy connection at: {self.proxy_manager.get_proxy_url() if self.proxy_manager else 'N/A'}"
            )
            exit_code = subprocess.call(cmd, env=env)

            return exit_code

        except Exception as e:
            print(f"Error launching Claude: {e}")
            return 1
        finally:
            # Restore settings.json backup if exists
            if settings_manager.backup_path:
                if settings_manager.restore_backup():
                    print("  ✅ Restored settings.json from backup")
                else:
                    print(
                        "  ⚠️  Could not restore settings.json - backup remains for manual recovery"
                    )

            # Clean up proxy
            if self.proxy_manager:
                self.proxy_manager.stop_proxy()

    def _paths_are_same_with_cache(self, path1: Path, path2: Path) -> bool:
        """Compare paths with caching for resolved paths.

        Args:
            path1: First path to compare
            path2: Second path to compare

        Returns:
            True if paths refer to the same location, False otherwise
        """

        def get_cached_resolved(path: Path) -> Path:
            """Get cached resolved path or compute and cache it."""
            path_key = str(path)
            if path_key not in self._cached_resolved_paths:
                self._cached_resolved_paths[path_key] = path.resolve()
            return self._cached_resolved_paths[path_key]

        return get_cached_resolved(path1) == get_cached_resolved(path2)

    def invalidate_path_cache(self) -> None:
        """Invalidate cached path resolutions.

        Call this when filesystem state may have changed or when
        working directory changes.
        """
        self._cached_resolved_paths.clear()

    def invalidate_uvx_cache(self) -> None:
        """Invalidate cached UVX decision.

        Call this when UVX environment may have changed.
        """
        self._cached_uvx_decision = None
