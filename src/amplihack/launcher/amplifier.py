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
    2. Relative to this package's location (for installed amplihack)

    Returns:
        Path to bundle.md or None if not found
    """
    # Check relative to current directory first
    cwd_bundle = Path.cwd() / "amplifier-bundle" / "bundle.md"
    if cwd_bundle.exists():
        return cwd_bundle.parent

    # Check relative to package location (for pip/uv installed amplihack)
    # The bundle is at the repo root, which is 4 levels up from this file
    # src/amplihack/launcher/amplifier.py -> repo_root/amplifier-bundle
    package_dir = Path(__file__).parent.parent.parent.parent
    package_bundle = package_dir / "amplifier-bundle" / "bundle.md"
    if package_bundle.exists():
        return package_bundle.parent

    return None


def launch_amplifier(
    args: list[str] | None = None,
    interactive: bool = True,
    prompt: str | None = None,
    resume: str | None = None,
    print_only: bool = False,
) -> int:
    """Launch Amplifier CLI with the amplihack bundle.

    Args:
        args: Additional arguments to pass to amplifier
        interactive: If True, launch in interactive mode (default)
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
        bundle_args = []
    else:
        print(f"Using amplihack bundle: {bundle_path}")
        bundle_args = ["--bundle", str(bundle_path)]

    # Build command
    cmd = ["amplifier"]

    # Add subcommand based on mode
    if resume:
        cmd.extend(["resume", resume])
    elif print_only and prompt:
        cmd.extend(["print", prompt])
    elif prompt:
        cmd.extend(["run"] + bundle_args + [prompt])
    else:
        # Interactive mode
        cmd.extend(["run"] + bundle_args)

    # Add any additional args
    if args:
        # Handle -p flag conversion for compatibility with other tools
        if "-p" in args:
            idx = args.index("-p")
            if idx + 1 < len(args):
                prompt_arg = args[idx + 1]
                # Remove -p and prompt from args, add prompt to cmd
                remaining = args[:idx] + args[idx + 2 :]
                if not prompt:  # Don't override if already set
                    cmd.extend(bundle_args if not bundle_args else [])
                    # Insert prompt after 'run' if using run command
                    if "run" in cmd and prompt_arg:
                        run_idx = cmd.index("run")
                        # Add bundle args after run if not already added
                        if bundle_args and bundle_args[0] not in cmd:
                            cmd = cmd[: run_idx + 1] + bundle_args + [prompt_arg]
                        else:
                            cmd.insert(run_idx + 1 + len(bundle_args), prompt_arg)
                args = remaining
        cmd.extend(args)

    # Launch
    if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
        print(f"Launching: {' '.join(cmd)}")

    result = subprocess.run(cmd, check=False)
    return result.returncode


def launch_amplifier_auto(prompt: str, max_turns: int = 10) -> int:
    """Launch Amplifier in autonomous mode.

    Note: Amplifier doesn't have a built-in auto mode like amplihack's AutoMode.
    This launches Amplifier with the prompt and lets it run until completion.

    Args:
        prompt: The task prompt
        max_turns: Maximum turns (informational, Amplifier manages its own loop)

    Returns:
        Exit code
    """
    print("Starting Amplifier with task (max context managed by Amplifier)...")
    return launch_amplifier(prompt=prompt, interactive=False)
