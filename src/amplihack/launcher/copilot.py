"""Copilot CLI launcher with full extensibility parity staging."""

import json
import os
import platform
import shlex
import shutil
import signal
import subprocess
import tempfile
import threading
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


def check_for_update() -> str | None:
    """Check if a newer version of Copilot CLI is available.

    Returns:
        New version string if update available, None otherwise
    """
    try:
        # Get current version
        current_result = subprocess.run(
            ["copilot", "--version"],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
        if current_result.returncode != 0:
            return None

        # Parse version from output: "@github/copilot/1.4.0 linux-x64 node-v20.10.0"
        current_output = current_result.stdout.strip()
        if "/" not in current_output:
            return None

        parts = current_output.split("/")
        if len(parts) < 3:
            return None

        # Extract version from: "1.4.0 linux-x64..." -> "1.4.0"
        current_version = parts[2].split()[0]

        # Get latest version from npm
        latest_result = subprocess.run(
            ["npm", "view", "@github/copilot", "version"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
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


def execute_update(install_method: str) -> bool:
    """Execute Copilot CLI update based on installation method.

    Args:
        install_method: Installation method ('npm' or 'uvx')

    Returns:
        True if update succeeded, False otherwise
    """
    print(f"\n📦 Updating Copilot CLI via {install_method}...")

    try:
        # Get current version before update
        try:
            pre_result = subprocess.run(
                ["copilot", "--version"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            pre_version = None
            if pre_result.returncode == 0:
                output = pre_result.stdout.strip()
                if "/" in output:
                    parts = output.split("/")
                    if len(parts) >= 3:
                        pre_version = parts[2].split()[0]
        except (subprocess.TimeoutExpired, FileNotFoundError, IndexError):
            pre_version = None

        # Execute update command
        if install_method == "uvx":
            # uvx update: run copilot with latest version
            result = subprocess.run(
                ["uvx", "--from", "@github/copilot@latest", "copilot", "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        else:
            # npm update
            result = subprocess.run(
                ["npm", "install", "-g", "@github/copilot"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

        if result.returncode != 0:
            print(f"✗ Update failed: {result.stderr.strip()}")
            return False

        # Verify update by checking version
        try:
            post_result = subprocess.run(
                ["copilot", "--version"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if post_result.returncode == 0:
                output = post_result.stdout.strip()
                if "/" in output:
                    parts = output.split("/")
                    if len(parts) >= 3:
                        post_version = parts[2].split()[0]
                        if pre_version and post_version != pre_version:
                            print(f"✓ Updated from {pre_version} to {post_version}")
                            return True
                        if post_version:
                            print(f"✓ Update complete (version: {post_version})")
                            return True
        except (subprocess.TimeoutExpired, FileNotFoundError, IndexError):
            pass

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


def check_copilot() -> bool:
    """Check if Copilot CLI is installed.

    Returns:
        bool: True if copilot is available, False otherwise

    Note:
        Handles FileNotFoundError (not installed), PermissionError (WSL),
        and TimeoutExpired (hanging command) gracefully.
    """
    try:
        subprocess.run(["copilot", "--version"], capture_output=True, timeout=5, check=False)
        return True
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        return False


def install_copilot() -> bool:
    """Install GitHub Copilot CLI via npm to user-local directory."""
    print("Installing GitHub Copilot CLI...")

    npm_prefix = Path.home() / ".npm-global"
    npm_prefix.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            ["npm", "install", "-g", "--prefix", str(npm_prefix), "@github/copilot"], check=False
        )
        if result.returncode == 0:
            print("✓ Copilot CLI installed")

            # Add to PATH for current process
            bin_path = npm_prefix / "bin"
            path_env = os.environ.get("PATH", "")
            if str(bin_path) not in path_env:
                os.environ["PATH"] = f"{bin_path}:{path_env}"
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
    """Stage amplihack agents to ~/.copilot/agents/ for Copilot CLI discovery.

    Copilot CLI searches ~/.copilot/agents/ (user-level) before .github/agents/
    (repo-level). Staging to user-level ensures agents are discoverable in ANY
    repo, not just repos with .github/agents/. (Fix for issue #2241)

    Args:
        source_agents: Path to amplihack agent source directory
            (e.g. package_dir/.claude/agents/amplihack/)
        copilot_home: Path to copilot home directory (e.g. ~/.copilot/)

    Returns:
        Number of agents staged
    """
    if not source_agents.exists():
        return 0

    agents_dest = copilot_home / "agents"
    agents_dest.mkdir(parents=True, exist_ok=True)

    # Clean stale agents first (removed/renamed agents)
    for old_file in agents_dest.glob("*.md"):
        old_file.unlink()

    # Flatten structure: core/architect.md → architect.md
    # NOTE: Assumes no basename collisions across subdirectories (core/, specialized/, workflows/)
    copied = 0
    for source_file in source_agents.rglob("*.md"):
        dest_file = agents_dest / source_file.name
        shutil.copy2(source_file, dest_file)
        copied += 1

    return copied


def stage_directory(source_dir: Path, copilot_home: Path, dest_name: str) -> int:
    """Stage a directory of .md files to ~/.copilot/<dest_name>/.

    Flattens any subdirectory structure. Cleans stale files before staging.

    Args:
        source_dir: Source directory containing .md files (may have subdirs)
        copilot_home: Path to copilot home directory (e.g. ~/.copilot/)
        dest_name: Subdirectory name under copilot_home (e.g. "workflow")

    Returns:
        Number of files staged
    """
    if not source_dir.exists():
        return 0

    dest = copilot_home / dest_name
    dest.mkdir(parents=True, exist_ok=True)

    # Clean stale files
    for old_file in dest.glob("*.md"):
        old_file.unlink()

    copied = 0
    for source_file in source_dir.rglob("*.md"):
        shutil.copy2(source_file, dest / source_file.name)
        copied += 1

    return copied


def generate_copilot_instructions(copilot_home: Path) -> None:
    """Generate ~/.copilot/copilot-instructions.md for amplihack integration.

    Copilot CLI auto-reads this file at session start. It tells copilot where
    to find amplihack's extensibility mechanisms (workflows, context, commands).

    Args:
        copilot_home: Path to copilot home directory (e.g. ~/.copilot/)
    """
    instructions = copilot_home / "copilot-instructions.md"
    copilot_home.mkdir(parents=True, exist_ok=True)

    content = f"""\
# Amplihack Framework Integration

You have access to the amplihack agentic coding framework. Use these resources:

## Workflows
Read workflow files from `{copilot_home}/workflow/` to follow structured processes:
- `DEFAULT_WORKFLOW.md` — Standard development workflow (23 steps)
- `INVESTIGATION_WORKFLOW.md` — Research and exploration (6 phases)
- `CASCADE_WORKFLOW.md`, `DEBATE_WORKFLOW.md`, `N_VERSION_WORKFLOW.md` — Fault tolerance patterns

For any non-trivial development task, read DEFAULT_WORKFLOW.md and follow its steps.

## Context
Read context files from `{copilot_home}/context/` for project philosophy and patterns:
- `PHILOSOPHY.md` — Core principles (ruthless simplicity, zero-BS, modular design)
- `PATTERNS.md` — Reusable solution patterns
- `TRUST.md` — Anti-sycophancy and direct communication guidelines
- `USER_PREFERENCES.md` — User-specific preferences (MANDATORY)

## Commands
Read command definitions from `{copilot_home}/commands/` for available capabilities:
- `ultrathink.md` — Deep analysis orchestration for complex tasks
- `analyze.md` — Comprehensive code review
- `improve.md` — Self-improvement and learning capture

## Agents
Custom agents are available at `{copilot_home}/agents/`. Use them via the task tool.

## Skills
Skills are available at `{copilot_home}/skills/`. They auto-activate based on context.
"""
    instructions.write_text(content)


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
    # Check for updates (non-blocking)
    try:
        new_version = check_for_update()
        if new_version:
            install_method = detect_install_method()
            if prompt_user_to_update(new_version, install_method):
                # User wants to update
                if execute_update(install_method):
                    print("✓ Copilot CLI updated successfully")
                else:
                    print("⚠ Update failed - continuing with current version")
    except Exception:
        # Silently ignore update check failures
        pass

    # Ensure copilot is installed
    if not check_copilot():
        if not install_copilot() or not check_copilot():
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

        # Commands (flattened from amplihack/ subdir)
        n = stage_directory(claude_dir / "commands", copilot_home, "commands")
        if n > 0:
            print(f"✓ Staged {n} commands to ~/.copilot/commands/")

        # Generate copilot-instructions.md so copilot knows where everything is
        generate_copilot_instructions(copilot_home)

        # Inject preferences into AGENTS.md for copilot context
        prefs_file = user_dir / ".claude/context/USER_PREFERENCES.md"
        if not prefs_file.exists():
            prefs_file = claude_dir / "context/USER_PREFERENCES.md"
        if prefs_file.exists():
            strategy.inject_context(prefs_file.read_text())
    except Exception as e:
        # Fail gracefully - Copilot will work without preferences
        print(f"Warning: Could not prepare Copilot environment: {e}")

    # Build command with filesystem access to user directories
    # Model can be overridden via COPILOT_MODEL env var (default: Opus 4.5)
    model = os.getenv("COPILOT_MODEL", "claude-opus-4.5")
    cmd = [
        "copilot",
        "--allow-all-tools",
        "--model",
        model,
    ]

    # Add all available directories (home, temp, cwd)
    for directory in get_copilot_directories():
        cmd.extend(["--add-dir", directory])

    # Disable GitHub MCP server to save context tokens
    cmd.extend(["--disable-mcp-server", "github-mcp-server"])

    if args:
        cmd.extend(args)

    # Launch using subprocess.run() for proper terminal handling
    # Note: os.execvp() doesn't work properly on Windows - it corrupts stdin/terminal state
    result = subprocess.run(cmd, check=False)
    return result.returncode
