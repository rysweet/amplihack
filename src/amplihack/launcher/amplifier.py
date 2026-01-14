"""Amplifier CLI launcher - wrapper around Microsoft Amplifier command.

Launches Amplifier with the amplihack bundle enabled for enhanced development workflows.
"""

import os
import subprocess
import sys
from pathlib import Path


def check_amplifier() -> bool:
    """Check if Amplifier CLI is installed."""
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


def get_bundle_path() -> Path | None:
    """Get the path to the amplihack bundle.

    Searches in order:
    1. ./amplifier-bundle/bundle.md (relative to cwd)
    2. Bounded upward search from package location (for installed amplihack)

    Returns:
        Path to bundle directory or None if not found
    """
    # Check relative to current directory first (development mode)
    cwd_bundle = Path.cwd() / "amplifier-bundle" / "bundle.md"
    if cwd_bundle.exists():
        return cwd_bundle.parent

    # Bounded upward search from package location (installed mode)
    # Search up to 5 levels to find amplifier-bundle directory
    pkg_dir = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = pkg_dir / "amplifier-bundle" / "bundle.md"
        if candidate.exists():
            return candidate.parent
        # Validate we're still in a sensible location
        if not (pkg_dir / "pyproject.toml").exists() and pkg_dir == pkg_dir.parent:
            break  # Hit filesystem root
        pkg_dir = pkg_dir.parent

    return None


def launch_amplifier(
    args: list[str] | None = None,
    prompt: str | None = None,
    resume: str | None = None,
    print_only: bool = False,
) -> int:
    """Launch Amplifier CLI with the amplihack bundle.

    Args:
        args: Additional arguments to pass to amplifier (--model, --provider, etc.)
        prompt: Initial prompt for non-interactive mode
        resume: Session ID to resume
        print_only: If True, use --print mode (single response, no tools)

    Returns:
        Exit code
    """
    # Ensure amplifier is installed
    if not check_amplifier():
        if not install_amplifier() or not check_amplifier():
            print("Failed to install Amplifier CLI")
            return 1

    # Find the bundle path
    bundle_path = get_bundle_path()
    if not bundle_path:
        print("Warning: amplihack bundle not found. Running Amplifier without bundle.")
        print("  Expected location: ./amplifier-bundle/bundle.md")
        bundle_args: list[str] = []
    else:
        print(f"Using amplihack bundle: {bundle_path}")
        bundle_args = ["--bundle", str(bundle_path)]

    # Build command - simple and direct
    cmd = ["amplifier"]

    if resume:
        cmd.extend(["resume", resume])
    elif print_only and prompt:
        cmd.extend(["print", prompt])
    elif prompt:
        cmd.extend(["run"] + bundle_args + [prompt])
    else:
        # Interactive mode
        cmd.extend(["run"] + bundle_args)

    # Pass through any extra args (model, provider, etc.)
    if args:
        cmd.extend(args)

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
    return launch_amplifier(prompt=prompt)
