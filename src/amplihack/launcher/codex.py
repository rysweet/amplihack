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
