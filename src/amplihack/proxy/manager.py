"""Proxy lifecycle management."""

import atexit
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .config import ProxyConfig
from .env import ProxyEnvironment
from .sanitizing_logger import get_sanitizing_logger

# Use sanitizing logger to prevent credential exposure (Issue #1997)
logger = get_sanitizing_logger(__name__)


class ProxyManager:
    """Manages claude-code-proxy lifecycle."""

    def __init__(self, proxy_config: ProxyConfig | None = None):
        """Initialize proxy manager.

        Args:
            proxy_config: Proxy configuration object.
        """
        self.proxy_config = proxy_config
        self.proxy_process: subprocess.Popen | None = None
        self.proxy_dir = Path.home() / ".amplihack" / "proxy"
        self.env_manager = ProxyEnvironment()
        # Read PORT from proxy_config if available, otherwise use default
        if proxy_config and proxy_config.get("PORT"):
            self.proxy_port = int(proxy_config.get("PORT"))
            print(f"Using proxy port from config: {self.proxy_port}")
        else:
            self.proxy_port = 8080  # Default port
            print(f"Using default proxy port: {self.proxy_port}")

        # Performance optimizations - cache URL templates and common operations
        self._url_template_cache = {}
        self._endpoint_cache = {}
        self._api_version_cache = {}

        # Log file handles for proxy output
        self._stdout_log_file = None
        self._stderr_log_file = None

    def ensure_proxy_installed(self) -> bool:
        """Ensure the proxy server can be run.

        Returns:
            True if proxy is ready to use, False otherwise.
        """
        # We're using the built-in proxy server from src/amplihack/proxy/server.py
        # Just check that Python is available (which it must be since we're running)
        print("Using built-in proxy server from src/amplihack/proxy/server.py")
        return True

    def setup_proxy_config(self) -> bool:
        """Set up proxy configuration.

        Returns:
            True if configuration is set up successfully, False otherwise.
        """
        if not self.proxy_config or not self.proxy_config.config_path:
            return True  # No config to set up

        proxy_repo = self.proxy_dir / "claude-code-proxy"
        target_env = proxy_repo / ".env"

        # Copy .env file to proxy directory
        try:
            self.proxy_config.save_to(target_env)
            print(f"Copied proxy configuration to {target_env}")
            return True
        except Exception as e:
            print(f"Failed to copy proxy configuration: {e}")
            return False

    def start_proxy(self) -> bool:
        """Start the claude-code-proxy server.

        Returns:
            True if proxy started successfully, False otherwise.
        """
        if self.proxy_process and self.proxy_process.poll() is None:
            print("Proxy is already running")
            return True

        # Validate configuration before starting
        if self.proxy_config and not self.proxy_config.validate():
            print("Invalid proxy configuration")
            return False

        if not self.ensure_proxy_installed():
            return False

        try:
            # Start the proxy process using the built-in server
            print(f"Starting built-in proxy server on port {self.proxy_port}...")

            # Create log directory and files
            from datetime import datetime

            log_dir = Path("/tmp/amplihack_logs")
            log_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            stdout_log_path = log_dir / f"proxy-stdout-{timestamp}.log"
            stderr_log_path = log_dir / f"proxy-stderr-{timestamp}.log"

            # Open log files for writing
            # Note: Cannot use context manager as files must stay open for subprocess lifetime
            self._stdout_log_file = open(stdout_log_path, "w")  # noqa: SIM115
            self._stderr_log_file = open(stderr_log_path, "w")  # noqa: SIM115

            # Create environment for the proxy process
            proxy_env = os.environ.copy()
            if self.proxy_config:
                proxy_env.update(self.proxy_config.to_env_dict())
            # Ensure PORT is set for the proxy process
            proxy_env["PORT"] = str(self.proxy_port)

            # Determine the correct way to start the proxy server
            start_command = self._get_proxy_start_command()

            if not start_command:
                print("Failed to determine proxy start command")
                self._close_log_files()
                return False

            self.proxy_process = subprocess.Popen(
                start_command,
                env=proxy_env,
                stdout=self._stdout_log_file,  # Redirect to log file
                stderr=self._stderr_log_file,  # Redirect to log file
                preexec_fn=os.setsid if os.name != "nt" else None,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )

            # Register cleanup on exit
            atexit.register(self.stop_proxy)

            # Wait a moment for the proxy to start
            time.sleep(3)

            # Check if proxy is still running
            if self.proxy_process.poll() is not None:
                print(f"Proxy failed to start. Exit code: {self.proxy_process.returncode}")
                print("Check logs for details:")
                print(f"  stdout: {stdout_log_path}")
                print(f"  stderr: {stderr_log_path}")
                self._close_log_files()
                return False

            # Set up environment variables - handle both OpenAI and Azure configs
            api_key = self.proxy_config.get("ANTHROPIC_API_KEY") if self.proxy_config else None
            azure_config = (
                self.proxy_config.to_env_dict()
                if self.proxy_config and self.is_azure_mode()
                else None
            )
            self.env_manager.setup(self.proxy_port, api_key, azure_config)

            print(f"Proxy started successfully on port {self.proxy_port}")
            print("Proxy logs:")
            print(f"  stdout: {stdout_log_path}")
            print(f"  stderr: {stderr_log_path}")
            return True

        except Exception as e:
            print(f"Failed to start proxy: {e}")
            self._close_log_files()
            return False

    def stop_proxy(self) -> None:
        """Stop the claude-code-proxy server."""
        if not self.proxy_process:
            return

        if self.proxy_process.poll() is None:
            print("Stopping claude-code-proxy...")
            try:
                if os.name == "nt":
                    # Windows
                    self.proxy_process.terminate()
                else:
                    # Unix-like
                    os.killpg(os.getpgid(self.proxy_process.pid), signal.SIGTERM)

                # Wait for graceful shutdown
                try:
                    self.proxy_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if not responding
                    if os.name == "nt":
                        self.proxy_process.kill()
                    else:
                        os.killpg(os.getpgid(self.proxy_process.pid), signal.SIGKILL)
                    self.proxy_process.wait()

                print("Proxy stopped successfully")
            except Exception as e:
                sanitized_error = self._sanitize_subprocess_error(str(e))
                print(f"Error stopping proxy: {sanitized_error}")

        # Close log files
        self._close_log_files()

        # Restore environment variables
        self.env_manager.restore()

        # Clear sensitive process information
        self.proxy_process = None

        # Force garbage collection of any cached sensitive data
        self._url_template_cache.clear()
        self._endpoint_cache.clear()
        self._api_version_cache.clear()

    def is_running(self) -> bool:
        """Check if proxy is running.

        Returns:
            True if proxy is running, False otherwise.
        """
        return self.proxy_process is not None and self.proxy_process.poll() is None

    def get_proxy_url(self) -> str:
        """Get the proxy URL.

        Returns:
            URL of the running proxy.
        """
        return f"http://localhost:{self.proxy_port}"

    def __enter__(self) -> "ProxyManager":
        """Context manager entry - starts proxy.

        Returns:
            Self for context manager use.
        """
        self.start_proxy()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit - stops proxy.

        Args:
            exc_type: Exception type if any.
            exc_val: Exception value if any.
            exc_tb: Exception traceback if any.
        """
        self.stop_proxy()

    def get_azure_deployment(self, model_name: str) -> str | None:
        """Get Azure deployment name for OpenAI model.

        Args:
            model_name: OpenAI model name

        Returns:
            Azure deployment name if mapping exists, None otherwise.
        """
        if not self.proxy_config:
            return None
        return self.proxy_config.get_azure_deployment(model_name)

    def is_azure_mode(self) -> bool:
        """Check if proxy is configured for Azure mode.

        Returns:
            True if Azure mode is enabled, False otherwise.
        """
        if not self.proxy_config:
            return False
        return self.proxy_config.is_azure_endpoint()

    def get_active_config_type(self) -> str:
        """Get the active configuration type.

        Returns:
            "azure" or "openai" depending on configuration.
        """
        if not self.proxy_config:
            return "openai"

        # Check for explicit proxy mode/type setting
        explicit_mode = self.proxy_config.get("PROXY_MODE") or self.proxy_config.get("PROXY_TYPE")
        if explicit_mode:
            return explicit_mode.lower()

        return self.proxy_config.get_endpoint_type()

    def get_azure_deployments(self) -> dict[str, str]:
        """Get Azure deployment mappings.

        Returns:
            Dictionary mapping OpenAI model names to Azure deployment names.
        """
        if not self.proxy_config or not self.is_azure_mode():
            return {}

        deployments = {}
        model_mappings = {
            "gpt-4": "AZURE_GPT4_DEPLOYMENT",
            "gpt-4o-mini": "AZURE_GPT4_MINI_DEPLOYMENT",
            "gpt-3.5-turbo": "AZURE_GPT35_DEPLOYMENT",
        }

        for model, env_var in model_mappings.items():
            deployment = self.proxy_config.get(env_var)
            if deployment:
                deployments[model] = deployment

        return deployments

    def transform_request_for_azure(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Transform OpenAI request format to Azure format.

        Args:
            request_data: OpenAI-format request data

        Returns:
            Azure-format request data
        """
        azure_request = request_data.copy()

        # Remove model from request body (Azure uses it in URL path)
        azure_request.pop("model", None)

        return azure_request

    def construct_azure_url(self, model: str) -> str | None:
        """Construct Azure OpenAI API URL for a specific model.

        Args:
            model: OpenAI model name

        Returns:
            Constructed Azure URL or None if not configured.
        """
        if not self.proxy_config or not self.is_azure_mode():
            return None

        # Check cache first for common model/endpoint combinations
        cache_key = f"{model}:{id(self.proxy_config)}"
        if cache_key in self._url_template_cache:
            return self._url_template_cache[cache_key]

        # Get components (these may also be cached)
        endpoint_cache_key = id(self.proxy_config)
        if endpoint_cache_key not in self._endpoint_cache:
            endpoint = self.proxy_config.get_azure_endpoint()
            if endpoint:
                self._endpoint_cache[endpoint_cache_key] = endpoint.rstrip("/")
            else:
                return None
        else:
            endpoint = self._endpoint_cache[endpoint_cache_key]

        deployment = self.proxy_config.get_azure_deployment(model)
        if not deployment:
            return None

        # Cache API version
        api_version_key = id(self.proxy_config)
        if api_version_key not in self._api_version_cache:
            self._api_version_cache[api_version_key] = (
                self.proxy_config.get_azure_api_version() or "2024-02-01"
            )
        api_version = self._api_version_cache[api_version_key]

        # Construct URL using format for better performance
        url = (
            f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        )

        # Cache the result
        self._url_template_cache[cache_key] = url
        return url

    def normalize_azure_response(
        self, response: dict[str, Any], original_model: str
    ) -> dict[str, Any]:
        """Normalize Azure response to OpenAI format.

        Args:
            response: Azure response data
            original_model: Original OpenAI model name requested

        Returns:
            Normalized response in OpenAI format
        """
        normalized = response.copy()

        # Replace Azure deployment name with original model name
        if "model" in normalized:
            normalized["model"] = original_model

        return normalized

    def _validate_git_url(self, url: str) -> bool:
        """Validate git repository URL for security.

        Args:
            url: Git repository URL

        Returns:
            True if URL is safe, False otherwise.
        """
        # Only allow HTTPS GitHub URLs for security
        allowed_patterns = [r"https://github\.com/[a-zA-Z0-9\-_.]+/[a-zA-Z0-9\-_.]+\.git$"]
        return any(re.match(pattern, url) for pattern in allowed_patterns)

    def _sanitize_subprocess_error(self, error_msg: str) -> str:
        """Sanitize subprocess error messages to prevent credential leakage.

        Args:
            error_msg: Error message from subprocess

        Returns:
            Sanitized error message.
        """
        if not error_msg:
            return "<no error message>"

        # Remove potential API keys, passwords, and other sensitive data
        sensitive_patterns = [
            r"[a-zA-Z0-9\-_]{20,}",  # Potential API keys
            r"password[=:]\s*\S+",  # Passwords
            r"key[=:]\s*\S+",  # Keys
            r"token[=:]\s*\S+",  # Tokens
        ]

        sanitized = error_msg
        for pattern in sensitive_patterns:
            sanitized = re.sub(pattern, "<redacted>", sanitized, flags=re.IGNORECASE)

        return sanitized

    def _is_safe_module_path(self, module_path: str) -> bool:
        """Validate that a module path is safe for execution.

        Args:
            module_path: Module path to validate

        Returns:
            True if the module path is safe, False otherwise.
        """
        if not module_path or not isinstance(module_path, str):
            return False

        # Only allow alphanumeric characters, dots, and underscores
        # This prevents injection attacks through module names
        allowed_pattern = re.compile(r"^[a-zA-Z0-9_.]+$")
        if not allowed_pattern.match(module_path):
            return False

        # Only allow known safe module prefixes
        safe_prefixes = [
            "amplihack.",
            "src.amplihack.",
            "amplihack.proxy.server",
            "src.amplihack.proxy.server",
        ]

        return any(
            module_path.startswith(prefix) or module_path == prefix.rstrip(".")
            for prefix in safe_prefixes
        )

    def _is_safe_file_path(self, file_path: Path) -> bool:
        """Validate that a file path is safe and within expected directories.

        Args:
            file_path: File path to validate

        Returns:
            True if the file path is safe, False otherwise.
        """
        try:
            # Resolve the path to handle any relative components or symlinks
            resolved_path = file_path.resolve()

            # Define safe base directories
            safe_bases = [
                Path(sys.prefix).resolve(),  # Python installation
                Path(sys.executable).parent.parent.resolve(),  # Virtual environment
                Path(__file__).parent.parent.parent.resolve(),  # Source directory
            ]

            # Check if the resolved path is within any safe base directory
            for safe_base in safe_bases:
                try:
                    resolved_path.relative_to(safe_base)
                    # If we get here, the path is within the safe base
                    return True
                except ValueError:
                    continue

            return False

        except (OSError, ValueError):
            # If path resolution fails, consider it unsafe
            return False

    def _sanitize_path_for_display(self, file_path: Path) -> str:
        """Sanitize file path for safe display in logs.

        Args:
            file_path: File path to sanitize

        Returns:
            Sanitized path string safe for display.
        """
        try:
            # Only show the last few components of the path to avoid leaking
            # sensitive directory structure information
            parts = file_path.parts
            if len(parts) > 3:
                return ".../" + "/".join(parts[-3:])
            return str(file_path)
        except Exception:
            return "<path unavailable>"

    def _build_safe_subprocess_command(self, command: list[str]) -> list[str] | None:
        """Build a safe subprocess command with validation.

        Args:
            command: Command list to validate and secure

        Returns:
            Safe command list or None if command is unsafe.
        """
        if not command or not isinstance(command, list):
            return None

        # Validate the Python executable path
        if not command[0] or command[0] != sys.executable:
            return None

        # Validate command structure and arguments
        safe_command = []
        for i, arg in enumerate(command):
            if not isinstance(arg, str):
                return None

            # Reject -c flag (inline code execution) for security
            if arg == "-c":
                logger.error("Inline code execution (-c) not allowed for security")
                return None

            # Validate module names for -m flag
            if arg == "-m" and i + 1 < len(command):
                next_arg = command[i + 1]
                if not self._is_safe_module_path(next_arg):
                    return None

            safe_command.append(arg)

        return safe_command

    def _is_safe_inline_code(self, code: str) -> bool:
        """Validate that inline code is safe for execution.

        Args:
            code: Python code string to validate

        Returns:
            True if code is safe, False otherwise.
        """
        if not code or not isinstance(code, str):
            return False

        # Only allow very specific safe patterns
        safe_patterns = [
            r'^import [a-zA-Z0-9_.]+; print\([\'"]OK[\'"]\)$',
            r"^import [a-zA-Z0-9_.]+$",
        ]

        return any(re.match(pattern, code.strip()) for pattern in safe_patterns)

    def _create_secure_env(self) -> dict[str, str]:
        """Create a secure environment dictionary.

        Returns:
            Sanitized environment dictionary.
        """
        env = {}

        # Only include necessary environment variables
        safe_vars = {
            "PATH",
            "HOME",
            "USER",
            "SHELL",
            "TERM",
            "LANG",
            "LC_ALL",
            "NODE_ENV",
            "NPM_CONFIG_PREFIX",
            "PYTHONPATH",
            "PORT",
        }

        for key in safe_vars:
            if key in os.environ:
                env[key] = os.environ[key]

        return env

    def _get_secure_start_command(self, proxy_repo: Path) -> list[str] | None:
        """Get a secure start command for the proxy.

        Args:
            proxy_repo: Path to proxy repository

        Returns:
            Secure start command list or None if no valid command found.
        """
        # Check for valid start methods in priority order
        if (proxy_repo / "start_proxy.py").exists():
            return ["python", "start_proxy.py"]
        if (proxy_repo / "src" / "proxy.py").exists():
            return ["python", "-m", "src.proxy"]
        if (proxy_repo / "package.json").exists():
            return ["npm", "start"]
        return None

    def _get_proxy_start_command(self) -> list[str] | None:
        """Determine the correct command to start the proxy server.

        This method handles both development (running from source) and
        installed (pip/uvx) scenarios robustly.

        Returns:
            List of command arguments, or None if unable to determine.
        """
        # Method 1: Try import-based detection (fastest and most reliable)
        import importlib.util

        # Try to find installed package first (pip/uvx scenario)
        if importlib.util.find_spec("amplihack.proxy.server"):
            module_path = "amplihack.proxy.server"
            print(f"Detected installed package, using module: {module_path}")
            return [sys.executable, "-m", module_path]

        # Try to find source directory (development scenario)
        if importlib.util.find_spec("src.amplihack.proxy.server"):
            module_path = "src.amplihack.proxy.server"
            print(f"Detected source directory, using module: {module_path}")
            return [sys.executable, "-m", module_path]

        # Method 2: File-based execution as fallback
        # This works universally but requires locating the actual file
        # This is especially important when imports fail due to syntax errors

        # First, try to find server.py relative to this file
        current_file = Path(__file__).resolve()
        server_candidates = [
            # In same directory structure
            current_file.parent / "server.py",
            # One level up in src structure
            current_file.parent.parent / "proxy" / "server.py",
            # Check common installation locations
            Path(sys.prefix)
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
            / "amplihack"
            / "proxy"
            / "server.py",
            # Also check site-packages directly in case of virtual environment
            Path(sys.executable).parent.parent
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
            / "amplihack"
            / "proxy"
            / "server.py",
        ]

        for server_path in server_candidates:
            if self._is_safe_file_path(server_path) and server_path.exists():
                print(f"Found proxy server file at: {self._sanitize_path_for_display(server_path)}")
                return [sys.executable, str(server_path)]

        # Method 3: Try both module paths with subprocess (last resort)
        # This catches edge cases where imports fail but modules work
        # Enhanced to handle uvx scenarios better
        module_paths = [
            "amplihack.proxy.server",  # Standard installed package
            "src.amplihack.proxy.server",  # Development structure
        ]

        # Also try without the src prefix in case we're in a different context
        # This helps with uvx where the package might be installed differently
        for module_path in module_paths:
            if self._is_safe_module_path(module_path):
                try:
                    # Test if the module can be executed safely
                    # Use secure module validation without dynamic code execution
                    safe_command = self._build_safe_subprocess_command(
                        [sys.executable, "-c", "import " + module_path + "; print('OK')"]
                    )
                    if not safe_command:
                        continue

                    test_result = subprocess.run(
                        safe_command,
                        capture_output=True,
                        text=True,
                        timeout=5,
                        env=self._create_secure_env(),
                    )
                    if test_result.returncode == 0 and "OK" in test_result.stdout:
                        print(f"Module {module_path} is executable via subprocess")
                        return [sys.executable, "-m", module_path]
                except (subprocess.TimeoutExpired, Exception):
                    continue

        # Method 4: Try to determine if we're in a uvx environment and adjust accordingly
        # Check if we're running from a uvx cache directory
        exe_path = Path(sys.executable).resolve()
        if "uvx" in str(exe_path) or ".local/bin" in str(exe_path):
            # We're likely in a uvx environment
            print("Detected uvx environment, trying amplihack.proxy.server directly")
            # In uvx, the package should be available as amplihack
            return [sys.executable, "-m", "amplihack.proxy.server"]

        # If all methods fail, provide helpful error message (sanitized)
        print("ERROR: Unable to locate proxy server module.")
        print("Attempted methods:")
        print("  1. Import 'amplihack.proxy.server' (installed package)")
        print("  2. Import 'src.amplihack.proxy.server' (development)")
        print("  3. File-based execution from package directory")
        print("  4. Subprocess module execution test")
        print("  5. uvx environment detection")
        print("\nPlease ensure the proxy server module is properly installed or available.")

        return None

    def _close_log_files(self) -> None:
        """Close proxy log files safely."""
        if self._stdout_log_file:
            try:
                self._stdout_log_file.close()
            except Exception as e:
                logger.debug(f"Error closing stdout log file: {e}")
            self._stdout_log_file = None

        if self._stderr_log_file:
            try:
                self._stderr_log_file.close()
            except Exception as e:
                logger.debug(f"Error closing stderr log file: {e}")
            self._stderr_log_file = None

    def _display_log_locations(self) -> None:
        """Display proxy log file locations."""
        try:
            from datetime import datetime

            # Create log directory path following amplihack pattern
            log_dir = Path("/tmp/amplihack_logs")

            # Generate timestamp for log file names
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

            # Define log file paths (following the pattern from Azure docs)
            jsonl_log = log_dir / f"proxy-log-{timestamp}.jsonl"
            html_log = log_dir / f"proxy-log-{timestamp}.html"

            # Display log locations
            print("Logs will be written to:")
            print(f"  JSONL: {jsonl_log}")
            print(f"  HTML:  {html_log}")

        except Exception as e:
            # Don't fail proxy startup if logging display fails
            print(f"Note: Unable to display log locations: {e}")
