"""Codex CLI launcher - wrapper around OpenAI Codex command."""

import json
import os
import subprocess
import sys
from pathlib import Path


def check_codex() -> bool:
    """Check if Codex CLI is installed."""
    try:
        subprocess.run(["codex", "--version"], capture_output=True, timeout=5, check=False)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _get_current_codex_version() -> str | None:
    """Get the currently installed Codex CLI version."""
    try:
        result = subprocess.run(
            ["codex", "--version"], capture_output=True, text=True, timeout=10, check=False
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip().split()[0].lstrip("v") if result.stdout.strip() else None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError, IndexError):
        return None


def _compare_versions(current: str, latest: str) -> bool:
    """Return True if latest > current using semantic version comparison."""
    try:
        cur = tuple(int(x) for x in current.lstrip("v").split("."))
        lat = tuple(int(x) for x in latest.lstrip("v").split("."))
        return lat > cur
    except (ValueError, AttributeError):
        return False


def ensure_latest_codex() -> bool:
    """Auto-update Codex CLI to the latest version if an update is available.

    Set AMPLIHACK_SKIP_UPDATE=1 to bypass.

    Returns:
        True if up-to-date or updated successfully, False on failure.
    """
    if os.environ.get("AMPLIHACK_SKIP_UPDATE", "") == "1":
        return True

    if not check_codex():
        return True  # not installed yet — let install_codex() handle it

    try:
        current = _get_current_codex_version()
        if current is None:
            return True

        latest_result = subprocess.run(
            ["npm", "view", "@openai/codex-cli", "version"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if latest_result.returncode != 0:
            return True

        latest = latest_result.stdout.strip()
        if not _compare_versions(current, latest):
            return True  # already up-to-date

        print(f"🔄 Codex CLI update available: {current} → {latest}")
        result = subprocess.run(
            ["npm", "install", "-g", "@openai/codex-cli"],
            capture_output=True, text=True, timeout=120, check=False,
        )
        if result.returncode == 0:
            post = _get_current_codex_version() or latest
            print(f"✓ Codex CLI updated to {post}")
            return True

        print(f"⚠ Codex update failed — continuing with current version: {result.stderr.strip()}")
        return False
    except Exception:
        return False


def install_codex() -> bool:
    """Install OpenAI Codex CLI via npm with security checks."""
    # Version pinning for security
    CODEX_PACKAGE = "@openai/codex-cli"  # Consider pinning to @latest or specific version

    print(f"Installing {CODEX_PACKAGE}...")
    print("⚠ This will install a global npm package.")

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
            ["npm", "install", "-g", CODEX_PACKAGE], check=False, capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✓ Codex CLI installed")
            return True
        print(f"✗ Installation failed: {result.stderr[:200]}")
        return False
    except FileNotFoundError:
        print("Error: npm not found. Install Node.js first.")
        return False
    except Exception as e:
        print(f"Error during installation: {e}")
        return False


def configure_codex() -> bool:
    """Configure Codex CLI with approval_mode: auto.

    Creates or updates ~/.openai/codex/config.json to set approval_mode to auto.

    Returns:
        True if configuration succeeded, False otherwise
    """
    try:
        config_dir = Path.home() / ".openai" / "codex"
        config_file = config_dir / "config.json"

        # Create config directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)

        # Read existing config or create new one
        config = {}
        if config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    config = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON in {config_file}, recreating config")
                config = {}
            except Exception as e:
                print(f"Warning: Failed to read config: {e}")
                config = {}

        # Set approval_mode to auto if not already set
        if config.get("approval_mode") != "auto":
            config["approval_mode"] = "auto"

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            print("✓ Codex configured with approval_mode: auto")
            return True

        print("Codex already configured")
        return True

    except Exception as e:
        print(f"Warning: Failed to configure Codex: {e}")
        return False


def launch_codex(args: list[str] | None = None, interactive: bool = True) -> int:
    """Launch Codex CLI.

    Args:
        args: Arguments to pass to codex
        interactive: If True, exec to replace process for interactive use

    Returns:
        Exit code (only for non-interactive mode)
    """
    # Auto-update to latest version before launching (fixes #3097)
    try:
        ensure_latest_codex()
    except Exception:
        pass  # non-critical — continue with current version

    # Ensure codex is installed
    if not check_codex():
        if not install_codex() or not check_codex():
            print("Failed to install Codex CLI")
            return 1

    # Auto-configure approval mode
    configure_codex()

    # Build command
    cmd = ["codex"]
    if args:
        # Codex uses "exec" command for prompts
        # Convert: codex -p "prompt" → codex exec "prompt"
        if "-p" in args:
            idx = args.index("-p")
            if idx + 1 < len(args):
                prompt = args[idx + 1]
                cmd.extend(["exec", prompt])
                # Add any remaining args after the prompt
                if idx + 2 < len(args):
                    cmd.extend(args[idx + 2 :])
            else:
                # No prompt after -p, just pass args as-is
                cmd.extend(args)
        else:
            # No -p flag, pass args as-is
            cmd.extend(args)

    # Launch using subprocess.run() for proper terminal handling
    # Note: os.execvp() doesn't work properly on Windows - it corrupts stdin/terminal state
    result = subprocess.run(cmd, check=False)
    return result.returncode
