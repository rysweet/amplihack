"""Core launcher functionality for Claude Code."""

import atexit
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

from ..tracing.trace_logger import TraceLogger
from ..utils.claude_cli import get_claude_cli_path
from ..utils.prerequisites import check_prerequisites
from ..uvx.manager import UVXManager
from .claude_binary_manager import ClaudeBinaryManager
from .detector import ClaudeDirectoryDetector
from .repo_checkout import checkout_repository

logger = logging.getLogger(__name__)


def get_claude_command() -> str:
    """Compatibility wrapper used by tracing tests."""
    return get_claude_cli_path(auto_install=False) or "claude"


def _is_noninteractive() -> bool:
    """Check if running in non-interactive mode.

    Non-interactive mode is triggered by:
    - AMPLIHACK_NONINTERACTIVE=1 environment variable
    - No TTY on stdin (e.g., sandboxed/isolated environments)
    - Sandboxed environment detected (isolated HOME, restricted PATH)

    In non-interactive mode, the launcher:
    - Skips interactive prompts
    - Skips auto-update and auto-install checks
    - Uses shorter timeouts for network operations
    - Fails fast when claude binary is not found

    Returns:
        True if running in non-interactive mode.
    """
    # Explicit environment variable takes priority
    if os.environ.get("AMPLIHACK_NONINTERACTIVE", "").strip() in ("1", "true", "yes"):
        return True

    # No TTY means non-interactive
    try:
        if sys.stdin is None or not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
            return True
    except (AttributeError, OSError):
        return True

    # Detect sandboxed environments (isolated HOME, restricted PATH)
    if _is_sandboxed():
        return True

    return False


def _is_sandboxed() -> bool:
    """Detect sandboxed/isolated environments that may cause hangs.

    Checks for:
    - HOME pointing to a non-standard or missing directory
    - PATH missing critical system directories (/usr/bin, /bin)
    - CI/container environment variables

    Returns:
        True if a sandboxed environment is detected.
    """
    # CI/container environment markers
    ci_vars = ("CI", "GITHUB_ACTIONS", "JENKINS_URL", "GITLAB_CI", "CODESPACES")
    if any(os.environ.get(v) for v in ci_vars):
        return True

    # HOME doesn't exist or is not a writable directory
    home = os.environ.get("HOME", "")
    if not home or not os.path.isdir(home):
        return True
    try:
        if not os.access(home, os.W_OK):
            return True
    except OSError:
        return True

    # PATH missing essential system directories
    path = os.environ.get("PATH", "")
    if not any(d in path for d in ("/usr/bin", "/bin")):
        return True

    return False


