"""Proxy lifecycle management."""

import atexit
import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import ProxyConfig
from .env import ProxyEnvironment


class ProxyManager:
    """Manages claude-code-proxy lifecycle."""

    def __init__(self, proxy_config: Optional[ProxyConfig] = None):
        """Initialize proxy manager.

        Args:
            proxy_config: Proxy configuration object.
        """
        self.proxy_config = proxy_config
        self.proxy_process: Optional[subprocess.Popen] = None
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

    def ensure_proxy_installed(self) -> bool:
        """Ensure claude-code-proxy is available via uvx.

        For UVX environments, we use the PyPI package directly instead of
        cloning and manually installing dependencies.

        Returns:
            True if proxy is ready to use, False otherwise.
        """
        # Check if uvx is available
        try:
            result = subprocess.run(
                ["uvx", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                print("Using claude-code-proxy via uvx (PyPI package)")
                return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Fallback: check if uv is available for direct package management
        try:
            result = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("UV available for claude-code-proxy management")
                return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass

        print("Neither uvx nor uv available - cannot run claude-code-proxy in this environment")
        return False

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
            # Start the proxy process using uvx (UVX-compatible approach)
            print(f"Starting claude-code-proxy on port {self.proxy_port} via uvx...")

            # Create environment for the proxy process
            proxy_env = os.environ.copy()
            if self.proxy_config:
                proxy_env.update(self.proxy_config.to_env_dict())
            # Ensure PORT is set for the proxy process
            proxy_env["PORT"] = str(self.proxy_port)

            # Use uvx to run claude-code-proxy directly from PyPI
            start_command = ["uvx", "claude-code-proxy"]

            self.proxy_process = subprocess.Popen(
                start_command,
                env=proxy_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid if os.name != "nt" else None,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )

            # Register cleanup on exit
            atexit.register(self.stop_proxy)

            # Wait a moment for the proxy to start
            time.sleep(3)

            # Check if proxy is still running
            if self.proxy_process.poll() is not None:
                stdout, stderr = self.proxy_process.communicate(timeout=1)
                print(f"Proxy failed to start. Exit code: {self.proxy_process.returncode}")
                if stderr:
                    print(f"Error output: {stderr}")
                if stdout:
                    print(f"Output: {stdout}")
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
            self._display_log_locations()
            return True

        except Exception as e:
            print(f"Failed to start proxy: {e}")
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

    def __enter__(self):
        """Context manager entry - starts proxy.

        Returns:
            Self for context manager use.
        """
        self.start_proxy()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stops proxy.

        Args:
            exc_type: Exception type if any.
            exc_val: Exception value if any.
            exc_tb: Exception traceback if any.
        """
        self.stop_proxy()

    def get_azure_deployment(self, model_name: str) -> Optional[str]:
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

    def get_azure_deployments(self) -> Dict[str, str]:
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

    def transform_request_for_azure(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
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

    def construct_azure_url(self, model: str) -> Optional[str]:
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
        self, response: Dict[str, Any], original_model: str
    ) -> Dict[str, Any]:
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

    def _create_secure_env(self) -> Dict[str, str]:
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

    def _get_secure_start_command(self, proxy_repo: Path) -> Optional[List[str]]:
        """Get a secure start command for the proxy.

        Args:
            proxy_repo: Path to proxy repository

        Returns:
            Secure start command list or None if no valid command found.
        """
        # Check for valid start methods in priority order
        if (proxy_repo / "start_proxy.py").exists():
            return ["python", "start_proxy.py"]
        elif (proxy_repo / "src" / "proxy.py").exists():
            return ["python", "-m", "src.proxy"]
        elif (proxy_repo / "package.json").exists():
            return ["npm", "start"]
        else:
            return None

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
