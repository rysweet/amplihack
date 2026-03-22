"""Auto-installer for github-copilot-sdk during startup."""


def ensure_copilot_sdk_installed() -> bool:
    """Ensure github-copilot-sdk is installed, auto-install if missing.

    The Copilot SDK is required for:
    - CopilotBackend (fleet reasoning without Anthropic API key)
    - Power steering (SessionCopilot)
    - Fleet copilot mode (/amplihack:lock)

    Returns:
        bool: True if SDK is available (was installed or got installed)
    """
    try:
        from copilot import CopilotClient  # noqa: F401

        return True  # Already installed
    except ImportError:
        pass

    # Not installed - auto-install
    import subprocess
    import sys

    print("Installing github-copilot-sdk (required for copilot features)...")

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "uv",
                "pip",
                "install",
                "github-copilot-sdk",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            print("github-copilot-sdk installed successfully")
            return True

        # Fallback to pip if uv not available
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "github-copilot-sdk",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            print("github-copilot-sdk installed successfully")
            return True

        print(f"Auto-install failed: {result.stderr[:200]}")
        print("   Install manually: uv pip install github-copilot-sdk")
        return False

    except Exception as e:
        print(f"Could not auto-install github-copilot-sdk: {e}")
        return False
