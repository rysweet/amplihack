"""Copilot CLI launcher with full extensibility parity staging."""

import json
import os
import platform
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from collections.abc import MutableMapping
from datetime import UTC, datetime
from pathlib import Path

from ..context.adaptive.detector import LauncherDetector


def get_gh_auth_account() -> str | None:
    """Check if gh CLI is authenticated and return the account name.

    Returns:
        Account name if authenticated, None otherwise.
    """
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            # Parse output - may be in stdout or stderr depending on environment
            output = result.stdout + result.stderr
            # Parse output like "Logged in to github.com account USERNAME"
            for line in output.split("\n"):
                if "Logged in to" in line and "account" in line:
                    parts = line.split("account")
                    if len(parts) > 1:
                        # Extract account name (format: "account USERNAME (path)")
                        account_part = parts[1].strip()
                        account = account_part.split()[0] if account_part else None
                        return account
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def disable_github_mcp_server() -> bool:
    """Disable the GitHub MCP server by staging an MCP config.

    Creates or updates ~/.copilot/github-copilot/mcp.json to disable
    the github-mcp-server, saving context tokens.

    Returns:
        True if config was staged successfully, False otherwise.
    """
    mcp_config_dir = Path.home() / ".copilot" / "github-copilot"
    mcp_config_file = mcp_config_dir / "mcp.json"

    try:
        # Create directory if needed
        mcp_config_dir.mkdir(parents=True, exist_ok=True)

        # Load existing config or create new
        if mcp_config_file.exists():
            config = json.loads(mcp_config_file.read_text())
        else:
            config = {}

        # Ensure mcpServers exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Disable github-mcp-server
        if "github-mcp-server" not in config["mcpServers"]:
            config["mcpServers"]["github-mcp-server"] = {}

        config["mcpServers"]["github-mcp-server"]["disabled"] = True

        # Write config
        mcp_config_file.write_text(json.dumps(config, indent=2) + "\n")
        return True
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: Could not disable GitHub MCP server: {e}")
        return False


def enable_awesome_copilot_mcp_server() -> bool:
    """Enable the awesome-copilot MCP server for community extensions via Docker.

    Adds the awesome-copilot MCP server to ~/.copilot/github-copilot/mcp.json
    if Docker is available. Uses the read-modify-write pattern to preserve
    existing MCP configuration.

    Returns:
        True if the server was added, False if Docker is not available.
    """
    if not shutil.which("docker"):
        return False

    mcp_config_dir = Path.home() / ".copilot" / "github-copilot"
    mcp_config_file = mcp_config_dir / "mcp.json"

    try:
        mcp_config_dir.mkdir(parents=True, exist_ok=True)

        # Load existing config or create new
        if mcp_config_file.exists():
            config = json.loads(mcp_config_file.read_text())
        else:
            config = {}

        # Ensure mcpServers exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Add awesome-copilot MCP server
        config["mcpServers"]["awesome-copilot"] = {
            "type": "stdio",
            "command": "docker",
            "args": [
                "run",
                "-i",
                "--rm",
                "ghcr.io/microsoft/mcp-dotnet-samples/awesome-copilot:latest",
            ],
        }

        # Write config
        mcp_config_file.write_text(json.dumps(config, indent=2) + "\n")
        return True
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: Could not enable awesome-copilot MCP server: {e}")
        return False


def register_awesome_copilot_marketplace() -> bool:
    """Register awesome-copilot marketplace extensions (best-effort).

    Runs the copilot plugin marketplace add command if not already registered.
    Uses a marker file to avoid re-registering on subsequent launches.

    Returns:
        True if registered (or already registered), False on failure.
    """
    marker = Path.home() / ".copilot" / "awesome-copilot-marketplace-registered"

    if marker.exists():
        return True

    try:
        result = subprocess.run(
            ["copilot", "plugin", "marketplace", "add", "github/awesome-copilot"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0:
            # Create marker file on success
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("registered\n")
            return True
        return False
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _compare_versions(current: str, latest: str) -> bool:
    """Compare version strings to determine if update is available.

    Args:
        current: Current version string (e.g., "1.0.0" or "v1.0.0")
        latest: Latest version string (e.g., "1.0.1")

    Returns:
        True if latest > current, False otherwise
    """
    try:
        # Strip 'v' prefix if present
        current_clean = current.lstrip("v")
        latest_clean = latest.lstrip("v")

        # Parse version strings into tuples of integers
        current_parts = tuple(int(x) for x in current_clean.split("."))
        latest_parts = tuple(int(x) for x in latest_clean.split("."))

        # Python tuple comparison handles semantic versioning correctly
        return latest_parts > current_parts
    except (ValueError, AttributeError):
        # Invalid version format - return False (no update)
        return False


def _get_current_copilot_version(
    env: MutableMapping[str, str] | None = None,
    home: Path | None = None,
) -> str | None:
    """Get the currently installed Copilot CLI version.

    Returns:
        Version string (e.g. "1.4.0") or None if not installed / not parseable.
    """
    effective_env = os.environ if env is None else env
    _ensure_copilot_bin_on_path(env=effective_env, home=home)
    try:
        kwargs: dict = {"capture_output": True, "text": True, "timeout": 10, "check": False}
        if env is not None:
            kwargs["env"] = effective_env
        result = subprocess.run(["copilot", "--version"], **kwargs)
        if result.returncode != 0:
            return None
        output = result.stdout.strip()
        if "/" not in output:
            return None
        parts = output.split("/")
        if len(parts) < 3:
            return None
        return parts[2].split()[0]
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError, IndexError):
        return None


def check_for_update(
    env: MutableMapping[str, str] | None = None,
    home: Path | None = None,
) -> str | None:
    """Check if a newer version of Copilot CLI is available.

    Args:
        env: Environment mapping (defaults to os.environ).
        home: Home directory for Copilot npm-global prefix.

    Returns:
        New version string if update available, None otherwise
    """
    try:
        current_version = _get_current_copilot_version(env=env, home=home)
        if current_version is None:
            return None

        # Get latest version from npm
        effective_env = os.environ if env is None else env
        kwargs: dict = {"capture_output": True, "text": True, "timeout": 15, "check": False}
        if env is not None:
            kwargs["env"] = effective_env
        latest_result = subprocess.run(["npm", "view", "@github/copilot", "version"], **kwargs)
        if latest_result.returncode != 0:
            return None

        latest_version = latest_result.stdout.strip()

        if _compare_versions(current_version, latest_version):
            return latest_version

        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError, IndexError):
        return None