class ClaudeLauncher:
    """Launches Claude Code with proper configuration and performance optimization.

    This class manages the complete Claude Code launch process including:
    - Repository checkout and directory management
    - UVX environment detection and --add-dir integration
    - Environment configuration for Azure integration
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
        append_system_prompt: Path | None = None,
        force_staging: bool = False,
        checkout_repo: str | None = None,
        claude_args: list[str] | None = None,
        verbose: bool = False,
    ):
        """Initialize Claude launcher.

        Args:
            append_system_prompt: Optional path to system prompt to append.
            force_staging: If True, force staging approach instead of --add-dir.
            checkout_repo: Optional GitHub repository URI to clone and use as working directory.
            claude_args: Additional arguments to forward to Claude.
            verbose: If True, add --verbose flag to Claude command.
        """
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

        # Native binary manager for detection and command building
        self.binary_manager = ClaudeBinaryManager()

        # Optional trace logger (initialized if tracing enabled)
        self.trace_logger: TraceLogger | None = None

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

    def prepare_launch(self) -> bool:
        """Prepare environment for launching Claude.

        Returns:
            True if preparation successful, False otherwise.
        """
        noninteractive = _is_noninteractive()

        if noninteractive:
            logger.info("Non-interactive mode: skipping interactive prompts and auto-install")

        # 1. Check prerequisites first - fail fast with helpful guidance
        # In non-interactive mode, skip auto-install to avoid blocking
        if noninteractive:
            if not self._check_prerequisites_noninteractive():
                return False
        else:
            if not check_prerequisites():
                return False

        # 2. Initialize TraceLogger if enabled
        self.trace_logger = TraceLogger.from_env()
        if self.trace_logger.enabled:
            print(f"Trace logging enabled: {self.trace_logger.log_file}")

        # 3. Blarify code indexing (non-blocking, failure doesn't stop launch)
        # Skip entirely in non-interactive mode (requires user prompts)
        if not noninteractive:
            if not self._prompt_blarify_indexing():
                logger.info("Blarify indexing skipped")

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

        # 9. Auto-configure LSP if supported languages detected
        # Skip in non-interactive mode (involves npm installs and network calls)
        if not noninteractive:
            self._configure_lsp_auto(target_dir)

        return True

    def _check_prerequisites_noninteractive(self) -> bool:
        """Check prerequisites in non-interactive mode.

        In non-interactive mode:
        - Does NOT attempt auto-installation of missing tools
        - Uses short timeouts (5s) for all checks
        - Fails fast if claude binary is not found
        - Never prompts for user input

        Returns:
            True if all critical prerequisites available, False otherwise.
        """

        from ..utils.prerequisites import PrerequisiteChecker

        checker = PrerequisiteChecker()

        # Check standard tools (node, npm, uv, git, rg) with short timeouts
        missing = []
        for tool, version_arg in checker.REQUIRED_TOOLS.items():
            result = checker.check_tool(tool, version_arg)
            if not result.available:
                missing.append(tool)

        # Check for claude binary - NO auto-install in non-interactive mode
        claude_path = get_claude_cli_path(auto_install=False)
        if not claude_path:
            print(
                "ERROR: Claude CLI not found. "
                "Install it or set AMPLIHACK_NONINTERACTIVE=0 to enable auto-install."
            )
            return False

        if missing:
            print(f"Warning: Missing optional tools: {', '.join(missing)}")
            print("Continuing in non-interactive mode...")

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

    def _has_model_arg(self) -> bool:
        """Check if user has already specified --model in claude_args.

        Returns:
            True if --model is present in self.claude_args, False otherwise.
        """
        if not self.claude_args:
            return False
        return "--model" in self.claude_args

    def build_claude_command(self) -> list[str]:
        """Build the Claude command with arguments.

        Note: Prerequisites have already been validated before this is called,
        so Claude CLI is guaranteed to be available.

        Returns:
            List of command arguments for subprocess.
        """
        # Detect native binary using ClaudeBinaryManager
        binary = self.binary_manager.detect_native_binary()

        # Fall back to standard claude if no native binary found
        if not binary:
            # Use standard claude CLI path
            claude_path = get_claude_cli_path(auto_install=False)
            if not claude_path:
                # This shouldn't happen after prerequisite checks, but be defensive
                raise RuntimeError("No Claude binary found. Please install Claude CLI.")

            # Build standard claude command
            is_copilot = os.getenv("AMPLIHACK_AGENT_BINARY", "") == "copilot"
            cmd = [claude_path] if is_copilot else [claude_path, "--dangerously-skip-permissions"]

            # Add --verbose if requested
            if self.verbose:
                cmd.append("--verbose")

            # Add system prompt if provided
            if self.append_system_prompt and self.append_system_prompt.exists():
                cmd.extend(["--append-system-prompt", str(self.append_system_prompt)])

            # Add --add-dir if in UVX mode
            if self._target_directory and self._cached_uvx_decision:
                cmd.extend(["--add-dir", str(self._target_directory)])

            # Add default model if user hasn't specified one
            if not self._has_model_arg():
                default_model = os.getenv("AMPLIHACK_DEFAULT_MODEL", "opus[1m]")
                cmd.extend(["--model", default_model])

            # Add forwarded arguments
            if self.claude_args:
                cmd.extend(self.claude_args)

            return cmd

        # Use native binary (rustyclawd, etc.)
        print(f"Using native binary: {binary.name} at {binary.path}")
        if binary.version:
            print(f"Version: {binary.version}")

        # Prepare trace file path if tracing is enabled
        trace_file = None
        if self.trace_logger and self.trace_logger.enabled:
            trace_file = str(self.trace_logger.log_file) if self.trace_logger.log_file else None

        # Build base command with trace support if available
        cmd = self.binary_manager.build_command(
            binary,
            enable_trace=self.trace_logger.enabled if self.trace_logger else False,
            trace_file=trace_file,
        )

        # Add standard Claude CLI arguments (not supported by copilot binary)
        is_copilot = binary.name == "copilot" or os.getenv("AMPLIHACK_AGENT_BINARY", "") == "copilot"
        if not is_copilot:
            cmd.append("--dangerously-skip-permissions")

        # Add --verbose if requested
        if self.verbose:
            cmd.append("--verbose")

        # Add system prompt if provided
        if self.append_system_prompt and self.append_system_prompt.exists():
            cmd.extend(["--append-system-prompt", str(self.append_system_prompt)])

        # Add --add-dir if in UVX mode
        if self._target_directory and self._cached_uvx_decision:
            cmd.extend(["--add-dir", str(self._target_directory)])

        # Add default model if user hasn't specified one
        if not self._has_model_arg():
            default_model = os.getenv("AMPLIHACK_DEFAULT_MODEL", "opus[1m]")
            cmd.extend(["--model", default_model])

        # Add forwarded arguments
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
                # Write back with absolute paths (atomic to prevent data loss)
                from ..settings import write_json_atomic

                write_json_atomic(str(settings_file), settings)
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

        # Auto-update to latest version before launching (fixes #3097)
        # Skip in non-interactive/sandboxed mode to avoid hangs
        if not _is_noninteractive():
            try:
                from ..utils.claude_cli import ensure_latest_claude

                ensure_latest_claude()
            except Exception:
                pass  # non-critical — continue with current version

        try:
            cmd = self.build_claude_command()
            print(f"Launching Claude with command: {' '.join(cmd)}")

            # Set up signal handling for graceful shutdown
            def signal_handler(sig, frame):
                print("\nReceived interrupt signal. Shutting down...")
                if self.claude_process:
                    self.claude_process.terminate()
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)
            if sys.platform != "win32":
                signal.signal(signal.SIGTERM, signal_handler)

            # Set environment variables for UVX mode
            env = os.environ.copy()

            # Set agent identity and home directory for Rust CLI parity
            env["AMPLIHACK_AGENT_BINARY"] = "claude"
            env.setdefault("AMPLIHACK_HOME", os.path.expanduser("~/.amplihack"))

            # Smart memory configuration
            from .memory_config import display_memory_config, get_memory_config

            memory_config = get_memory_config(env.get("NODE_OPTIONS"))
            if memory_config and "node_options" in memory_config:
                env["NODE_OPTIONS"] = memory_config["node_options"]
                # Display configuration on launch
                display_memory_config(memory_config)
            else:
                # Fallback to 32GB if detection fails
                # Intentional: High-RAM development systems should use generous heap
                # for large codebases (6000+ files). Matches smart memory system's
                # cap and ensures blarify indexing completes on typical dev machines.
                env["NODE_OPTIONS"] = "--max-old-space-size=32768"

            if self._target_directory:
                env.update(self.uvx_manager.get_environment_variables())
            # Pass through CLAUDE_PROJECT_DIR if set (for UVX temp environments)
            if "CLAUDE_PROJECT_DIR" in os.environ:
                env["CLAUDE_PROJECT_DIR"] = os.environ["CLAUDE_PROJECT_DIR"]

            # Export CLAUDE_PLUGIN_ROOT for plugin discoverability
            # Check if plugin was installed via Claude Code (AMPLIHACK_PLUGIN_INSTALLED set by cli.py)
            if os.environ.get("AMPLIHACK_PLUGIN_INSTALLED") == "true":
                # Plugin installed via Claude Code - use installed plugin path
                installed_plugin_path = (
                    Path.home()
                    / ".claude"
                    / "plugins"
                    / "cache"
                    / "amplihack"
                    / "amplihack"
                    / "0.9.0"
                )
                env["CLAUDE_PLUGIN_ROOT"] = str(installed_plugin_path)
            else:
                # Directory copy mode - use ~/.amplihack/.claude/
                plugin_root = Path.home() / ".amplihack" / ".claude"
                if plugin_root.exists():
                    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)

            # Ensure user-local npm bin is in PATH (for claude installed via npm)
            user_npm_bin = str(Path.home() / ".npm-global" / "bin")
            current_path = env.get("PATH", "")
            if user_npm_bin not in current_path:
                env["PATH"] = f"{user_npm_bin}:{current_path}"

            # Launch Claude
            self.claude_process = subprocess.Popen(cmd, env=env)

            # Wait for Claude to finish
            exit_code = self.claude_process.wait()

            return exit_code

        except Exception as e:
            print(f"Error launching Claude: {e}")
            return 1

    def launch_interactive(self) -> int:
        """Launch Claude in interactive mode with live output.

        Note: This method does NOT use SettingsManager because hooks added by
        ensure_settings_json() during prepare_launch() are PERMANENT changes.
        SettingsManager is designed for TEMPORARY changes that restore on exit.
        Using it here would incorrectly remove hooks when Claude exits.

        Returns:
            Exit code from Claude process.
        """
        # NOTE: We don't use SettingsManager here because amplihack launch makes
        # PERMANENT changes (adding hooks via ensure_settings_json()).
        # SettingsManager is designed for TEMPORARY changes that restore on exit.
        # Using it here would wipe hooks on exit, defeating the purpose of installation.

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
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)
            if sys.platform != "win32":
                signal.signal(signal.SIGTERM, signal_handler)

            # Set environment variables for UVX mode
            env = os.environ.copy()

            # Set agent identity and home directory for Rust CLI parity
            env["AMPLIHACK_AGENT_BINARY"] = "claude"
            env.setdefault("AMPLIHACK_HOME", os.path.expanduser("~/.amplihack"))

            # Smart memory configuration
            from .memory_config import display_memory_config, get_memory_config

            memory_config = get_memory_config(env.get("NODE_OPTIONS"))
            if memory_config and "node_options" in memory_config:
                env["NODE_OPTIONS"] = memory_config["node_options"]
                # Display configuration on launch
                display_memory_config(memory_config)
            else:
                # Fallback to 32GB if detection fails
                # Intentional: High-RAM development systems should use generous heap
                # for large codebases (6000+ files). Matches smart memory system's
                # cap and ensures blarify indexing completes on typical dev machines.
                env["NODE_OPTIONS"] = "--max-old-space-size=32768"

            if self._target_directory:
                env.update(self.uvx_manager.get_environment_variables())
            # Pass through CLAUDE_PROJECT_DIR if set (for UVX temp environments)
            if "CLAUDE_PROJECT_DIR" in os.environ:
                env["CLAUDE_PROJECT_DIR"] = os.environ["CLAUDE_PROJECT_DIR"]

            # Export CLAUDE_PLUGIN_ROOT for plugin discoverability
            # Check if plugin was installed via Claude Code (AMPLIHACK_PLUGIN_INSTALLED set by cli.py)
            if os.environ.get("AMPLIHACK_PLUGIN_INSTALLED") == "true":
                # Plugin installed via Claude Code - use installed plugin path
                installed_plugin_path = (
                    Path.home()
                    / ".claude"
                    / "plugins"
                    / "cache"
                    / "amplihack"
                    / "amplihack"
                    / "0.9.0"
                )
                env["CLAUDE_PLUGIN_ROOT"] = str(installed_plugin_path)
            else:
                # Directory copy mode - use ~/.amplihack/.claude/
                plugin_root = Path.home() / ".amplihack" / ".claude"
                if plugin_root.exists():
                    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)

            # Ensure user-local npm bin is in PATH (for claude installed via npm)
            user_npm_bin = str(Path.home() / ".npm-global" / "bin")
            current_path = env.get("PATH", "")
            if user_npm_bin not in current_path:
                env["PATH"] = f"{user_npm_bin}:{current_path}"

            # Launch Claude with direct I/O (interactive mode)
            print("Starting Claude...")
            exit_code = subprocess.call(cmd, env=env)

            return exit_code

        except Exception as e:
            print(f"Error launching Claude: {e}")
            return 1

    # Neo4j startup methods removed (Week 7 cleanup)

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

    # Neo4j credential check removed (Week 7 cleanup)

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown.

        Registers handlers for SIGINT (Ctrl-C) and SIGTERM that allow
        process to exit gracefully. Also registers atexit handler as fallback.
        """

        def signal_handler(signum: int, frame) -> None:
            """Handle shutdown signals."""
            signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
            logger.info(f"Received {signal_name}, initiating graceful shutdown...")

            # Trigger cleanup via stop hook
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

    def _get_project_consent_cache_path(self, project_path: Path) -> Path:
        """Get per-project consent cache path.

        Args:
            project_path: Project root directory

        Returns:
            Path to consent cache file
        """
        import hashlib

        # Hash project path to create unique identifier
        project_hash = hashlib.sha256(str(project_path.resolve()).encode()).hexdigest()[:16]

        # Store in ~/.amplihack/.blarify_consent_<hash>
        cache_dir = Path.home() / ".amplihack"
        cache_dir.mkdir(parents=True, exist_ok=True)

        return cache_dir / f".blarify_consent_{project_hash}"

    def _has_blarify_consent(self, project_path: Path) -> bool:
        """Check if user has already consented to blarify indexing for this project.

        Args:
            project_path: Project root directory

        Returns:
            True if consent already given, False otherwise
        """
        consent_cache = self._get_project_consent_cache_path(project_path)
        return consent_cache.exists()

    def _save_blarify_consent(self, project_path: Path) -> None:
        """Save blarify consent for this project.

        Args:
            project_path: Project root directory
        """
        consent_cache = self._get_project_consent_cache_path(project_path)
        try:
            consent_cache.touch()
            logger.debug("Saved blarify consent for %s", project_path)
        except Exception as e:
            logger.warning("Failed to save blarify consent: %s", e)

    def _prompt_blarify_indexing(self) -> bool:
        """Prompt user to run blarify code indexing with staleness detection.

        Features:
        - Staleness detection (only prompts if index missing or stale)
        - Time estimation with language breakdown
        - Background indexing option
        - Per-project "don't ask again" preference
        - Non-blocking (failure doesn't stop launch)

        Returns:
            True if indexing completed or skipped, False on error
        """
        # Blarify is disabled by default - only run if explicitly enabled
        if os.getenv("AMPLIHACK_ENABLE_BLARIFY") != "1":
            logger.debug(
                "Blarify indexing disabled by default (set AMPLIHACK_ENABLE_BLARIFY=1 to enable)"
            )
            return True

        # Get project directory (current working directory)
        project_path = Path.cwd()

        # Check if user has "don't ask again" preference for this project
        if self._has_blarify_consent(project_path):
            logger.debug("Blarify 'don't ask again' preference set for %s", project_path)
            return True

        try:
            # Check index status using staleness detector
            from ..memory.kuzu.indexing.staleness_detector import check_index_status
            from ..memory.kuzu.indexing.time_estimator import estimate_time

            status = check_index_status(project_path)

            # If index is up-to-date, skip prompting
            if not status.needs_indexing:
                logger.debug("Blarify index is up-to-date: %s", status.reason)
                return True

            # Index is needed - estimate time
            # TODO: Make language detection dynamic based on project files
            languages = ["python", "typescript", "javascript", "go", "rust", "csharp", "c", "cpp"]
            estimate = estimate_time(project_path, languages)

            # Format time estimate
            if estimate.total_seconds < 60:
                time_str = f"{estimate.total_seconds:.0f}s"
            else:
                minutes = int(estimate.total_seconds // 60)
                seconds = int(estimate.total_seconds % 60)
                time_str = f"{minutes}m {seconds}s"

            # Check if running in interactive terminal
            from .memory_config import is_interactive_terminal

            if not is_interactive_terminal():
                # Non-interactive mode - skip indexing
                logger.info("Non-interactive environment, skipping blarify prompt")
                return True

            # Interactive mode - prompt user
            print("\n" + "=" * 60)
            print("Code Indexing with Blarify")
            print("=" * 60)
            print(f"Status: {status.reason}")
            print(f"Files to index: {status.estimated_files}")
            print(f"Estimated time: {time_str}")
            print()
            print("Language breakdown:")
            for lang, seconds in sorted(estimate.by_language.items()):
                if estimate.file_counts[lang] > 0:
                    lang_time = (
                        f"{seconds:.0f}s"
                        if seconds < 60
                        else f"{int(seconds // 60)}m {int(seconds % 60)}s"
                    )
                    print(
                        f"  • {lang.capitalize()}: {estimate.file_counts[lang]} files ({lang_time})"
                    )
            print()
            print("Blarify enables code-aware features:")
            print("  • Code context in memory retrieval")
            print("  • Function and class awareness")
            print("  • Automatic code-memory linking")
            print("=" * 60)

            # Import timeout utilities from memory_config
            from .memory_config import get_user_input_with_timeout, parse_consent_response

            prompt_msg = "\nRun indexing? [y/N/b/n] (b=background, n=don't ask again): "
            response = get_user_input_with_timeout(prompt_msg, timeout_seconds=30, logger=logger)

            # Handle "don't ask again" option
            if response and response.lower().strip() in ["n", "never", "skip"]:
                print("\n⏭️  Indexing skipped (won't ask again for this project)")
                self._save_blarify_consent(project_path)
                return True

            # Check for background mode
            background_mode = False
            if response and response.lower().strip() in ["b", "background"]:
                background_mode = True
                user_consented = True
            else:
                # Parse response with default no (opt-in, not opt-out)
                user_consented = parse_consent_response(response, default=False)

            if user_consented:
                if background_mode:
                    print("\n📊 Starting blarify code indexing in background...")
                else:
                    print("\n📊 Starting blarify code indexing...")

                success = self._run_blarify_and_import(project_path, background=background_mode)

                if success:
                    if background_mode:
                        print("✅ Code indexing started in background\n")
                    else:
                        print("✅ Code indexing complete\n")
                    return True
                print("⚠️  Code indexing failed (non-critical, continuing...)\n")
                return True  # Return True - failure is non-blocking

            print("\n⏭️  Skipping code indexing (you can run it later with: amplihack index-code)\n")
            return True

        except KeyboardInterrupt:
            print("\n⏭️  Skipping code indexing (interrupted)\n")
            return True
        except Exception as e:
            logger.warning("Blarify prompt failed: %s", e)
            print(f"\n⚠️  Code indexing prompt failed: {e} (continuing...)\n")
            return True  # Non-blocking - always return True

    def _count_files_by_language(self, project_path: Path, languages: list[str]) -> dict[str, int]:
        """Count files for each language in the project.

        Args:
            project_path: Project root directory
            languages: List of languages to count

        Returns:
            Dict mapping language to file count
        """
        extensions_map = {
            "python": [".py"],
            "javascript": [".js", ".jsx"],
            "typescript": [".ts", ".tsx"],
            "csharp": [".cs"],
        }

        counts = {}
        for lang in languages:
            extensions = extensions_map.get(lang, [])
            count = 0
            for ext in extensions:
                count += len(list(project_path.rglob(f"*{ext}")))
            counts[lang] = count

        return counts

    def _run_blarify_and_import(self, project_path: Path, background: bool = False) -> bool:
        """Run blarify and import results to Kuzu.

        Args:
            project_path: Project root directory to index
            background: If True, run indexing in background

        Returns:
            True if successful, False otherwise
        """
        try:
            # Import prerequisite checker and orchestrator
            from ..memory.kuzu.connector import KuzuConnector
            from ..memory.kuzu.indexing.orchestrator import Orchestrator
            from ..memory.kuzu.indexing.prerequisite_checker import PrerequisiteChecker

            # Step 1: Check prerequisites
            print("\n🔍 Checking prerequisites...")
            checker = PrerequisiteChecker()
            result = checker.check_all(["python", "javascript", "typescript", "csharp"])

            if not result.can_proceed:
                print("❌ No indexing tools available. Install scip-python, node, or dotnet.")
                return False

            # Show what's available
            if result.available_languages:
                print(f"✓ Available languages: {', '.join(result.available_languages)}")
            if result.unavailable_languages:
                print(f"⚠️  Skipping languages: {', '.join(result.unavailable_languages)}")
                if result.language_statuses:
                    for lang in result.unavailable_languages:
                        status = result.language_statuses.get(lang)
                        if status and status.error_message:
                            print(f"   - {lang}: {status.error_message}")

            # Step 2: Estimate file count and time
            file_counts = self._count_files_by_language(project_path, result.available_languages)
            total_files = sum(file_counts.values())

            if total_files > 0:
                # Estimate time (average ~0.5 seconds per file)
                estimated_seconds = total_files * 0.5
                estimated_minutes = estimated_seconds / 60

                print("\n📊 Estimated workload:")
                for lang, count in file_counts.items():
                    print(f"   {lang}: {count} files")
                print(f"   Total: {total_files} files")

                if estimated_minutes < 1:
                    print(f"   Estimated time: ~{int(estimated_seconds)} seconds")
                else:
                    print(f"   Estimated time: ~{estimated_minutes:.1f} minutes")

            # Step 3: Get Kuzu connector
            kuzu_db_path = Path.home() / ".amplihack" / "memory_kuzu.db"
            connector = KuzuConnector(str(kuzu_db_path))
            connector.connect()

            # Step 4: Create orchestrator and run indexing
            orchestrator = Orchestrator(connector=connector)

            # Show progress for foreground indexing
            if not background and total_files > 0:
                print("\n🚀 Starting indexing...")
                import time

                start_time = time.time()

            indexing_result = orchestrator.run(
                codebase_path=project_path,
                languages=result.available_languages,
                background=background,
            )

            if indexing_result.success:
                if not background and total_files > 0:
                    elapsed = time.time() - start_time
                    print(
                        f"\n✅ Indexed {indexing_result.total_files} files in {elapsed:.1f} seconds"
                    )
                else:
                    print(f"\n✅ Indexed {indexing_result.total_files} files")
                logger.info("Blarify import complete: %s files", indexing_result.total_files)
                return True
            print("\n⚠️  Indexing completed with errors")
            if indexing_result.errors:
                for error in indexing_result.errors[:3]:  # Show first 3 errors
                    print(f"   - {error.language}: {error.message}")
            return False

        except Exception as e:
            logger.error("Blarify indexing failed: %s", e)
            print(f"\n❌ Indexing failed: {e}")
            return False


def launch_claude(
    *,
    enable_trace: bool = False,
    trace_file: str | None = None,
    args: list[str] | None = None,
) -> int:
    """Launch Claude through the lightweight compatibility facade expected by tests."""

    manager = ClaudeBinaryManager()
    binary = manager.detect_native_binary()
    trace_callback = None
    unregister = None

    if enable_trace:
        TraceLogger(enabled=True, log_file=Path(trace_file) if trace_file else None)
        from ..proxy.litellm_callbacks import register_trace_callbacks, unregister_trace_callbacks

        trace_callback = register_trace_callbacks(enabled=True, trace_file=trace_file)
        unregister = unregister_trace_callbacks

    if binary is not None:
        cmd = manager.build_command(binary, enable_trace=enable_trace, trace_file=trace_file)
    else:
        cmd = [get_claude_command()]

    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    finally:
        if unregister is not None and trace_callback is not None:
            unregister(trace_callback)
