"""Auto-installer for amplihack-memory-lib during startup."""


def ensure_memory_lib_installed() -> bool:
    """Ensure amplihack-memory-lib is installed, auto-install if missing.

    Returns:
        bool: True if library is available (was installed or got installed)
    """
    try:
        import amplihack_memory  # noqa: F401

        return True  # Already installed
    except ImportError:
        import sys

        print("WARNING: amplihack_memory not available, attempting auto-install", file=sys.stderr)

    # Not installed - auto-install
    import subprocess
    import sys

    print("📦 Installing amplihack-memory-lib (required for learning agents)...")

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "git+https://github.com/rysweet/amplihack-memory-lib.git@v0.1.0",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            print("✅ amplihack-memory-lib installed successfully")
            return True
        print(f"⚠️ Auto-install failed: {result.stderr}")
        print(
            "   Install manually: pip install git+https://github.com/rysweet/amplihack-memory-lib.git@v0.1.0"
        )
        return False

    except Exception as e:
        print(f"⚠️ Could not auto-install: {e}")
        return False