def detect_install_method() -> str:
    """Detect how Copilot CLI was installed.

    Returns:
        'npm' or 'uvx' based on installation method, defaults to 'npm'
    """
    try:
        # Check npm global installation
        npm_result = subprocess.run(
            ["npm", "list", "-g", "@github/copilot"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if npm_result.returncode == 0:
            # If the path contains uv/tools, it's actually uvx
            if "uv/tools" in npm_result.stdout or "uv\\tools" in npm_result.stdout:
                return "uvx"
            return "npm"

        # Check uvx installation if npm check failed
        uvx_result = subprocess.run(
            ["uvx", "list"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if uvx_result.returncode == 0 and "copilot" in uvx_result.stdout:
            return "uvx"

    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "npm"


def prompt_user_to_update(new_version: str, install_method: str) -> bool:
    """Prompt user to update Copilot CLI with timeout.

    Args:
        new_version: The new version available
        install_method: Installation method ('npm' or 'uvx')

    Returns:
        True if user wants to update, False otherwise
    """
    print(f"🔄 Copilot CLI update available: v{new_version}")

    if install_method == "uvx":
        print("  Update: uvx --from @github/copilot@latest copilot")
    else:
        # Default to npm (install_method == "npm" or unknown)
        print("  Update: npm install -g @github/copilot")

    # Cross-platform timeout implementation
    timeout_seconds = 5
    user_input = None

    if platform.system() == "Windows":
        # Windows: Use threading-based timeout
        def get_input():
            nonlocal user_input
            try:
                user_input = input("Update now? (y/N): ").strip().lower()
            except EOFError:
                user_input = ""

        input_thread = threading.Thread(target=get_input)
        input_thread.daemon = True
        input_thread.start()
        input_thread.join(timeout=timeout_seconds)

        if input_thread.is_alive():
            # Timeout occurred - default to No
            print("\nTimeout - skipping update")
            return False
    else:
        # Unix: Use signal-based timeout
        def timeout_handler(signum, frame):
            raise TimeoutError("Input timeout")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)

        try:
            user_input = input("Update now? (y/N): ").strip().lower()
            signal.alarm(0)  # Cancel alarm
        except TimeoutError:
            print("\nTimeout - skipping update")
            signal.signal(signal.SIGALRM, old_handler)
            return False
        except EOFError:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
            return False
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    # Handle empty input or 'n' as No, only 'y' as Yes
    return user_input == "y"


def execute_update(
    install_method: str,
    env: MutableMapping[str, str] | None = None,
    home: Path | None = None,
) -> bool:
    """Execute Copilot CLI update based on installation method.

    Args:
        install_method: Installation method ('npm' or 'uvx')
        env: Environment mapping (defaults to os.environ).
        home: Home directory for npm-global prefix resolution.

    Returns:
        True if update succeeded, False otherwise
    """
    effective_env = os.environ if env is None else env
    _ensure_copilot_bin_on_path(env=effective_env, home=home)

    print(f"\n📦 Updating Copilot CLI via {install_method}...")

    try:
        pre_version = _get_current_copilot_version(env=env, home=home)

        # Execute update command
        run_kwargs: dict = {"check": False}
        if env is not None:
            run_kwargs["env"] = effective_env

        if install_method == "uvx":
            result = subprocess.run(
                ["uvx", "--from", "@github/copilot@latest", "copilot", "--version"],
                capture_output=True,
                text=True,
                timeout=60,
                **run_kwargs,
            )
        else:
            # npm update — use the same --prefix as install_copilot() so the
            # binary lands in the correct npm-global directory.
            npm_prefix = _copilot_home(home=home, env=effective_env) / ".npm-global"
            npm_prefix.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["npm", "install", "-g", "--prefix", str(npm_prefix), "@github/copilot"],
                capture_output=True,
                text=True,
                timeout=120,
                **run_kwargs,
            )

        if result.returncode != 0:
            print(f"✗ Update failed: {result.stderr.strip()}")
            return False

        # Verify update by checking version
        post_version = _get_current_copilot_version(env=env, home=home)
        if post_version:
            if pre_version and post_version != pre_version:
                print(f"✓ Updated from {pre_version} to {post_version}")
            else:
                print(f"✓ Update complete (version: {post_version})")
            return True

        # If version check fails but update command succeeded
        print("✓ Update completed")
        return True

    except subprocess.TimeoutExpired:
        print("✗ Update timed out")
        return False
    except FileNotFoundError:
        print(f"✗ Update failed: {install_method} not found")
        return False
    except Exception as e:
        print(f"✗ Update failed: {e}")
        return False


def ensure_latest_copilot(
    env: MutableMapping[str, str] | None = None,
    home: Path | None = None,
) -> bool:
    """Ensure the latest Copilot CLI is installed, updating automatically if needed.

    This is the primary pre-launch update gate. It runs without user prompts
    so that new CLI flags (e.g. --autopilot) are always available.

    Set AMPLIHACK_SKIP_UPDATE=1 to bypass the update check.

    Args:
        env: Environment mapping (defaults to os.environ).
        home: Home directory for npm-global prefix resolution.

    Returns:
        True if copilot is up-to-date (or was successfully updated), False on
        update failure (launch should still proceed with the current version).
    """
    effective_env = os.environ if env is None else env

    if effective_env.get("AMPLIHACK_SKIP_UPDATE", "") == "1":
        return True

    _ensure_copilot_bin_on_path(env=effective_env, home=home)

    # If copilot isn't installed at all, install_copilot() handles that separately
    if not check_copilot(env=env, home=home):
        return True  # let the caller's install_copilot() path handle this

    try:
        new_version = check_for_update(env=env, home=home)
        if new_version is None:
            return True  # already up-to-date (or couldn't check — don't block)

        current = _get_current_copilot_version(env=env, home=home) or "unknown"
        print(f"🔄 Copilot CLI update available: {current} → {new_version}")

        install_method = detect_install_method()
        if execute_update(install_method, env=env, home=home):
            return True

        print("⚠ Update failed — continuing with current version")
        return False
    except Exception as e:
        import logging

        logging.getLogger(__name__).debug(f"Copilot auto-update failed: {type(e).__name__}: {e}")
        return False


def _copilot_home(home: Path | None = None, env: MutableMapping[str, str] | None = None) -> Path:
    """Resolve the home directory used for Copilot installation/discovery."""
    if home is not None:
        return home.expanduser().resolve()
    if env is not None and env.get("HOME"):
        return Path(env["HOME"]).expanduser().resolve()
    return Path.home()


def _copilot_npm_bin(home: Path | None = None, env: MutableMapping[str, str] | None = None) -> Path:
    """Return the npm-global bin directory used for Copilot CLI installs."""
    return _copilot_home(home=home, env=env) / ".npm-global" / "bin"


def _ensure_copilot_bin_on_path(
    env: MutableMapping[str, str] | None = None, home: Path | None = None
) -> Path:
    """Prepend the Copilot npm-global bin dir to PATH for the selected environment."""
    target_env = os.environ if env is None else env
    bin_path = _copilot_npm_bin(home=home, env=target_env)
    current_path = target_env.get("PATH", "")
    path_entries = [entry for entry in current_path.split(os.pathsep) if entry]
    if str(bin_path) not in path_entries:
        target_env["PATH"] = (
            f"{bin_path}{os.pathsep}{current_path}" if current_path else str(bin_path)
        )
    return bin_path


def check_copilot(env: MutableMapping[str, str] | None = None, home: Path | None = None) -> bool:
    """Check if Copilot CLI is installed.

    Returns:
        bool: True if copilot is available, False otherwise

    Note:
        Handles FileNotFoundError (not installed), PermissionError (WSL),
        and TimeoutExpired (hanging command) gracefully.
    """
    effective_env = os.environ if env is None else env
    _ensure_copilot_bin_on_path(env=effective_env, home=home)
    try:
        kwargs = {"capture_output": True, "timeout": 5, "check": False}
        if env is not None:
            kwargs["env"] = effective_env
        subprocess.run(["copilot", "--version"], **kwargs)
        return True
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        return False


def install_copilot(env: MutableMapping[str, str] | None = None, home: Path | None = None) -> bool:
    """Install GitHub Copilot CLI via npm to user-local directory."""
    print("Installing GitHub Copilot CLI...")

    effective_env = os.environ if env is None else env
    npm_prefix = _copilot_home(home=home, env=effective_env) / ".npm-global"
    npm_prefix.mkdir(parents=True, exist_ok=True)

    try:
        if env is not None:
            result = subprocess.run(
                ["npm", "install", "-g", "--prefix", str(npm_prefix), "@github/copilot"],
                check=False,
                env=effective_env,
            )
        else:
            result = subprocess.run(
                ["npm", "install", "-g", "--prefix", str(npm_prefix), "@github/copilot"],
                check=False,
            )
        if result.returncode == 0:
            print("✓ Copilot CLI installed")

            # Add to PATH for current process
            bin_path = npm_prefix / "bin"
            path_env = effective_env.get("PATH", "")
            path_entries = [entry for entry in path_env.split(os.pathsep) if entry]
            if str(bin_path) not in path_entries:
                _ensure_copilot_bin_on_path(env=effective_env, home=home)
                print(f"\n⚠️  Added to PATH for this session: {bin_path}")
                print("   Add to ~/.bashrc or ~/.zshrc for persistence:")
                print(f'   export PATH="{bin_path}:$PATH"')

            return True
        print("✗ Installation failed")
        return False
    except FileNotFoundError:
        print("Error: npm not found. Install Node.js first.")
        return False


def stage_agents(source_agents: Path, copilot_home: Path) -> int:
    """Stage amplihack agents to ~/.copilot/agents/amplihack/ for Copilot CLI discovery.

    Copilot CLI searches ~/.copilot/agents/ (user-level) before .github/agents/
    (repo-level). Staging to a namespaced subdirectory ensures agents are discoverable
    in ANY repo while preserving user-managed agents in ~/.copilot/agents/.
    (Fix for issue #2241)

    Args:
        source_agents: Path to amplihack agent source directory
            (e.g. package_dir/.claude/agents/amplihack/)
        copilot_home: Path to copilot home directory (e.g. ~/.copilot/)

    Returns:
        Number of agents staged
    """
    if not source_agents.exists():
        return 0

    # Namespace under agents/amplihack/ to avoid deleting user agents
    agents_dest = copilot_home / "agents" / "amplihack"
    agents_dest.mkdir(parents=True, exist_ok=True)

    # Clean only amplihack's staging directory (not all of ~/.copilot/agents/)
    for old_file in agents_dest.glob("*.md"):
        old_file.unlink()

    # Flatten structure: core/architect.md → amplihack/architect.md
    # NOTE: Assumes no basename collisions across subdirectories (core/, specialized/, workflows/)
    copied = 0
    for source_file in source_agents.rglob("*.md"):
        dest_file = agents_dest / source_file.name
        shutil.copy2(source_file, dest_file)
        copied += 1

    return copied


def register_copilot_plugin(source_commands: Path, copilot_home: Path) -> bool:
    """Register amplihack as a Copilot CLI local plugin and stage command files.

    Copilot CLI only discovers commands from registered plugins (not from
    ~/.copilot/commands/ directly). This function:
    1. Copies command .md files to ~/.copilot/installed-plugins/amplihack@local/commands/
    2. Copies plugin.json to ~/.copilot/installed-plugins/amplihack@local/
    3. Registers the plugin in ~/.copilot/config.json under installed_plugins

    Args:
        source_commands: Path to amplihack commands source directory
            (e.g. package_dir/.claude/commands/amplihack/)
        copilot_home: Path to copilot home directory (e.g. ~/.copilot/)

    Returns:
        True if registration succeeded, False otherwise
    """
    if not source_commands.exists():
        return False

    plugin_cache = copilot_home / "installed-plugins" / "amplihack@local"
    plugin_commands_dest = plugin_cache / "commands"
    plugin_commands_dest.mkdir(parents=True, exist_ok=True)

    # Copy plugin.json to plugin root
    plugin_json_src = source_commands / "plugin.json"
    if plugin_json_src.exists():
        shutil.copy2(plugin_json_src, plugin_cache / "plugin.json")

    # Copy all command .md files (skip plugin.json)
    copied = 0
    for source_file in source_commands.glob("*.md"):
        shutil.copy2(source_file, plugin_commands_dest / source_file.name)
        copied += 1

    if copied == 0:
        return False

    # Register plugin in ~/.copilot/config.json
    config_file = copilot_home / "config.json"
    try:
        if config_file.exists():
            config = json.loads(config_file.read_text())
        else:
            config = {}

        if "installed_plugins" not in config:
            config["installed_plugins"] = []

        # Remove existing amplihack entry if present (idempotent update)
        config["installed_plugins"] = [
            p for p in config["installed_plugins"] if p.get("name") != "amplihack"
        ]

        config["installed_plugins"].append(
            {
                "name": "amplihack",
                "marketplace": "local",
                "version": "1.0.0",
                "enabled": True,
                "cache_path": str(plugin_cache),
                "source": "local",
                "installed_at": datetime.now(UTC).isoformat(),
            }
        )

        copilot_home.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps(config, indent=2) + "\n")
        return True
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: Could not update Copilot CLI config.json: {e}")
        return False


# Required fields for installed_plugins entries in config.json.
# Copilot CLI validates these on startup — missing fields cause crashes.
# See issue #3671.
REQUIRED_PLUGIN_FIELDS: dict[str, str | bool] = {
    "name": "unknown",
    "marketplace": "local",
    "version": "0.0.0",
    "enabled": True,
    "cache_path": "",
    "source": "unknown",
    "installed_at": "1970-01-01T00:00:00+00:00",
}


def validate_and_repair_copilot_config(copilot_home: Path) -> bool:
    """Validate and repair installed_plugins entries in config.json.

    Reads config.json, checks each installed_plugins entry for missing
    required fields, and backfills them with safe defaults.  Only writes
    the file if changes were actually made (write-only-when-dirty).

    Returns True if config is valid (or was successfully repaired),
    False if validation failed and could not be repaired.
    """
    config_file = copilot_home / "config.json"
    if not config_file.exists():
        return True

    try:
        raw = config_file.read_text()
        config = json.loads(raw)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: Could not read Copilot config.json for validation: {e}")
        return False

    if "installed_plugins" not in config:
        return True

    plugins = config["installed_plugins"]
    if not isinstance(plugins, list):
        return True

    dirty = False
    repaired_count = 0

    for entry in plugins:
        if not isinstance(entry, dict):
            continue

        entry_repaired = False
        for field, default in REQUIRED_PLUGIN_FIELDS.items():
            if field not in entry or not isinstance(entry[field], type(default)):
                entry[field] = default
                entry_repaired = True

        if entry_repaired:
            dirty = True
            repaired_count += 1

    if not dirty:
        return True

    try:
        config_file.write_text(json.dumps(config, indent=2) + "\n")
        print(f"Repaired {repaired_count} installed_plugins entries in config.json (issue #3671)")
        return True
    except OSError as e:
        print(f"Warning: Could not write repaired config.json: {e}")
        return False


def stage_directory(source_dir: Path, copilot_home: Path, dest_name: str) -> int:
    """Stage a directory of .md files to ~/.copilot/<dest_name>/amplihack/.

    Flattens any subdirectory structure. Stages to a namespaced subdirectory
    to preserve user-added content in ~/.copilot/<dest_name>/.

    Args:
        source_dir: Source directory containing .md files (may have subdirs)
        copilot_home: Path to copilot home directory (e.g. ~/.copilot/)
        dest_name: Subdirectory name under copilot_home (e.g. "workflow")

    Returns:
        Number of files staged
    """
    if not source_dir.exists():
        return 0

    # Namespace under <dest_name>/amplihack/ to avoid deleting user content
    dest = copilot_home / dest_name / "amplihack"
    dest.mkdir(parents=True, exist_ok=True)

    # Clean only amplihack's staging directory (not all of ~/.copilot/<dest_name>/)
    for old_file in dest.glob("*.md"):
        old_file.unlink()

    copied = 0
    for source_file in source_dir.rglob("*.md"):
        shutil.copy2(source_file, dest / source_file.name)
        copied += 1

    return copied


def stage_hooks(package_dir: Path, user_dir: Path) -> int:
    """Stage amplihack hooks for Copilot CLI discovery.

    Copilot CLI reads hooks from .github/hooks/ in the repo root.
    This function:
    1. Copies amplihack-hooks.json to user's .github/hooks/
    2. Creates bash wrapper scripts that invoke hooks

    When AMPLIHACK_HOOK_ENGINE=rust, hooks with Rust equivalents use the
    amplihack-hooks binary. Hooks without Rust equivalents (e.g.,
    workflow_classification_reminder.py) still use Python.

    Existing user hooks are preserved — only amplihack-managed hooks are written.
    A hook is considered amplihack-managed if it contains "amplihack" in its content.

    Args:
        package_dir: Path to amplihack package directory
        user_dir: Path to user's working directory (repo root)

    Returns:
        Number of hooks staged
    """
    from ..settings import find_rust_hook_binary, get_hook_engine

    # Source hooks manifest from the package's .github/hooks/
    # Try package .github first, then repo root .github
    source_hooks_json = package_dir / ".github" / "hooks" / "amplihack-hooks.json"
    if not source_hooks_json.exists():
        source_hooks_json = package_dir.parent.parent / ".github" / "hooks" / "amplihack-hooks.json"
    if not source_hooks_json.exists():
        return 0

    # Target: user's repo .github/hooks/
    target_hooks_dir = user_dir / ".github" / "hooks"
    target_hooks_dir.mkdir(parents=True, exist_ok=True)

    # Copy hooks manifest (amplihack-specific, safe to overwrite)
    shutil.copy2(source_hooks_json, target_hooks_dir / "amplihack-hooks.json")

    # Determine hook engine
    hook_engine = get_hook_engine()
    rust_binary = None
    if hook_engine == "rust":
        rust_binary = find_rust_hook_binary()
        if rust_binary is None:
            raise FileNotFoundError(
                "AMPLIHACK_HOOK_ENGINE=rust but amplihack-hooks binary not found. "
                "Install it from https://github.com/rysweet/amplihack-rs or set "
                "AMPLIHACK_HOOK_ENGINE=python."
            )

    # Import the mapping
    from .. import RUST_HOOK_MAP

    # Map of copilot hook names to Python implementation filenames
    # Events with multiple scripts use a list — all scripts run sequentially
    hook_map = {
        "session-start": ["session_start.py"],
        "session-stop": ["stop.py", "session_stop.py"],
        "pre-tool-use": ["pre_tool_use.py"],
        "post-tool-use": ["post_tool_use.py"],
        "user-prompt-submit": ["user_prompt_submit.py", "workflow_classification_reminder.py"],
    }
    # pre-compact is NOT listed here — Copilot CLI does not support this event type.
    # It is only available via Claude Code's settings.json (see HOOK_CONFIGS).

    # error-occurred is handled by the bash wrapper directly (no Python hook)

    staged = 0
    for hook_name, py_files in hook_map.items():
        wrapper_path = target_hooks_dir / hook_name

        # Preserve existing user hooks that are NOT amplihack-managed
        if wrapper_path.exists():
            existing = wrapper_path.read_text(errors="replace")
            if "amplihack" not in existing:
                continue  # User's own hook, don't overwrite

        if hook_name == "pre-tool-use":
            wrapper_content = _generate_pre_tool_use_wrapper(
                hook_engine=hook_engine,
                rust_binary=rust_binary,
                rust_hook_map=RUST_HOOK_MAP,
            )
        elif hook_engine == "rust":
            wrapper_content = _generate_rust_wrapper(
                hook_name, py_files, rust_binary, RUST_HOOK_MAP
            )
        elif len(py_files) == 1:
            # Single-script hook — use exec for exit code propagation
            py_file = py_files[0]
            wrapper_content = f"""#!/usr/bin/env bash
# Copilot hook wrapper - generated by amplihack
HOOK="{py_file}"
AMPLIHACK_HOOKS="$HOME/.amplihack/.claude/tools/amplihack/hooks"

if [[ -f "${{AMPLIHACK_HOOKS}}/${{HOOK}}" ]]; then
    exec python3 "${{AMPLIHACK_HOOKS}}/${{HOOK}}" "$@"
elif REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" && [[ -f "${{REPO_ROOT}}/.claude/tools/amplihack/hooks/${{HOOK}}" ]]; then
    exec python3 "${{REPO_ROOT}}/.claude/tools/amplihack/hooks/${{HOOK}}" "$@"
else
    echo "{{}}"
fi
"""
        else:
            # Multi-script hook — capture stdin, pipe to each script
            script_blocks = []
            for py_file in py_files:
                script_blocks.append(f"""if [[ -f "${{AMPLIHACK_HOOKS}}/{py_file}" ]]; then
    echo "$INPUT" | python3 "${{AMPLIHACK_HOOKS}}/{py_file}" "$@" 2>/dev/null || true
elif [[ -n "$REPO_ROOT" ]] && [[ -f "${{REPO_ROOT}}/.claude/tools/amplihack/hooks/{py_file}" ]]; then
    echo "$INPUT" | python3 "${{REPO_ROOT}}/.claude/tools/amplihack/hooks/{py_file}" "$@" 2>/dev/null || true
fi""")

            scripts_joined = "\n\n".join(script_blocks)
            wrapper_content = f"""#!/usr/bin/env bash
# Copilot hook wrapper - generated by amplihack
# Runs multiple hook scripts for this event
AMPLIHACK_HOOKS="$HOME/.amplihack/.claude/tools/amplihack/hooks"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || REPO_ROOT=""
INPUT=$(cat)

{scripts_joined}
"""

        wrapper_path.write_text(wrapper_content)
        if sys.platform != "win32":
            wrapper_path.chmod(0o755)
        staged += 1

    # Stage the error-occurred wrapper separately (no Python hook, uses inline fallback)
    error_wrapper = target_hooks_dir / "error-occurred"
    if not error_wrapper.exists() or "amplihack" in error_wrapper.read_text(errors="replace"):
        source_error = package_dir.parent.parent / ".github" / "hooks" / "error-occurred"
        if source_error.exists():
            shutil.copy2(source_error, error_wrapper)
            if sys.platform != "win32":
                error_wrapper.chmod(0o755)
            staged += 1

    return staged


def _generate_rust_wrapper(hook_name, py_files, rust_binary, rust_hook_map):
    """Generate a bash wrapper script that uses the Rust hook binary.

    For hooks with Rust equivalents, uses ``amplihack-hooks <subcommand>``.
    For hooks without (e.g., workflow_classification_reminder.py), uses Python.
    Multi-script events run each script sequentially.
    """
    # Partition files into Rust and Python
    rust_commands = []
    python_files = []
    for py_file in py_files:
        subcmd = rust_hook_map.get(py_file)
        if subcmd:
            rust_commands.append((py_file, subcmd))
        else:
            python_files.append(py_file)

    if len(rust_commands) == 1 and not python_files:
        # Single Rust hook — use exec for exit code propagation
        _, subcmd = rust_commands[0]
        quoted_binary = shlex.quote(rust_binary)
        return f"""#!/usr/bin/env bash
# Copilot hook wrapper - generated by amplihack (rust engine)
exec {quoted_binary} {subcmd} "$@"
"""

    # Multi-command: capture stdin, pipe to each
    quoted_binary = shlex.quote(rust_binary)
    blocks = []
    for _, subcmd in rust_commands:
        blocks.append(f'echo "$INPUT" | {quoted_binary} {subcmd} "$@" || true')
    for py_file in python_files:
        blocks.append(f"""AMPLIHACK_HOOKS="$HOME/.amplihack/.claude/tools/amplihack/hooks"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || REPO_ROOT=""
if [[ -f "${{AMPLIHACK_HOOKS}}/{py_file}" ]]; then
    echo "$INPUT" | python3 "${{AMPLIHACK_HOOKS}}/{py_file}" "$@" 2>/dev/null || true
elif [[ -n "$REPO_ROOT" ]] && [[ -f "${{REPO_ROOT}}/.claude/tools/amplihack/hooks/{py_file}" ]]; then
    echo "$INPUT" | python3 "${{REPO_ROOT}}/.claude/tools/amplihack/hooks/{py_file}" "$@" 2>/dev/null || true
fi""")

    body = "\n\n".join(blocks)
    return f"""#!/usr/bin/env bash
# Copilot hook wrapper - generated by amplihack (rust engine)
# Runs multiple hook scripts for this event
INPUT=$(cat)

{body}
"""


def _generate_pre_tool_use_wrapper(hook_engine, rust_binary, rust_hook_map):
    """Generate the Copilot pre-tool-use wrapper.

    The pre-tool path is special because it needs one JSON response on stdout.
    We therefore capture the amplihack and XPIA hook results independently,
    then normalize them into a single Claude/Copilot-style permission payload.
    """
    rust_subcmd = rust_hook_map.get("pre_tool_use.py")
    if hook_engine == "rust" and rust_binary and rust_subcmd:
        amplihack_capture = (
            f'AMPLIHACK_OUTPUT=$(echo "$INPUT" | {shlex.quote(rust_binary)} {rust_subcmd} "$@" '
            "2>/dev/null || printf '{}')"
        )
    else:
        amplihack_capture = """AMPLIHACK_OUTPUT="{}"
AMPLIHACK_HOOKS="$HOME/.amplihack/.claude/tools/amplihack/hooks"
if [[ -f "${AMPLIHACK_HOOKS}/pre_tool_use.py" ]]; then
    AMPLIHACK_OUTPUT=$(echo "$INPUT" | python3 "${AMPLIHACK_HOOKS}/pre_tool_use.py" "$@" 2>/dev/null || printf '{}')
elif [[ -n "$REPO_ROOT" ]] && [[ -f "${REPO_ROOT}/.claude/tools/amplihack/hooks/pre_tool_use.py" ]]; then
    AMPLIHACK_OUTPUT=$(echo "$INPUT" | python3 "${REPO_ROOT}/.claude/tools/amplihack/hooks/pre_tool_use.py" "$@" 2>/dev/null || printf '{}')
fi"""

    xpia_capture = """XPIA_OUTPUT="{}"
XPIA_HOOKS="$HOME/.amplihack/.claude/tools/xpia/hooks"
if [[ -f "${XPIA_HOOKS}/pre_tool_use.py" ]]; then
    XPIA_OUTPUT=$(echo "$INPUT" | python3 "${XPIA_HOOKS}/pre_tool_use.py" "$@" 2>/dev/null || printf '{}')
elif [[ -n "$REPO_ROOT" ]] && [[ -f "${REPO_ROOT}/.claude/tools/xpia/hooks/pre_tool_use.py" ]]; then
    XPIA_OUTPUT=$(echo "$INPUT" | python3 "${REPO_ROOT}/.claude/tools/xpia/hooks/pre_tool_use.py" "$@" 2>/dev/null || printf '{}')
fi"""

    return f"""#!/usr/bin/env bash
# Copilot hook wrapper - generated by amplihack ({hook_engine} engine)
# Aggregates amplihack and XPIA pre-tool validation into one JSON response
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || REPO_ROOT=""
INPUT=$(cat)

{amplihack_capture}

{xpia_capture}

python3 - "$AMPLIHACK_OUTPUT" "$XPIA_OUTPUT" <<'PY'
import json
import sys


def parse_payload(raw: str) -> dict:
    raw = raw.strip()
    if not raw:
        return {{}}
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return {{}}


amplihack = parse_payload(sys.argv[1])
xpia = parse_payload(sys.argv[2])

permission = xpia.get("permissionDecision")
if permission in {{"allow", "deny", "ask"}}:
    print(json.dumps(xpia))
    raise SystemExit(0)

permission = amplihack.get("permissionDecision")
if permission in {{"allow", "deny", "ask"}}:
    print(json.dumps(amplihack))
    raise SystemExit(0)

if amplihack.get("block"):
    print(
        json.dumps(
            {{
                "permissionDecision": "deny",
                "message": amplihack.get(
                    "message",
                    "Blocked by amplihack pre-tool-use hook.",
                ),
            }}
        )
    )
    raise SystemExit(0)

print("{{}}")
PY
"""


INSTRUCTIONS_MARKER_START = "<!-- AMPLIHACK_INSTRUCTIONS_START -->"
INSTRUCTIONS_MARKER_END = "<!-- AMPLIHACK_INSTRUCTIONS_END -->"


def _read_text_if_exists(path: Path) -> str:
    """Read a text file if it exists, otherwise return an empty string."""
    return path.read_text() if path.exists() else ""


def _extract_heading_block(text: str, start_heading: str, end_heading: str) -> str:
    """Extract a markdown section bounded by two headings."""
    start = text.find(start_heading)
    if start == -1:
        return ""

    block = text[start:]
    end = block.find(end_heading)
    if end != -1:
        block = block[:end]

    return block.strip()


def build_copilot_agents_context(claude_dir: Path, preferences_text: str | None = None) -> str:
    """Build the AGENTS.md context Copilot needs for workflow enforcement."""
    routing_prompt = _read_text_if_exists(
        claude_dir / "tools" / "amplihack" / "hooks" / "templates" / "routing_prompt.txt"
    ).strip()
    dev_skill = _read_text_if_exists(claude_dir / "skills" / "dev-orchestrator" / "SKILL.md")
    execution_block = _extract_heading_block(
        dev_skill, "## Execution Instructions", "## Task Type Classification"
    )

    sections = [
        "## Amplihack Copilot Workflow Rules\n\n"
        "For any DEV, INVESTIGATE, or HYBRID request, invoke "
        '`Skill(skill="dev-orchestrator")` immediately.\n\n'
        "After the skill is activated, the next tool call must execute the "
        '`smart-orchestrator` recipe via `run_recipe_by_name("smart-orchestrator")`.\n\n'
        "Do not follow the workflow manually and do not fall back to legacy "
        "`ultrathink` behavior.",
    ]

    if routing_prompt:
        sections.append("## Auto-routing prompt\n\n" + routing_prompt)

    if execution_block:
        sections.append(execution_block)

    if preferences_text:
        sections.append("## User Preferences\n\n" + preferences_text.strip())

    return "\n\n".join(section for section in sections if section)


def generate_copilot_instructions(copilot_home: Path) -> None:
    """Inject amplihack section into ~/.copilot/copilot-instructions.md.

    Preserves any existing user content. Uses HTML comment markers to
    isolate amplihack's section so it can be updated without overwriting
    the user's own instructions.

    Args:
        copilot_home: Path to copilot home directory (e.g. ~/.copilot/)
    """
    instructions = copilot_home / "copilot-instructions.md"
    copilot_home.mkdir(parents=True, exist_ok=True)

    # Auto-derive workflow step count from DEFAULT_WORKFLOW.md
    workflow_desc = "Standard development workflow"
    default_workflow = copilot_home / "workflow" / "amplihack" / "DEFAULT_WORKFLOW.md"
    if default_workflow.exists():
        import re

        content = default_workflow.read_text()
        # Count "### Step N" patterns (including decimal steps like 5.5, 7.5)
        steps = re.findall(r"^### Step \d+(?:\.\d+)?:", content, re.MULTILINE)
        if steps:
            workflow_desc = f"Standard development workflow ({len(steps)} steps)"

    amplihack_section = f"""\
{INSTRUCTIONS_MARKER_START}
# Amplihack Framework Integration

You have access to the amplihack agentic coding framework. Use these resources:

## Workflows
Read workflow files from `{copilot_home}/workflow/amplihack/` to follow structured processes:
- `DEFAULT_WORKFLOW.md` — {workflow_desc}
- `INVESTIGATION_WORKFLOW.md` — Research and exploration (6 phases)
- `CASCADE_WORKFLOW.md`, `DEBATE_WORKFLOW.md`, `N_VERSION_WORKFLOW.md` — Fault tolerance patterns

    For any non-trivial development or investigation task, use `/dev` (or `Skill(skill="dev-orchestrator")`)
    so the smart-orchestrator recipe executes the workflow instead of handling it manually.

## Context
Read context files from `{copilot_home}/context/amplihack/` for project philosophy and patterns:
- `PHILOSOPHY.md` — Core principles (ruthless simplicity, zero-BS, modular design)
- `PATTERNS.md` — Reusable solution patterns
- `TRUST.md` — Anti-sycophancy and direct communication guidelines
- `USER_PREFERENCES.md` — User-specific preferences (MANDATORY)

    ## Commands
    Read command definitions from `{copilot_home}/commands/amplihack/` for available capabilities:
    - `dev.md` — Primary dev-orchestrator entry point
    - `ultrathink.md` — Deprecated alias to `/dev`
    - `analyze.md` — Comprehensive code review
    - `improve.md` — Self-improvement and learning capture

## Agents
Custom agents are available at `{copilot_home}/agents/amplihack/`. Use them via the task tool.

## Skills
Skills are available at `{copilot_home}/skills/`. They auto-activate based on context.
{INSTRUCTIONS_MARKER_END}"""

    if instructions.exists():
        existing = instructions.read_text()
        # Replace existing amplihack section if present
        if INSTRUCTIONS_MARKER_START in existing:
            import re

            pattern = (
                re.escape(INSTRUCTIONS_MARKER_START) + r".*?" + re.escape(INSTRUCTIONS_MARKER_END)
            )
            updated = re.sub(pattern, amplihack_section, existing, flags=re.DOTALL)
            instructions.write_text(updated)
        else:
            # Append amplihack section to existing user content
            instructions.write_text(existing.rstrip() + "\n\n" + amplihack_section + "\n")
    else:
        instructions.write_text(amplihack_section + "\n")


def get_copilot_directories() -> list[str]:
    """Get list of directories to provide copilot filesystem access.

    Returns:
        List of existing directory paths as strings.
        Non-existent directories are silently skipped.
    """
    directories = []

    # Collect candidate directories
    candidates = [
        Path.home(),
        Path(tempfile.gettempdir()),
        Path(os.getcwd()),
    ]

    # Filter to only existing directories
    for path in candidates:
        try:
            if path.exists() and path.is_dir():
                directories.append(str(path))
        except (OSError, RuntimeError):
            # Skip directories that raise errors (permissions, broken symlinks, etc.)
            continue

    return directories


def launch_copilot(args: list[str] | None = None, interactive: bool = True) -> int:
    """Launch Copilot CLI.

    Args:
        args: Arguments to pass to copilot
        interactive: If True, use subprocess for proper terminal handling on Windows

    Returns:
        Exit code
    """
    # Auto-update to latest version before launching (fixes #3097).
    # This ensures new flags like --autopilot are always supported.
    try:
        ensure_latest_copilot()
    except Exception:
        pass  # non-critical — continue with current version

    # Ensure copilot is installed
    if not check_copilot():
        if not install_copilot():
            print("Failed to install Copilot CLI")
            return 1

    # Disable GitHub MCP server to save context tokens
    # Users can re-enable by asking "please use the GitHub MCP server"
    if disable_github_mcp_server():
        print("✓ Disabled GitHub MCP server to save context tokens - using gh CLI instead")
        gh_account = get_gh_auth_account()
        if gh_account:
            print(f"  Using gh CLI with account: {gh_account}")
        else:
            print("  ⚠ gh CLI not authenticated - run 'gh auth login' for GitHub access")
        print("  To re-enable GitHub MCP, just ask: 'please use the GitHub MCP server'")

    # Enable awesome-copilot MCP server (requires Docker)
    if enable_awesome_copilot_mcp_server():
        print("✓ Enabled awesome-copilot MCP server (community extensions via Docker)")

    # Register awesome-copilot marketplace extensions (best-effort, silent on failure)
    register_awesome_copilot_marketplace()

    # Ensure XPIA defender binary is installed (security-critical, fail-closed)
    try:
        from ..security.xpia_install import ensure_xpia_binary

        binary_path = ensure_xpia_binary()
        print(f"✓ XPIA security defender ready ({binary_path})")
    except ImportError:
        # Module not available — installer not yet integrated, warn but continue
        import logging

        logging.getLogger(__name__).warning("XPIA installer module not found")
        print("⚠ XPIA defender installer not available (module missing)")
    except Exception as e:
        # Installation failed — warn loudly but don't block startup.
        # The pre-tool-use hook will enforce fail-closed at validation time.
        import logging

        logging.getLogger(__name__).error("XPIA defender binary install failed: %s", e)
        print(f"⚠ XPIA defender not installed: {e}")
        print("  Security validation will block tool use until xpia-defend is available.")

    # Prompt to re-enable power-steering if disabled (#2544)
    try:
        from ..power_steering.re_enable_prompt import prompt_re_enable_if_disabled

        prompt_re_enable_if_disabled()
    except Exception as e:
        # Fail-open: log error but continue
        import logging

        logging.getLogger(__name__).debug(f"Error checking power-steering re-enable prompt: {e}")

    # Write launcher context before launching
    project_root = Path(os.getcwd())
    detector = LauncherDetector(project_root)
    # Sanitize args for safe logging
    safe_args = " ".join(shlex.quote(arg) for arg in (args or []))
    detector.write_context(
        launcher_type="copilot",
        command=f"amplihack copilot {safe_args}",
        environment={"AMPLIHACK_LAUNCHER": "copilot"},
    )

    # CRITICAL: Create agent files and AGENTS.md BEFORE launching Copilot
    # Copilot autodiscovers these at startup
    try:
        import amplihack

        from ..context.adaptive.strategies import CopilotStrategy

        # Get package directory (where .claude/ is actually staged)
        package_dir = Path(amplihack.__file__).parent

        # User's working directory
        user_dir = Path(os.getcwd())

        strategy = CopilotStrategy(user_dir)

        # Copilot home directory — all user-level staging goes here
        copilot_home = Path.home() / ".copilot"

        # Stage ALL extensibility mechanisms to ~/.copilot/ for parity
        # with Claude Code. Copilot CLI discovers agents/skills natively;
        # workflows/context/commands are referenced via copilot-instructions.md.
        claude_dir = package_dir / ".claude"

        # Agents (flattened from core/specialized/workflows subdirs)
        n = stage_agents(claude_dir / "agents/amplihack", copilot_home)
        if n > 0:
            print(f"✓ Staged {n} agents to ~/.copilot/agents/")

        # Skills (directory trees, not flattened)
        source_skills = claude_dir / "skills"
        if source_skills.exists():
            skills_dest = copilot_home / "skills"
            skills_dest.mkdir(parents=True, exist_ok=True)
            skills_copied = 0
            for skill_dir in source_skills.iterdir():
                if skill_dir.is_dir():
                    dest_skill = skills_dest / skill_dir.name
                    is_new = not dest_skill.exists()
                    shutil.copytree(skill_dir, dest_skill, dirs_exist_ok=True)
                    if is_new:
                        skills_copied += 1
            if skills_copied > 0:
                print(f"✓ Staged {skills_copied} new skills to ~/.copilot/skills/")

        # Workflows
        n = stage_directory(claude_dir / "workflow", copilot_home, "workflow")
        if n > 0:
            print(f"✓ Staged {n} workflows to ~/.copilot/workflow/")

        # Context (philosophy, patterns, preferences, etc.)
        n = stage_directory(claude_dir / "context", copilot_home, "context")
        if n > 0:
            print(f"✓ Staged {n} context files to ~/.copilot/context/")

        # Commands — register as a proper Copilot CLI plugin so commands are discoverable.
        # ~/.copilot/commands/ is not a supported location; Copilot only loads from
        # registered plugins (installed_plugins in config.json) or Skills.
        # (Fix for issue #2686)
        if register_copilot_plugin(claude_dir / "commands" / "amplihack", copilot_home):
            print(
                "✓ Registered amplihack as Copilot CLI plugin (~/.copilot/installed-plugins/amplihack@local/)"
            )

        # Hooks (bash wrappers + amplihack-hooks.json to .github/hooks/)
        n = stage_hooks(package_dir, user_dir)
        if n > 0:
            print(f"✓ Staged {n} hooks to .github/hooks/")

        # Generate copilot-instructions.md so copilot knows where everything is
        generate_copilot_instructions(copilot_home)

        # Inject workflow instructions and preferences into AGENTS.md for Copilot context.
        # Copilot's UserPromptSubmit hook is observe-only, so AGENTS.md must carry the
        # actual routing/workflow instructions up front.
        prefs_file = user_dir / ".claude/context/USER_PREFERENCES.md"
        if not prefs_file.exists():
            prefs_file = claude_dir / "context/USER_PREFERENCES.md"
        preferences_text = prefs_file.read_text() if prefs_file.exists() else None
        strategy.inject_context(build_copilot_agents_context(claude_dir, preferences_text))
    except Exception as e:
        # Fail gracefully - Copilot will work without preferences
        print(f"Warning: Could not prepare Copilot environment: {e}")

    # Validate and repair config.json before launching nested agents.
    # Catches missing plugin metadata fields that cause Copilot CLI to crash.
    # See issue #3671.
    validate_and_repair_copilot_config(copilot_home)

    # Build command with filesystem access to user directories
    # Model override via COPILOT_MODEL env var. Note: Copilot CLI uses different
    # model IDs than Claude Code — "opus[1m]" is Claude-specific and not recognized
    # by Copilot. Only pass --model if explicitly set by the user.
    cmd = [
        "copilot",
        "--allow-all-tools",
    ]
    if not args:
        cmd.extend(
            [
                "--autopilot",
                "--yolo",
                "--max-autopilot-continues",
                "100",
            ]
        )
    copilot_model = os.getenv("COPILOT_MODEL", "")
    if copilot_model:
        cmd.extend(["--model", copilot_model])

    # Add all available directories (home, temp, cwd)
    for directory in get_copilot_directories():
        cmd.extend(["--add-dir", directory])

    # Disable GitHub MCP server to save context tokens
    cmd.extend(["--disable-mcp-server", "github-mcp-server"])

    # If the user passes Copilot CLI args after `--`, treat that as a full override
    # of the default autopilot/yolo launch behavior.
    if args:
        cmd.extend(args)

    # Build explicit env with agent identity and home directory for Rust CLI parity
    env = os.environ.copy()
    env["AMPLIHACK_AGENT_BINARY"] = "copilot"
    env.setdefault("AMPLIHACK_HOME", os.path.expanduser("~/.amplihack"))

    # Launch using subprocess.run() for proper terminal handling
    # Note: os.execvp() doesn't work properly on Windows - it corrupts stdin/terminal state
    result = subprocess.run(cmd, check=False, env=env)
    return result.returncode
