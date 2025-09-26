"""Core launcher functionality for Claude Code."""

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from ..proxy.manager import ProxyManager
from ..utils.claude_trace import get_claude_command
from ..uvx.manager import UVXManager
from .detector import ClaudeDirectoryDetector
from .repo_checkout import checkout_repository


class ClaudeLauncher:
    """Launches Claude Code with proper configuration."""

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

    def prepare_launch(self) -> bool:
        """Prepare environment for launching Claude.

        Returns:
            True if preparation successful, False otherwise.
        """
        # 1. Handle repository checkout if needed
        if self.checkout_repo:
            if not self._handle_repo_checkout():
                return False

        # 2. Find and validate target directory
        target_dir = self._find_target_directory()
        if not target_dir:
            print("Failed to determine target directory")
            return False

        # 3. Handle directory change if needed (unless UVX with --add-dir)
        if not self._handle_directory_change(target_dir):
            return False

        # 4. Start proxy if needed
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
            print(f"Repository checkout failed: {str(e)}")
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
            else:
                print(f"Project root is not accessible: {project_root}")
                return None
        else:
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
            # Fallback - cache resolved paths for efficiency
            if not hasattr(self, "_resolved_current") or self._resolved_current[0] != current_dir:
                self._resolved_current = (current_dir, current_dir.resolve())
            if not hasattr(self, "_resolved_target") or self._resolved_target[0] != target_dir:
                self._resolved_target = (target_dir, target_dir.resolve())
            same_dir = self._resolved_current[1] == self._resolved_target[1]

        if same_dir:
            # Already in correct directory
            return True

        # Check if we're in UVX mode and can use --add-dir (avoids directory change)
        # Cache the UVX decision to avoid repeated expensive checks
        if not hasattr(self, "_use_add_dir_cached"):
            self._use_add_dir_cached = self.uvx_manager.should_use_add_dir()

        if self._use_add_dir_cached:
            print("UVX environment detected - will use --add-dir approach")
            # Store target directory for --add-dir arguments
            self._target_directory = target_dir
            return True

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
            if not self.proxy_manager.start_proxy():
                print("Failed to start proxy")
                return False
            print(f"Proxy running at: {self.proxy_manager.get_proxy_url()}")

        return True

    def build_claude_command(self) -> List[str]:
        """Build the Claude command with arguments.

        Returns:
            List of command arguments for subprocess.
        """
        # Use claude-trace if requested and available, otherwise use claude
        claude_binary = get_claude_command()
        cmd = [claude_binary, "--dangerously-skip-permissions"]

        # Add system prompt if provided
        if self.append_system_prompt and self.append_system_prompt.exists():
            cmd.extend(["--append-system-prompt", str(self.append_system_prompt)])

        # Add --add-dir arguments if UVX mode and we have a target directory
        # Use cached decision to avoid re-checking
        if hasattr(self, "_target_directory") and getattr(self, "_use_add_dir_cached", False):
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
            if hasattr(self, "_target_directory"):
                env.update(self.uvx_manager.get_environment_variables())

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
            if hasattr(self, "_target_directory"):
                env.update(self.uvx_manager.get_environment_variables())

            # Launch Claude with direct I/O (interactive mode)
            exit_code = subprocess.call(cmd, env=env)

            return exit_code

        except Exception as e:
            print(f"Error launching Claude: {e}")
            return 1
        finally:
            # Clean up proxy
            if self.proxy_manager:
                self.proxy_manager.stop_proxy()
