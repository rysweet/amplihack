"""Proxy lifecycle management."""

import atexit
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional

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
            port_str = proxy_config.get("PORT")
            # Handle quoted port values
            if isinstance(port_str, str):
                port_str = port_str.strip('"').strip("'")
            self.proxy_port = int(port_str)
            print(f"Using proxy port from config: {self.proxy_port}")
        else:
            self.proxy_port = 8080  # Default port
            print(f"Using default proxy port: {self.proxy_port}")

    def ensure_proxy_installed(self) -> bool:
        """Ensure claude-code-proxy is installed.

        Returns:
            True if proxy is ready to use, False otherwise.
        """
        proxy_repo = self.proxy_dir / "claude-code-proxy"

        if not proxy_repo.exists():
            print("Claude-code-proxy not found. Cloning...")
            try:
                self.proxy_dir.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "https://github.com/fuergaosi233/claude-code-proxy.git",
                        str(proxy_repo),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                print(f"Successfully cloned claude-code-proxy to {proxy_repo}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to clone claude-code-proxy: {e}")
                return False

        return proxy_repo.exists()

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
            # Log what we're writing for debugging
            print(f"Writing proxy configuration to {target_env}")
            print(f"Configuration keys: {list(self.proxy_config.config.keys())}")
            if "PORT" in self.proxy_config.config:
                print(f"PORT configuration: {self.proxy_config.config['PORT']}")

            self.proxy_config.save_to(target_env)

            # Verify the file was written correctly
            if target_env.exists():
                with open(target_env, "r") as f:
                    content = f.read()
                    if "PORT=" in content:
                        print(f"Successfully wrote PORT configuration to {target_env}")
                    else:
                        print("WARNING: PORT not found in written .env file")

            return True
        except Exception as e:
            print(f"Failed to copy proxy configuration: {e}")
            import traceback

            traceback.print_exc()
            return False

    def start_proxy(self) -> bool:
        """Start the claude-code-proxy server.

        Returns:
            True if proxy started successfully, False otherwise.
        """
        if self.proxy_process and self.proxy_process.poll() is None:
            print("Proxy is already running")
            return True

        if not self.ensure_proxy_installed():
            return False

        if not self.setup_proxy_config():
            return False

        proxy_repo = self.proxy_dir / "claude-code-proxy"

        try:
            # Determine project type and install dependencies
            requirements_txt = proxy_repo / "requirements.txt"
            package_json = proxy_repo / "package.json"

            # Install Python dependencies if needed
            if requirements_txt.exists():
                print("Installing Python proxy dependencies...")
                # Try uv first (preferred in uvx context), fall back to pip3/pip
                # Note: uv needs --system flag to install outside a virtual environment
                pip_commands = [
                    ["uv", "pip", "install", "--system", "-r", "requirements.txt"],
                    ["python3", "-m", "pip", "install", "-r", "requirements.txt"],
                    ["pip3.13", "install", "-r", "requirements.txt"],
                    ["pip3", "install", "-r", "requirements.txt"],
                    ["pip", "install", "-r", "requirements.txt"],
                ]

                install_result = None
                install_success = False
                for pip_cmd in pip_commands:
                    try:
                        print(f"  Trying: {' '.join(pip_cmd)}")
                        # First check if the command exists
                        which_result = subprocess.run(
                            ["which", pip_cmd[0]], capture_output=True, text=True
                        )
                        if which_result.returncode != 0:
                            print(f"  {pip_cmd[0]} not found, trying next option...")
                            continue

                        install_result = subprocess.run(
                            pip_cmd,
                            check=False,
                            cwd=str(proxy_repo),
                            capture_output=True,
                            text=True,
                        )
                        if install_result.returncode == 0:
                            print("  ✓ Python dependencies installed successfully")
                            install_success = True
                            break
                        else:
                            if install_result.stderr and "not found" not in install_result.stderr:
                                print(f"  Failed: {install_result.stderr[:200]}")
                    except FileNotFoundError:
                        print(f"  {pip_cmd[0]} not found, trying next option...")
                        continue
                    except Exception as e:
                        print(f"  Error: {e}")
                        continue

                if not install_success:
                    print("Failed to install Python dependencies with any method")
                    if install_result and install_result.stderr:
                        print(f"Last error: {install_result.stderr}")
                    return False

            # Install npm dependencies if needed
            elif package_json.exists():
                node_modules = proxy_repo / "node_modules"
                if not node_modules.exists():
                    print("Installing npm proxy dependencies...")
                    install_result = subprocess.run(
                        ["npm", "install"],
                        check=False,
                        cwd=str(proxy_repo),
                        capture_output=True,
                        text=True,
                    )
                    if install_result.returncode != 0:
                        print(f"Failed to install npm dependencies: {install_result.stderr}")
                        return False
                    print("npm dependencies installed successfully")

            # Start the proxy process
            print(f"Starting claude-code-proxy on port {self.proxy_port}...")

            # Create environment for the proxy process
            proxy_env = os.environ.copy()
            if self.proxy_config:
                # Add all config values to environment
                config_dict = self.proxy_config.to_env_dict()
                proxy_env.update(config_dict)
                print(f"Added {len(config_dict)} configuration values to proxy environment")
            # Ensure PORT is set for the proxy process (override any existing value)
            proxy_env["PORT"] = str(self.proxy_port)
            print(f"Proxy environment PORT set to: {proxy_env.get('PORT')}")

            # Check if we should use 'npm start' or 'python' based on project structure
            start_command = ["npm", "start"]
            if (proxy_repo / "start_proxy.py").exists():
                # It's a Python project - try uv run first, fall back to python3/python
                # Check if uv is available
                uv_check = subprocess.run(
                    ["which", "uv"], check=False, capture_output=True, shell=True
                )
                if uv_check.returncode == 0:
                    start_command = ["uv", "run", "python", "start_proxy.py"]
                else:
                    # Try python3 first, then python
                    python3_check = subprocess.run(
                        ["which", "python3"], check=False, capture_output=True, shell=True
                    )
                    if python3_check.returncode == 0:
                        start_command = ["python3", "start_proxy.py"]
                    else:
                        start_command = ["python", "start_proxy.py"]
            elif (proxy_repo / "src" / "proxy.py").exists():
                # Alternative Python structure
                uv_check = subprocess.run(
                    ["which", "uv"], check=False, capture_output=True, shell=True
                )
                if uv_check.returncode == 0:
                    start_command = ["uv", "run", "python", "-m", "src.proxy"]
                else:
                    # Try python3 first, then python
                    python3_check = subprocess.run(
                        ["which", "python3"], check=False, capture_output=True, shell=True
                    )
                    if python3_check.returncode == 0:
                        start_command = ["python3", "-m", "src.proxy"]
                    else:
                        start_command = ["python", "-m", "src.proxy"]

            self.proxy_process = subprocess.Popen(
                start_command,
                cwd=str(proxy_repo),
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
            time.sleep(2)

            # Check if proxy is still running
            if self.proxy_process.poll() is not None:
                stdout, stderr = self.proxy_process.communicate(timeout=0.1)
                print(f"Proxy failed to start. Exit code: {self.proxy_process.returncode}")
                if stdout:
                    print(f"Standard output: {stdout}")
                if stderr:
                    print(f"Error output: {stderr}")
                return False

            # Verify the proxy is listening on the expected port
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1)
                        result = s.connect_ex(("127.0.0.1", self.proxy_port))
                        if result == 0:
                            print(f"✓ Verified proxy is listening on port {self.proxy_port}")
                            break
                except Exception:
                    pass
                if attempt < max_attempts - 1:
                    time.sleep(1)
            else:
                print(f"WARNING: Could not verify proxy is listening on port {self.proxy_port}")

            # Set up environment variables
            api_key = self.proxy_config.get("ANTHROPIC_API_KEY") if self.proxy_config else None
            self.env_manager.setup(self.proxy_port, api_key)

            print(f"Proxy started successfully on port {self.proxy_port}")
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
                print(f"Error stopping proxy: {e}")

        # Restore environment variables
        self.env_manager.restore()
        self.proxy_process = None

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
