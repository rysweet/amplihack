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
    ):
        """Initialize Claude launcher.

        Args:
            proxy_manager: Optional proxy manager for Azure integration.
            append_system_prompt: Optional path to system prompt to append.
            force_staging: If True, force staging approach instead of --add-dir.
            checkout_repo: Optional GitHub repository URI to clone and use as working directory.
        """
        self.proxy_manager = proxy_manager
        self.append_system_prompt = append_system_prompt
        self.detector = ClaudeDirectoryDetector()
        self.uvx_manager = UVXManager(force_staging=force_staging)
        self.checkout_repo = checkout_repo
        self.claude_process: Optional[subprocess.Popen] = None

    def prepare_launch(self) -> bool:
        """Prepare environment for launching Claude.

        Returns:
            True if preparation successful, False otherwise.
        """
        # Handle repository checkout if requested
        if self.checkout_repo:
            return self._handle_checkout_repo()

        # Check if we're in UVX mode and should use --add-dir instead of changing directories
        if self.uvx_manager.is_uvx_environment() and not self.uvx_manager.should_use_staging():
            print("UVX environment detected - will use --add-dir approach")
            # In UVX mode with --add-dir, we don't change the working directory
            # The session hook will handle directory changes after Claude starts
        else:
            # Standard directory detection and change logic
            claude_dir = self.detector.find_claude_directory()
            if claude_dir:
                print(f"Found .claude directory at: {claude_dir}")
                project_root = self.detector.get_project_root(claude_dir)

                # Only change directory if not already in project root
                try:
                    # Use samefile for efficient directory comparison
                    if not os.path.samefile(os.getcwd(), project_root):
                        os.chdir(project_root)
                        print(f"Changed directory to project root: {project_root}")
                    else:
                        print(f"Already in project root: {project_root}")
                except (OSError, FileNotFoundError):
                    # Fallback for non-existent paths or permission issues
                    current_dir = Path.cwd().resolve()
                    target_dir = Path(project_root).resolve()
                    if current_dir != target_dir:
                        os.chdir(project_root)
                        print(f"Changed directory to project root: {project_root}")
                    else:
                        print(f"Already in project root: {project_root}")
            else:
                print("No .claude directory found in current or parent directories")

        return self._start_proxy_if_needed()

    def _handle_checkout_repo(self) -> bool:
        """Handle repository checkout and directory change.

        Returns:
            True if checkout and preparation successful, False otherwise.
        """
        if not self.checkout_repo:
            print("No repository specified for checkout")
            return False

        repo_path = checkout_repository(self.checkout_repo)

        if not repo_path:
            print(f"Failed to checkout repository: {self.checkout_repo}")
            return False

        try:
            os.chdir(repo_path)
            print(f"Changed directory to cloned repository: {repo_path}")
        except Exception as e:
            print(f"Failed to change directory to {repo_path}: {e}")
            return False

        return self._start_proxy_if_needed()

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

        # Enhance command with UVX manager (adds --add-dir if appropriate)
        cmd = self.uvx_manager.enhance_claude_command(cmd)

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
