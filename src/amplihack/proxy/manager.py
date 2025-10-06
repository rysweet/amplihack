"""Proxy lifecycle management."""

import atexit
import os
import re
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import ProxyConfig
from .env import ProxyEnvironment
from .responses_api_proxy import ResponsesAPIProxy, create_responses_api_proxy


class ProxyManager:
    """Manages claude-code-proxy lifecycle."""

    def __init__(self, proxy_config: Optional[ProxyConfig] = None):
        """Initialize proxy manager.

        Args:
            proxy_config: Proxy configuration object.
        """
        self.proxy_config = proxy_config
        self.proxy_process: Optional[subprocess.Popen] = None
        self.responses_api_proxy: Optional[ResponsesAPIProxy] = None
        self.proxy_dir = Path.home() / ".amplihack" / "proxy"
        self.env_manager = ProxyEnvironment()
        # Get port from configuration, default to 8082 if not specified
        self.proxy_port = self.get_configured_port()
        print(f"Using proxy port from config: {self.proxy_port}")

        # Performance optimizations - cache URL templates and common operations
        self._url_template_cache = {}
        self._endpoint_cache = {}
        self._api_version_cache = {}

    def get_configured_port(self) -> int:
        """Get the configured port from proxy config, with fallback to default.

        Returns:
            Port number to use for the proxy.
        """
        if self.proxy_config:
            port_str = self.proxy_config.get("PORT")
            if port_str:
                try:
                    return int(port_str)
                except (ValueError, TypeError):
                    print(f"Invalid PORT value '{port_str}', using default 8082")

        # Default port if not configured or invalid
        return 8082

    def is_responses_api(self) -> bool:
        """Check if the configured endpoint uses Azure Responses API.

        Returns:
            True if the endpoint appears to be using Azure Responses API.
        """
        if not self.proxy_config:
            return False

        base_url = self.proxy_config.get("OPENAI_BASE_URL", "")
        return "/openai/responses" in base_url

    def _start_responses_api_proxy(self) -> bool:
        """Start the custom Responses API proxy.

        Returns:
            True if proxy started successfully, False otherwise.
        """
        try:
            # Create the responses API proxy
            if not self.proxy_config:
                print("No proxy configuration available for Responses API")
                return False

            self.responses_api_proxy = create_responses_api_proxy(
                self.proxy_config.to_env_dict(), self.proxy_port
            )

            # Start the proxy
            if not self.responses_api_proxy.start():
                print("Failed to start Responses API proxy")
                return False

            print(f"Responses API proxy started successfully on port {self.proxy_port}")

            # Set up environment variables for Claude to use our proxy
            api_key = self.proxy_config.get("ANTHROPIC_API_KEY") if self.proxy_config else None
            azure_config = (
                self.proxy_config.to_env_dict()
                if self.proxy_config and self.is_azure_mode()
                else None
            )
            self.env_manager.setup(self.proxy_port, api_key, azure_config)

            self._display_log_locations()
            return True

        except Exception as e:
            print(f"Failed to start Responses API proxy: {e}")
            return False

    def _start_integrated_proxy(self) -> bool:
        """Start our integrated proxy server.

        Returns:
            True if proxy started successfully, False otherwise.
        """
        try:
            # Import the integrated proxy (run_server function)
            import threading
            import time

            from . import integrated_proxy

            if not self.proxy_config:
                print("No proxy configuration available for integrated proxy")
                return False

            # Create environment dict from proxy config
            proxy_env = self.proxy_config.to_env_dict()

            # Start the integrated proxy server in a background thread
            def run_integrated_server():
                try:
                    # Get host and port from config
                    host = proxy_env.get("HOST", "127.0.0.1")

                    print(f"Starting integrated proxy server on {host}:{self.proxy_port}")
                    print(f"Configuration: {len(proxy_env)} environment variables loaded")

                    # Create the FastAPI app and run it
                    app = integrated_proxy.create_app(proxy_env)

                    import uvicorn

                    uvicorn.run(app, host=host, port=self.proxy_port, log_level="error")
                except Exception as e:
                    print(f"Error in integrated proxy server: {e}")

            # Start the server thread
            server_thread = threading.Thread(target=run_integrated_server, daemon=True)
            server_thread.start()

            # Store thread reference for is_running() check
            self.server_thread = server_thread

            # Wait for server to start up
            time.sleep(3)

            # Check if thread is still alive
            if not server_thread.is_alive():
                print("Server thread died immediately after startup")
                return False

            # Test if the server is responding
            try:
                import requests

                response = requests.get(f"http://127.0.0.1:{self.proxy_port}/health", timeout=10)
                if response.status_code == 200:
                    print(f"Integrated proxy started successfully on port {self.proxy_port}")

                    # Set up environment variables for Claude
                    api_key = (
                        self.proxy_config.get("ANTHROPIC_API_KEY") if self.proxy_config else None
                    )
                    azure_config = (
                        self.proxy_config.to_env_dict()
                        if self.proxy_config and self.is_azure_mode()
                        else None
                    )
                    self.env_manager.setup(self.proxy_port, api_key, azure_config)

                    self._display_log_locations()
                    return True
                else:
                    print(f"Integrated proxy health check failed: {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                print(f"Failed to connect to integrated proxy: {e}")
                return False

        except Exception as e:
            print(f"Failed to start integrated proxy: {e}")
            return False

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

            # Validate passthrough configuration if enabled
            if self.proxy_config.is_passthrough_mode_enabled():
                if not self.proxy_config.validate_passthrough_config():
                    print("Passthrough mode configuration validation failed")
                    return False
                print("Passthrough mode enabled and validated")

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

        # Try integrated proxy first (if dependencies are available)
        try:
            print("Starting integrated proxy with Azure Responses API support")
            return self._start_integrated_proxy()
        except ImportError as e:
            print(f"Integrated proxy dependencies not available: {e}")
            print("Falling back to external claude-code-proxy")
            # Continue to original external proxy logic below
        except Exception as e:
            print(f"Integrated proxy failed to start: {e}")
            print("Falling back to external claude-code-proxy")
            # Continue to original external proxy logic below

        # Fallback to original external proxy logic
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
            print(f"Executing command: {' '.join(start_command)}")

            self.proxy_process = subprocess.Popen(
                start_command,
                env=proxy_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid if os.name != "nt" else None,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )

            print(f"Proxy process started with PID: {self.proxy_process.pid}")

            # Register cleanup on exit
            atexit.register(self.stop_proxy)

            # Wait for proxy to be ready (with health check)
            # Use a more generous timeout for initial startup
            if not self.wait_for_proxy_ready(timeout=45):
                print("Proxy startup failed or timed out")
                self.stop_proxy()
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
        """Stop the proxy server."""
        # Stop responses API proxy if running
        if self.responses_api_proxy:
            print("Stopping Responses API proxy...")
            self.responses_api_proxy.stop()
            self.responses_api_proxy = None

        # Stop claude-code-proxy if running
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

    def wait_for_proxy_ready(self, timeout: int = 30) -> bool:
        """Wait for proxy to be ready to accept connections.

        Args:
            timeout: Maximum time to wait in seconds.

        Returns:
            True if proxy is ready, False if timeout or proxy failed.
        """
        start_time = time.time()
        check_interval = 0.5  # Check every 500ms
        last_check_time = start_time

        print(f"Waiting for proxy to be ready on port {self.proxy_port}...")

        while time.time() - start_time < timeout:
            elapsed = time.time() - start_time

            # First check if process is still running
            if self.proxy_process and self.proxy_process.poll() is not None:
                # Process has exited, get error details
                try:
                    stdout, stderr = self.proxy_process.communicate(timeout=2)
                    print(f"Proxy process exited with code: {self.proxy_process.returncode}")
                    if stderr:
                        print(f"Error output: {stderr}")
                    if stdout:
                        print(f"Output: {stdout}")
                except subprocess.TimeoutExpired:
                    print("Proxy process exited but couldn't get output")
                return False

            # Check if port is accepting connections
            if self._check_port_ready(self.proxy_port):
                print(f"Proxy ready after {elapsed:.1f} seconds")
                return True

            # Print progress every 5 seconds
            if elapsed - (last_check_time - start_time) >= 5:
                print(f"Still waiting for proxy... ({elapsed:.1f}s elapsed)")
                last_check_time = time.time()

            time.sleep(check_interval)

        print(f"Timeout waiting for proxy to be ready after {timeout} seconds")

        # Try to get final process status for debugging
        if self.proxy_process:
            if self.proxy_process.poll() is None:
                print("Proxy process is still running but not accepting connections")
            else:
                print(f"Proxy process has exited with code: {self.proxy_process.returncode}")

        return False

    def _check_port_ready(self, port: int) -> bool:
        """Check if a port is ready to accept connections.

        Args:
            port: Port number to check.

        Returns:
            True if port is accepting connections, False otherwise.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1.0)  # 1 second timeout for connection attempt
                result = sock.connect_ex(("localhost", port))
                return result == 0
        except Exception:
            return False

    def is_running(self) -> bool:
        """Check if proxy is running.

        Returns:
            True if proxy is running, False otherwise.
        """
        # Check if integrated proxy (thread-based) is running
        if hasattr(self, 'server_thread') and self.server_thread is not None:
            if self.server_thread.is_alive():
                # Double-check with health check
                try:
                    import requests
                    response = requests.get(f"http://127.0.0.1:{self.proxy_port}/health", timeout=2)
                    return response.status_code == 200
                except Exception:
                    return False
            return False

        # Check if external proxy (subprocess-based) is running
        if self.proxy_process is not None:
            return self.proxy_process.poll() is None

        return False

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
            if self.proxy_process:
                print("\n📊 Proxy Logs:")
                print(f"  • Process PID: {self.proxy_process.pid}")
                print(f"  • Proxy URL: http://localhost:{self.proxy_port}")
                print("  • Real-time logs: Captured in subprocess pipes")
                print("    - stdout: Available via proxy_process.stdout")
                print("    - stderr: Available via proxy_process.stderr")
                print(f"  • To monitor process: ps {self.proxy_process.pid}")
                print("  • To view live logs: Use proxy_process.stdout.read() or .stderr.read()")
                print("  • Log level can be set via LOG_LEVEL env var")
                print(f"  • Working directory: {os.getcwd()}")

                # Show recent stdout if available
                if self.proxy_process.stdout:
                    try:
                        # Try to read any immediately available output (non-blocking)
                        import select
                        import sys

                        if hasattr(select, "select") and sys.platform != "win32":
                            ready, _, _ = select.select([self.proxy_process.stdout], [], [], 0)
                            if ready:
                                recent_output = self.proxy_process.stdout.read(1024)
                                if recent_output:
                                    print(f"  • Recent stdout: {recent_output[:200]}...")
                    except Exception:
                        # Non-blocking read failed, that's okay
                        pass
                print()
            else:
                print("\n📊 Proxy process not available for log display\n")

        except Exception as e:
            # Don't fail proxy startup if logging display fails
            print(f"Note: Unable to display log locations: {e}")
