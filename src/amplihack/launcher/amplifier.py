"""Amplifier CLI launcher - wrapper around Microsoft Amplifier command.

Launches Amplifier with the amplihack bundle enabled for enhanced development workflows.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_uv_tool_bin_dir() -> Path | None:
    """Get the uv tool bin directory."""
    # Try common locations
    candidates = [
        Path.home() / ".local" / "bin",  # Linux/macOS default
        Path.home() / ".cargo" / "bin",  # Alternative location
    ]

    # Also check UV_TOOL_BIN_DIR environment variable
    if env_dir := os.environ.get("UV_TOOL_BIN_DIR"):
        candidates.insert(0, Path(env_dir))

    for candidate in candidates:
        if candidate.exists() and (candidate / "amplifier").exists():
            return candidate

    # Return first candidate even if amplifier not there yet (for post-install)
    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def ensure_uv_bin_in_path() -> None:
    """Ensure uv tool bin directory is in PATH for current process."""
    bin_dir = get_uv_tool_bin_dir()
    if bin_dir and str(bin_dir) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{bin_dir}:{os.environ.get('PATH', '')}"


def check_amplifier() -> bool:
    """Check if Amplifier CLI is installed."""
    # Ensure uv bin dir is in PATH
    ensure_uv_bin_in_path()

    try:
        result = subprocess.run(
            ["amplifier", "--version"], capture_output=True, timeout=5, check=False
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_amplifier() -> bool:
    """Install Amplifier CLI via uv tool install.

    Returns:
        True if installation succeeded, False otherwise
    """
    AMPLIFIER_PACKAGE = "git+https://github.com/microsoft/amplifier"

    print(f"Installing Amplifier from {AMPLIFIER_PACKAGE}...")
    print("This will install Amplifier as a uv tool.")

    # Skip prompt in CI/non-interactive environments
    if sys.stdin.isatty():
        print("Continue? [y/N] ", end="", flush=True)
        try:
            response = input().strip().lower()
            if response not in ["y", "yes"]:
                print("Installation cancelled")
                return False
        except (EOFError, KeyboardInterrupt):
            print("\nInstallation cancelled")
            return False
    else:
        print("(non-interactive mode, proceeding)")

    try:
        result = subprocess.run(
            ["uv", "tool", "install", AMPLIFIER_PACKAGE],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("\u2713 Amplifier CLI installed")
            return True
        # Check if already installed
        if "already installed" in result.stderr.lower():
            print("\u2713 Amplifier CLI already installed")
            return True
        print(f"\u2717 Installation failed: {result.stderr[:200]}")
        return False
    except FileNotFoundError:
        print("Error: uv not found. Install uv first: https://docs.astral.sh/uv/")
        return False
    except Exception as e:
        print(f"Error during installation: {e}")
        return False


def sync_agents_md(project_root: Path) -> bool:
    """Sync AGENTS.md from CLAUDE.md for Amplifier compatibility.

    CLAUDE.md is the single source of truth. This function creates AGENTS.md
    as a symlink (Unix) or copy (Windows) so Amplifier can read the same instructions.

    Args:
        project_root: Root directory containing CLAUDE.md

    Returns:
        True if sync succeeded or wasn't needed, False on error
    """
    claude_md = project_root / "CLAUDE.md"
    agents_md = project_root / "AGENTS.md"

    # Nothing to sync if CLAUDE.md doesn't exist
    if not claude_md.exists():
        return True

    # Handle symlinks first (including broken symlinks)
    # Note: is_symlink() returns True even for broken symlinks, but exists() returns False
    if agents_md.is_symlink():
        if agents_md.exists() and agents_md.resolve() == claude_md.resolve():
            return True
        # Wrong target or broken symlink - remove and recreate
        agents_md.unlink()

    # Handle regular files
    if agents_md.is_file():
        if agents_md.read_text(encoding="utf-8") == claude_md.read_text(encoding="utf-8"):
            return True
        # Outdated - remove and recreate
        agents_md.unlink()

    # Create AGENTS.md
    try:
        if sys.platform == "win32":
            # Windows: copy the file (symlinks require admin privileges)
            shutil.copy2(claude_md, agents_md)
        else:
            # Unix: create symlink
            agents_md.symlink_to(claude_md.name)
        return True
    except OSError as e:
        print(f"Warning: Could not sync AGENTS.md from CLAUDE.md: {e}")
        return False


def get_bundle_path() -> Path | None:
    """Get the path to the amplihack bundle.

    Searches in order:
    1. ./amplifier-bundle/bundle.md (relative to cwd - development mode)
    2. Inside the installed amplihack package (uvx/pip installed mode)
    3. Bounded upward search from package location (editable install)

    Returns:
        Path to bundle directory or None if not found
    """
    # Check relative to current directory first (development mode)
    cwd_bundle = Path.cwd() / "amplifier-bundle" / "bundle.md"
    if cwd_bundle.exists():
        return cwd_bundle.parent

    # Check inside the installed package (uvx installed mode)
    # The bundle is copied into src/amplihack/amplifier-bundle/ during wheel build
    pkg_dir = Path(__file__).resolve().parent.parent  # Go up from launcher/ to amplihack/
    pkg_bundle = pkg_dir / "amplifier-bundle" / "bundle.md"
    if pkg_bundle.exists():
        return pkg_bundle.parent

    # Bounded upward search from package location (editable install)
    # Search up to 5 levels to find amplifier-bundle directory
    search_dir = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = search_dir / "amplifier-bundle" / "bundle.md"
        if candidate.exists():
            return candidate.parent
        # Validate we're still in a sensible location
        if not (search_dir / "pyproject.toml").exists() and search_dir == search_dir.parent:
            break  # Hit filesystem root
        search_dir = search_dir.parent

    return None


def ensure_bundle_registered(bundle_path: Path) -> bool:
    """Ensure the amplihack bundle is registered with Amplifier.

    Args:
        bundle_path: Path to the bundle directory

    Returns:
        True if bundle is registered (or was successfully registered), False otherwise
    """
    # Check if already registered by looking for 'amplihack' in bundle list
    try:
        result = subprocess.run(
            ["amplifier", "bundle", "list"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0 and "amplihack" in result.stdout:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

    # Not registered, add it
    print("Registering amplihack bundle with Amplifier...")
    try:
        result = subprocess.run(
            ["amplifier", "bundle", "add", str(bundle_path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0:
            print("\u2713 Bundle registered")
            return True
        print(f"Warning: Failed to register bundle: {result.stderr[:200]}")
        return False
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"Warning: Failed to register bundle: {e}")
        return False


def upgrade_amplifier() -> bool:
    """Upgrade Amplifier CLI to the latest version using amplifier's built-in update.

    Returns:
        True if upgrade succeeded (or was not needed), False otherwise
    """
    print("Checking for Amplifier updates...")
    try:
        result = subprocess.run(
            ["amplifier", "update", "-y"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            # Check if actually upgraded or already latest
            if (
                "already up-to-date" in result.stdout.lower()
                or "already at latest" in result.stdout.lower()
                or "no updates" in result.stdout.lower()
            ):
                print("✓ Amplifier is up-to-date")
            else:
                print("✓ Amplifier upgraded to latest version")
            return True
        print(f"⚠ Upgrade check failed: {result.stderr[:200]}")
        return False
    except FileNotFoundError:
        print("Warning: amplifier update command not found, skipping upgrade check")
        return False
    except subprocess.TimeoutExpired:
        print("Warning: upgrade check timed out, continuing with current version")
        return False
    except Exception as e:
        print(f"Warning: upgrade check error: {e}")
        return False


def launch_amplifier(args: list[str] | None = None) -> int:
    """Launch Amplifier CLI with the amplihack bundle.

    All amplifier args (--model, --provider, --resume, -p, etc.) should be passed
    via the args parameter, which comes from everything after the "--" separator.

    Args:
        args: Arguments to pass to amplifier CLI (everything after --)

    Returns:
        Exit code
    """
    # Ensure amplifier is installed
    if not check_amplifier():
        if not install_amplifier() or not check_amplifier():
            print("Failed to install Amplifier CLI")
            return 1
    else:
        # Already installed - check for and install updates automatically
        upgrade_amplifier()

    # Find the bundle path and ensure it's registered
    bundle_path = get_bundle_path()
    if not bundle_path:
        print("Warning: amplihack bundle not found. Running Amplifier without bundle.")
        print("  Expected location: ./amplifier-bundle/bundle.md")
        bundle_args: list[str] = []
    else:
        # Sync AGENTS.md from CLAUDE.md (CLAUDE.md is source of truth)
        # This ensures Amplifier sees the same instructions as Claude Code
        project_root = bundle_path.parent
        sync_agents_md(project_root)

        # Ensure bundle is registered with Amplifier (uses bundle name, not path)
        if ensure_bundle_registered(bundle_path):
            print(f"Using amplihack bundle: {bundle_path}")
            bundle_args = ["--bundle", "amplihack"]
        else:
            print("Warning: Could not register bundle. Running without it.")
            bundle_args = []

    # Parse args to determine mode (resume, run, etc.)
    args = args or []

    # Check for resume mode: amplihack amplifier -- resume <session_id>
    if args and args[0] == "resume":
        # Resume mode: amplifier resume <session_id> [other args]
        cmd = ["amplifier"] + args
    elif args and args[0] == "run":
        # User explicitly passed 'run', insert bundle args after 'run'
        cmd = ["amplifier", "run"] + bundle_args + args[1:]
    else:
        # Default to interactive chat mode with bundle
        # Add --mode chat to ensure interactive mode (Amplifier defaults to single)
        cmd = ["amplifier", "run", "--mode", "chat"] + bundle_args + args

    # Debug output to stderr
    if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
        print(f"Launching: {' '.join(cmd)}", file=sys.stderr)

    # Launch with error handling
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except FileNotFoundError:
        print("Error: amplifier command not found. Try reinstalling.")
        return 1
    except OSError as e:
        print(f"Error launching amplifier: {e}")
        return 1


def launch_amplifier_auto(prompt: str) -> int:
    """Launch Amplifier with a prompt (Amplifier manages its own execution loop).

    Args:
        prompt: The task prompt

    Returns:
        Exit code
    """
    print("Starting Amplifier with task...")
    return launch_amplifier(args=["-p", prompt])
