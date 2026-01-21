"""Core launcher functionality for Claude Code."""

import atexit
import logging
import os
import shlex
import signal
import subprocess
import sys
from pathlib import Path

from ..neo4j.manager import Neo4jManager
from ..proxy.manager import ProxyManager
from ..utils.claude_cli import get_claude_cli_path
from ..utils.claude_trace import get_claude_command
from ..utils.prerequisites import check_prerequisites
from ..uvx.manager import UVXManager
from .detector import ClaudeDirectoryDetector
from .repo_checkout import checkout_repository

logger = logging.getLogger(__name__)


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
        proxy_manager: ProxyManager | None = None,
        append_system_prompt: Path | None = None,
        force_staging: bool = False,
        checkout_repo: str | None = None,
        claude_args: list[str] | None = None,
        verbose: bool = False,
    ):
        """Initialize Claude launcher.

        Args:
            proxy_manager: Optional proxy manager for Azure integration.
            append_system_prompt: Optional path to system prompt to append.
            force_staging: If True, force staging approach instead of --add-dir.
            checkout_repo: Optional GitHub repository URI to clone and use as working directory.
            claude_args: Additional arguments to forward to Claude.
            verbose: If True, add --verbose flag to Claude command.
        """
        self.proxy_manager = proxy_manager
        self.append_system_prompt = append_system_prompt
        self.detector = ClaudeDirectoryDetector()
        self.uvx_manager = UVXManager(force_staging=force_staging)
        self.checkout_repo = checkout_repo
        self.claude_args = claude_args or []
        self.verbose = verbose
        self.claude_process: subprocess.Popen | None = None

        # Cached computation results for performance optimization
        self._cached_resolved_paths = {}  # Cache for path resolution results
        self._cached_uvx_decision = None  # Cache for UVX --add-dir decision
        self._target_directory = None  # Target directory for --add-dir

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

    def prepare_launch(self) -> bool:
        """Prepare environment for launching Claude.

        Returns:
            True if preparation successful, False otherwise.
        """
        # 1. Check prerequisites first - fail fast with helpful guidance
        if not check_prerequisites():
            return False

        # 2. Check and sync Neo4j credentials from existing containers (if any)
        self._check_neo4j_credentials()

        # 3. Interactive Neo4j startup (blocks until ready or user decides)
        if not self._interactive_neo4j_startup():
            # User chose to exit rather than continue without Neo4j
            return False

        # 4. Handle repository checkout if needed
        if self.checkout_repo:
            if not self._handle_repo_checkout():
                return False

        # 5. Find and validate target directory
        target_dir = self._find_target_directory()
        if not target_dir:
            print("Failed to determine target directory")
            return False

        # 6. Ensure required runtime directories exist
        if not self._ensure_runtime_directories(target_dir):
            print("Warning: Could not create runtime directories")
            # Don't fail - just warn

        # 7. Fix hook paths in settings.json to use absolute paths
        if not self._fix_hook_paths_in_settings(target_dir):
            print("Warning: Could not fix hook paths in settings.json")
            # Don't fail - hooks might still work

        # 8. Handle directory change if needed (unless UVX with --add-dir)
        if not self._handle_directory_change(target_dir):
            return False

        # 9. Start proxy if needed
        if not self._start_proxy_if_needed():
            return False

        # 10. Auto-configure LSP if supported languages detected
        self._configure_lsp_auto(target_dir)

        return True

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

    def _find_target_directory(self) -> Path | None:
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

            # Open terminal window tailing proxy logs
            self._open_log_tail_window()

        return True

    def _configure_lsp_auto(self, target_dir: Path) -> None:
        """Auto-configure LSP using Claude Code plugin marketplace.

        Automatically configures LSP by:
        1. Detecting languages in target directory
        2. Setting ENABLE_LSP_TOOL=1 environment variable
        3. Adding plugin marketplace (boostvolt/claude-code-lsps)
        4. Installing LSP plugins via claude plugin install

        Args:
            target_dir: Project directory to configure LSP for

        Note:
            Silently skips if LSP modules not available or if no languages detected.
            This is a best-effort enhancement - failure doesn't block Claude launch.
        """
        try:
            import subprocess
            import sys

            # Add .claude/skills to Python path
            claude_dir = target_dir / ".claude" / "skills"
            if claude_dir.exists() and str(claude_dir) not in sys.path:
                sys.path.insert(0, str(claude_dir))

            from lsp_setup import (  # type: ignore[import-not-found]
                LanguageDetector,
                LSPConfigurator,
            )

            # Step 1: Detect languages
            detector = LanguageDetector(target_dir)
            languages_dict = detector.detect_languages()

            if not languages_dict:
                return

            lang_names = list(languages_dict.keys())
            print(f"📡 LSP: Detected {len(lang_names)} language(s): {', '.join(lang_names[:3])}...")

            # Step 2: Set environment variable
            os.environ["ENABLE_LSP_TOOL"] = "1"

            # Step 3: Configure .env file
            configurator = LSPConfigurator(target_dir)
            if not configurator.is_lsp_enabled():
                configurator.enable_lsp()
                print("📡 LSP: Enabled ENABLE_LSP_TOOL=1 in .env")

            # Step 4: Check and install system LSP binaries (required for plugins to work)
            binaries_to_install = {
                "python": "pyright",
                "typescript": "typescript-language-server",
                "javascript": "typescript-language-server",
                "rust": "rust-analyzer",
            }

            for lang in lang_names[:3]:
                binary = binaries_to_install.get(lang)
                if (
                    binary
                    and subprocess.run(["which", binary], capture_output=True).returncode != 0
                ):
                    # Try to install via npm (for most LSP servers)
                    try:
                        subprocess.run(
                            ["npm", "install", "-g", binary], capture_output=True, timeout=60
                        )
                        print(f"📡 LSP: Installed {binary}")
                    except (subprocess.TimeoutExpired, Exception):
                        pass

            # Step 5: Add plugin marketplace
            try:
                subprocess.run(
                    ["claude", "plugin", "marketplace", "add", "boostvolt/claude-code-lsps"],
                    capture_output=True,
                    timeout=30,
                )
                print("📡 LSP: Added plugin marketplace")
            except (subprocess.TimeoutExpired, Exception):
                pass

            # Step 5: Install plugins (map languages to plugin names)
            plugin_map = {
                "python": "pyright",
                "typescript": "vtsls",
                "javascript": "vtsls",
                "rust": "rust-analyzer",
                "go": "gopls",
                "java": "jdtls",
                "cpp": "clangd",
                "c": "clangd",
                "ruby": "ruby-lsp",
                "php": "phpactor",
            }

            installed = 0
            for lang in lang_names[:3]:
                plugin_name = plugin_map.get(lang)
                if not plugin_name:
                    continue

                try:
                    result = subprocess.run(
                        [
                            "claude",
                            "plugin",
                            "install",
                            f"{plugin_name}@claude-code-lsps",
                            "--scope",
                            "project",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=str(target_dir),
                    )
                    if result.returncode == 0:
                        installed += 1
                        print(f"📡 LSP: Installed {plugin_name} plugin")
                    else:
                        print(
                            f"📡 LSP: Failed to install {plugin_name}: {result.stderr.strip()[:100]}"
                        )
                except Exception as e:
                    print(f"📡 LSP: Error installing {plugin_name}: {e}")

            if installed == 0:
                print("📡 LSP: No plugins installed (system LSP binaries + marketplace configured)")

        except Exception as e:
            logger.debug(f"LSP auto-configuration skipped: {e}")

    def _open_log_tail_window(self) -> None:
        """Open a new terminal window tailing proxy logs.

        This method spawns a new terminal window (macOS Terminal.app on Darwin)
        that tails both stdout and stderr proxy log files. The terminal window
        remains open even after Claude exits, allowing for post-mortem debugging.

        Platform Support:
            - macOS (Darwin): Uses osascript to open Terminal.app
            - Other platforms: Not yet implemented (gracefully skips)

        Error Handling:
            Errors are logged but do not fail the proxy startup process.
        """
        # Only supported on macOS for now
        if sys.platform != "darwin":
            return

        try:
            # Get log directory
            log_dir = Path("/tmp/amplihack_logs")
            if not log_dir.exists():
                print("Log directory does not exist, skipping log tail window")
                return

            # Find the most recent log files (they were just created)
            # We use glob pattern to match any timestamp
            stdout_logs = list(log_dir.glob("proxy-stdout-*.log"))
            stderr_logs = list(log_dir.glob("proxy-stderr-*.log"))

            if not stdout_logs or not stderr_logs:
                print("Could not find proxy log files, skipping log tail window")
                return

            # Sort by modification time and get the most recent
            stdout_log = sorted(stdout_logs, key=lambda p: p.stat().st_mtime)[-1]
            stderr_log = sorted(stderr_logs, key=lambda p: p.stat().st_mtime)[-1]

            # Build the tail command that follows both files
            # Using tail -f to follow files as they grow
            # Use shlex.quote() to prevent command injection via log file paths
            tail_cmd = f"tail -f {shlex.quote(str(stdout_log))} {shlex.quote(str(stderr_log))}"

            # AppleScript to open a new Terminal window with the tail command
            # We use 'do script' to execute the command in a new window
            applescript = f'''
            tell application "Terminal"
                activate
                do script "{tail_cmd}"
            end tell
            '''

            # Execute osascript in the background (non-blocking)
            subprocess.Popen(
                ["osascript", "-e", applescript],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            print("Opened terminal window tailing proxy logs")
            print(f"  stdout: {stdout_log.name}")
            print(f"  stderr: {stderr_log.name}")

        except Exception as e:
            # Log error but don't fail proxy startup
            print(f"Warning: Could not open log tail window: {e}")

    def _has_model_arg(self) -> bool:
        """Check if user has already specified --model in claude_args.

        Returns:
            True if --model is present in self.claude_args, False otherwise.
        """
        if not self.claude_args:
            return False
        return "--model" in self.claude_args

    def _get_azure_model(self) -> str:
        """Extract Azure model name from proxy configuration.

        Reads from proxy config in priority order:
        1. BIG_MODEL (primary deployment model)
        2. AZURE_OPENAI_DEPLOYMENT_NAME (fallback deployment name)
        3. "gpt-5-codex" (hardcoded fallback)

        Returns:
            Azure model deployment name.
        """
        if not self.proxy_manager or not self.proxy_manager.proxy_config:
            return "gpt-5-codex"

        proxy_config = self.proxy_manager.proxy_config
        return (
            proxy_config.get("BIG_MODEL")
            or proxy_config.get("AZURE_OPENAI_DEPLOYMENT_NAME")
            or "gpt-5-codex"
        )

    def build_claude_command(self) -> list[str]:
        """Build the Claude command with arguments.

        Note: Prerequisites have already been validated before this is called,
        so Claude CLI is guaranteed to be available.

        Returns:
            List of command arguments for subprocess.
        """
        # Get claude command (could be claude, claude-trace, or rustyclawd)
        claude_binary = get_claude_command()

        # Check if this is RustyClawd (Rust implementation)
        is_rustyclawd = "rustyclawd" in claude_binary.lower() or "claude-code-rs" in claude_binary

        if is_rustyclawd:
            # RustyClawd has same CLI as claude (simpler than claude-trace)
            cmd = [claude_binary, "--dangerously-skip-permissions"]

            # Add --verbose if requested
            if self.verbose:
                cmd.append("--verbose")

            # Add system prompt if provided
            if self.append_system_prompt and self.append_system_prompt.exists():
                cmd.extend(["--append-system-prompt", str(self.append_system_prompt)])

            # Add --add-dir if in UVX mode
            if self._target_directory and self._cached_uvx_decision:
                cmd.extend(["--add-dir", str(self._target_directory)])

            # Add Azure model when using proxy
            if self.proxy_manager:
                azure_model = self._get_azure_model()
                cmd.extend(["--model", f"azure/{azure_model}"])
            # Add default model if not using proxy and user hasn't specified one
            elif not self._has_model_arg():
                default_model = os.getenv("AMPLIHACK_DEFAULT_MODEL", "sonnet[1m]")
                cmd.extend(["--model", default_model])

            # Add forwarded arguments
            if self.claude_args:
                cmd.extend(self.claude_args)

            return cmd

        if claude_binary == "claude-trace":
            # claude-trace requires --run-with before Claude arguments
            cmd = [claude_binary]

            # Get claude binary path (already validated by prerequisites check)
            claude_path = get_claude_cli_path(auto_install=False)

            # Add --claude-path if we have a claude binary
            if claude_path:
                cmd.extend(["--claude-path", claude_path])

            claude_args = ["--dangerously-skip-permissions"]

            # Add --verbose flag only if requested (auto mode)
            if self.verbose:
                claude_args.append("--verbose")

            # Add system prompt if provided
            if self.append_system_prompt and self.append_system_prompt.exists():
                claude_args.extend(["--append-system-prompt", str(self.append_system_prompt)])

            # Add --add-dir arguments if UVX mode and we have a target directory
            # Use cached decision to avoid re-checking
            if self._target_directory and self._cached_uvx_decision:
                claude_args.extend(["--add-dir", str(self._target_directory)])

            # Add Azure model when using proxy
            if self.proxy_manager:
                azure_model = self._get_azure_model()
                claude_args.extend(["--model", f"azure/{azure_model}"])
            # Add default model if not using proxy and user hasn't specified one
            elif not self._has_model_arg():
                default_model = os.getenv("AMPLIHACK_DEFAULT_MODEL", "sonnet[1m]")
                claude_args.extend(["--model", default_model])

            # Add forwarded Claude arguments
            if self.claude_args:
                claude_args.extend(self.claude_args)

            # Add --run-with followed by all Claude arguments
            if claude_args:
                cmd.extend(["--run-with"] + claude_args)

            return cmd
        # Standard claude command
        cmd = [claude_binary, "--dangerously-skip-permissions"]

        # Add --verbose flag only if requested (auto mode)
        if self.verbose:
            cmd.append("--verbose")

        # Add system prompt if provided
        if self.append_system_prompt and self.append_system_prompt.exists():
            cmd.extend(["--append-system-prompt", str(self.append_system_prompt)])

        # Add --add-dir arguments if UVX mode and we have a target directory
        # Use cached decision to avoid re-checking
        if self._target_directory and self._cached_uvx_decision:
            cmd.extend(["--add-dir", str(self._target_directory)])

        # Add Azure model when using proxy
        if self.proxy_manager:
            azure_model = self._get_azure_model()
            cmd.extend(["--model", f"azure/{azure_model}"])
        # Add default model if not using proxy and user hasn't specified one
        elif not self._has_model_arg():
            default_model = os.getenv("AMPLIHACK_DEFAULT_MODEL", "sonnet[1m]")
            cmd.extend(["--model", default_model])

        # Add forwarded Claude arguments
        if self.claude_args:
            cmd.extend(self.claude_args)

        return cmd

    def _ensure_runtime_directories(self, target_dir: Path) -> bool:
        """Ensure required runtime directories exist.

        Creates:
        - .claude/runtime/locks (for lock-based continuous work)
        - .claude/runtime/reflection (for reflection system)
        - .claude/runtime/logs (for session logs)
        - .claude/runtime/metrics (for hook metrics)

        Args:
            target_dir: Project root directory

        Returns:
            True if successful, False on error
        """
        try:
            runtime_dir = target_dir / ".claude" / "runtime"

            # Create all required directories
            required_dirs = [
                runtime_dir / "locks",
                runtime_dir / "reflection",
                runtime_dir / "logs",
                runtime_dir / "metrics",
            ]

            for dir_path in required_dirs:
                dir_path.mkdir(parents=True, exist_ok=True)

            print(f"✓ Runtime directories ensured in {runtime_dir}")
            return True

        except (OSError, PermissionError) as e:
            print(f"Warning: Could not create runtime directories: {e}")
            return False

    def _fix_hook_paths_in_settings(self, target_dir: Path) -> bool:
        """Fix hook paths in settings.json to use absolute paths.

        Replaces $CLAUDE_PROJECT_DIR with actual absolute project path.
        This ensures hooks work reliably even when Claude Code doesn't
        properly evaluate environment variables.

        Args:
            target_dir: Project root directory

        Returns:
            True if successful or no changes needed, False on error
        """
        import json

        settings_file = target_dir / ".claude" / "settings.json"

        if not settings_file.exists():
            # No settings file, nothing to fix
            return True

        try:
            # Read current settings
            with open(settings_file) as f:
                settings = json.load(f)

            # Check if hooks exist and contain $CLAUDE_PROJECT_DIR
            if "hooks" not in settings:
                return True

            hooks_modified = False
            project_dir_str = str(target_dir.resolve())

            # Recursively replace $CLAUDE_PROJECT_DIR in hook commands
            def replace_in_hooks(obj):
                nonlocal hooks_modified
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key == "command" and isinstance(value, str):
                            if "$CLAUDE_PROJECT_DIR" in value:
                                obj[key] = value.replace("$CLAUDE_PROJECT_DIR", project_dir_str)
                                hooks_modified = True
                        else:
                            replace_in_hooks(value)
                elif isinstance(obj, list):
                    for item in obj:
                        replace_in_hooks(item)

            replace_in_hooks(settings["hooks"])

            if hooks_modified:
                # Write back with absolute paths
                with open(settings_file, "w") as f:
                    json.dump(settings, f, indent=2)
                print(f"✓ Fixed hook paths in {settings_file.relative_to(target_dir)}")

            return True

        except (OSError, json.JSONDecodeError, PermissionError) as e:
            print(f"Warning: Could not fix hook paths: {e}")
            return False

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

            # Smart memory configuration
            from .memory_config import display_memory_config, get_memory_config

            memory_config = get_memory_config(env.get("NODE_OPTIONS"))
            if memory_config and "node_options" in memory_config:
                env["NODE_OPTIONS"] = memory_config["node_options"]
                # Display configuration on launch
                display_memory_config(memory_config)
            else:
                # Fallback to 8GB if detection fails
                env["NODE_OPTIONS"] = "--max-old-space-size=8192"

            if self._target_directory:
                env.update(self.uvx_manager.get_environment_variables())
            # Pass through CLAUDE_PROJECT_DIR if set (for UVX temp environments)
            if "CLAUDE_PROJECT_DIR" in os.environ:
                env["CLAUDE_PROJECT_DIR"] = os.environ["CLAUDE_PROJECT_DIR"]

            # Export CLAUDE_PLUGIN_ROOT for plugin discoverability
            # Check if plugin was installed via Claude Code (AMPLIHACK_PLUGIN_INSTALLED set by cli.py)
            if os.environ.get("AMPLIHACK_PLUGIN_INSTALLED") == "true":
                # Plugin installed via Claude Code - use installed plugin path
                installed_plugin_path = Path.home() / ".claude" / "plugins" / "cache" / "amplihack" / "amplihack" / "0.9.0"
                env["CLAUDE_PLUGIN_ROOT"] = str(installed_plugin_path)
            else:
                # Directory copy mode - use ~/.amplihack/.claude/
                plugin_root = Path.home() / ".amplihack" / ".claude"
                if plugin_root.exists():
                    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)

            # Ensure user-local npm bin is in PATH (for claude/claude-trace installed via npm)
            user_npm_bin = str(Path.home() / ".npm-global" / "bin")
            current_path = env.get("PATH", "")
            if user_npm_bin not in current_path:
                env["PATH"] = f"{user_npm_bin}:{current_path}"

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
                # Set shutdown flag BEFORE sys.exit to coordinate with hooks
                # Prevents BrokenPipeError in sessionstop hook during interrupt shutdown
                os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
                if self.proxy_manager:
                    self.proxy_manager.stop_proxy()
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)
            if sys.platform != "win32":
                signal.signal(signal.SIGTERM, signal_handler)

            # Set environment variables for UVX mode
            env = os.environ.copy()

            # Smart memory configuration
            from .memory_config import display_memory_config, get_memory_config

            memory_config = get_memory_config(env.get("NODE_OPTIONS"))
            if memory_config and "node_options" in memory_config:
                env["NODE_OPTIONS"] = memory_config["node_options"]
                # Display configuration on launch
                display_memory_config(memory_config)
            else:
                # Fallback to 8GB if detection fails
                env["NODE_OPTIONS"] = "--max-old-space-size=8192"

            if self._target_directory:
                env.update(self.uvx_manager.get_environment_variables())
            # Pass through CLAUDE_PROJECT_DIR if set (for UVX temp environments)
            if "CLAUDE_PROJECT_DIR" in os.environ:
                env["CLAUDE_PROJECT_DIR"] = os.environ["CLAUDE_PROJECT_DIR"]

            # Export CLAUDE_PLUGIN_ROOT for plugin discoverability
            # Check if plugin was installed via Claude Code (AMPLIHACK_PLUGIN_INSTALLED set by cli.py)
            if os.environ.get("AMPLIHACK_PLUGIN_INSTALLED") == "true":
                # Plugin installed via Claude Code - use installed plugin path
                installed_plugin_path = Path.home() / ".claude" / "plugins" / "cache" / "amplihack" / "amplihack" / "0.9.0"
                env["CLAUDE_PLUGIN_ROOT"] = str(installed_plugin_path)
            else:
                # Directory copy mode - use ~/.amplihack/.claude/
                plugin_root = Path.home() / ".amplihack" / ".claude"
                if plugin_root.exists():
                    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)

            # Ensure user-local npm bin is in PATH (for claude/claude-trace installed via npm)
            user_npm_bin = str(Path.home() / ".npm-global" / "bin")
            current_path = env.get("PATH", "")
            if user_npm_bin not in current_path:
                env["PATH"] = f"{user_npm_bin}:{current_path}"

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

    def _interactive_neo4j_startup(self) -> bool:
        """Interactive Neo4j startup with user feedback.

        BLOCKS until Neo4j ready or user decides to continue without it.
        Neo4j is disabled by default unless AMPLIHACK_ENABLE_NEO4J_MEMORY=1 is set.

        Returns:
            True to continue, False to exit
        """
        import logging

        method_logger = logging.getLogger(__name__)

        # Check if Neo4j is enabled via environment variable (default: disabled)
        neo4j_enabled = os.environ.get("AMPLIHACK_ENABLE_NEO4J_MEMORY") == "1"

        if not neo4j_enabled:
            # Neo4j disabled - skip interactive startup entirely
            return True

        try:
            from ..memory.neo4j.startup_wizard import interactive_neo4j_startup

            return interactive_neo4j_startup()
        except ImportError:
            # Neo4j modules not available - continue without
            method_logger.debug("Neo4j modules not found")
            return True
        except Exception as e:
            method_logger.error("Neo4j startup failed: %s", e)
            print(f"\n⚠️  Neo4j startup error: {e}")
            print("Continuing with basic memory system...\n")
            return True

    def _auto_setup_and_start_neo4j_OLD(self):
        """Auto-setup prerequisites and start Neo4j in background.

        Self-healing approach:
        - Creates .env with password if missing
        - Starts Docker if not running
        - Starts Neo4j container
        All in background thread, non-blocking.
        """
        import threading

        def start_neo4j():
            """Background thread function with auto-setup."""
            import logging

            thread_logger = logging.getLogger(__name__)

            try:
                # Auto-setup prerequisites
                from ..memory.neo4j.auto_setup import ensure_prerequisites

                if not ensure_prerequisites():
                    thread_logger.warning("Neo4j prerequisites not met, falling back to SQLite")
                    return

                # Start Neo4j
                from ..memory.neo4j.diagnostics import verify_neo4j_working
                from ..memory.neo4j.lifecycle import ensure_neo4j_running

                thread_logger.info("Starting Neo4j memory system...")
                if ensure_neo4j_running(blocking=True):
                    # Verify and show stats
                    verify_neo4j_working()

            except Exception as e:
                # Never crash session start due to Neo4j issues
                thread_logger.warning("Neo4j initialization error: %s", e)
                thread_logger.info("Continuing with existing memory system")

        # Start in background thread
        thread = threading.Thread(
            target=start_neo4j,
            name="neo4j-startup",
            daemon=True,  # Don't block process exit
        )
        thread.start()

        # Don't wait - return immediately

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

    def _check_neo4j_credentials(self) -> None:
        """Check and sync Neo4j credentials from containers.

        Neo4j is disabled by default unless AMPLIHACK_ENABLE_NEO4J_MEMORY=1 is set.
        """
        # Check if Neo4j is enabled via environment variable (default: disabled)
        neo4j_enabled = os.environ.get("AMPLIHACK_ENABLE_NEO4J_MEMORY") == "1"

        if not neo4j_enabled:
            # Neo4j disabled - skip credential check entirely
            return

        try:
            # Create Neo4j manager (interactive mode)
            neo4j_manager = Neo4jManager()

            # Check and sync credentials if needed
            neo4j_manager.check_and_sync()

        except Exception:
            # Graceful degradation - never crash launcher
            # No error message needed as Neo4j detection is optional
            pass

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown.

        Registers handlers for SIGINT (Ctrl-C) and SIGTERM that:
        1. Trigger Neo4j cleanup via stop hook
        2. Allow process to exit gracefully

        Also registers atexit handler as fallback.
        """

        def signal_handler(signum: int, frame) -> None:
            """Handle shutdown signals."""
            signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
            logger.info(f"Received {signal_name}, initiating graceful shutdown...")

            # Trigger Neo4j cleanup via stop hook
            try:
                from amplihack.hooks.manager import execute_stop_hook

                logger.info("Executing stop hook for cleanup...")
                execute_stop_hook()
            except Exception as e:
                logger.warning(f"Stop hook execution failed: {e}")

            # Exit gracefully
            logger.info("Graceful shutdown complete")
            sys.exit(0)

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Also register atexit handler as fallback
        atexit.register(self._cleanup_on_exit)

        logger.debug("Signal handlers registered for graceful shutdown")

    def _cleanup_on_exit(self) -> None:
        """Fallback cleanup handler for atexit.

        This is a fail-safe that runs when the process exits normally
        without receiving signals. Executes stop hook silently.
        """
        try:
            # Set shutdown flag BEFORE executing stop hook to prevent stdin blocking
            os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

            from amplihack.hooks.manager import execute_stop_hook

            execute_stop_hook()
        except Exception:
            # Fail silently in atexit - cleanup is best-effort
            pass
