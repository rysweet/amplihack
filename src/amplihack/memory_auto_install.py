"""Auto-installer for amplihack-memory-lib during startup."""

import sys


def _is_arm64_interpreter() -> bool:
    """Check if the current Python interpreter is ARM64 (not the CPU)."""
    # sys.version contains the build arch: "64 bit (ARM64)" vs "64 bit (AMD64)"
    # platform.machine() returns CPU arch which is always ARM64 on ARM hardware,
    # even when running x86_64 Python under emulation.
    return "ARM64" in sys.version or "aarch64" in sys.version


def _find_x86_python() -> list[str] | None:
    """On Windows ARM64, find an x86_64 Python that can load kuzu's win_amd64 wheel.

    Returns:
        A command list like ["C:\\...\\py.exe", "-3.13"] or None if not found.
    """
    if sys.platform != "win32":
        return None
    import re
    import shutil
    import subprocess

    if not _is_arm64_interpreter():
        return None  # Already x86_64 — no need for fallback

    # Try the py launcher which lists all installed Pythons
    py = shutil.which("py")
    if not py:
        return None

    try:
        result = subprocess.run(
            [py, "--list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        # Look for a non-ARM64 Python (e.g., " -V:3.13  Python 3.13 (64-bit)")
        # Version tags look like "-V:3.13" or "-3.13-64"
        ver_pattern = re.compile(r"-(?:V:)?(\d+\.\d+)")
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped or "arm64" in stripped.lower():
                continue
            match = ver_pattern.search(stripped)
            if not match:
                continue
            ver_tag = f"-{match.group(1)}"
            # Verify this Python is actually a working 64-bit interpreter
            check = subprocess.run(
                [py, ver_tag, "-c", "import struct; print(struct.calcsize('P')*8)"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if check.returncode == 0 and "64" in check.stdout.strip():
                return [py, ver_tag]
    except Exception as exc:
        print(f"WARNING: Failed to enumerate Python installations: {exc}", file=sys.stderr)
    return None


def ensure_memory_lib_installed() -> bool:
    """Ensure amplihack-memory-lib is installed, auto-install if missing.

    Returns:
        bool: True if library is available (was installed or got installed)
    """
    try:
        import amplihack_memory  # noqa: F401

        return True  # Already installed
    except ImportError:
        pass

    # On Windows ARM64 interpreter, kuzu has no win_arm64 wheel — need x86_64 Python
    if sys.platform == "win32" and _is_arm64_interpreter():
        x86_py = _find_x86_python()
        if x86_py:
            return _install_via_x86_python(x86_py)
        print(
            "⚠️  amplihack-memory-lib requires kuzu, which has no ARM64 Windows wheel.\n"
            "   Install Python 3.13 x86_64: winget install Python.Python.3.13 --architecture x64\n"
            "   Then run amplihack with: py -3.13 -m amplihack",
            file=sys.stderr,
        )
        return False

    print("WARNING: amplihack_memory not available, attempting auto-install", file=sys.stderr)
    return _do_install([sys.executable, "-m", "pip"])


def _install_via_x86_python(py_cmd: list[str]) -> bool:
    """Install amplihack-memory-lib using an x86_64 Python (for ARM64 Windows).

    Args:
        py_cmd: Command list to invoke x86_64 Python, e.g. ["py", "-3.13"].

    Returns:
        False always — the library is installed into the x86_64 Python's
        site-packages, not the current (ARM64) interpreter, so it cannot
        be imported from this process.
    """
    import subprocess

    print(f"📦 Installing amplihack-memory-lib via x86_64 Python ({' '.join(py_cmd)})...")

    try:
        result = subprocess.run(
            [
                *py_cmd,
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
            print("✅ amplihack-memory-lib installed (x86_64 Python)")
            # Also install into the current (ARM64) Python's site-packages
            # so 'import amplihack_memory' works from this interpreter.
            # amplihack-memory-lib is pure Python; only kuzu is native.
            # We can't load kuzu from ARM64 Python regardless, so just
            # report partial success.
            print(
                "⚠️  Note: kuzu (native C++) can only run under x86_64 Python.\n"
                "   Memory features will work when running: py -3.13 -m amplihack",
                file=sys.stderr,
            )
            return False  # Not usable from this interpreter
        print(f"⚠️  Install failed: {result.stderr[:300]}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"⚠️  Install error: {e}", file=sys.stderr)
        return False


def _do_install(pip_cmd: list[str]) -> bool:
    """Run pip install for amplihack-memory-lib.

    Args:
        pip_cmd: Base pip command list, e.g. [sys.executable, "-m", "pip"].

    Returns:
        True if installation succeeded and library is importable.
    """
    import subprocess

    print("📦 Installing amplihack-memory-lib (required for learning agents)...")

    try:
        result = subprocess.run(
            [
                *pip_cmd,
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
        print(f"⚠️ Auto-install failed: {result.stderr[:300]}")
        print(
            "   Install manually: pip install git+https://github.com/rysweet/amplihack-memory-lib.git@v0.1.0"
        )
        return False

    except Exception as e:
        print(f"⚠️ Could not auto-install: {e}")
        return False
