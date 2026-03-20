"""Startup check for amplihack-memory-lib.

amplihack-memory-lib is a mandatory dependency declared in pyproject.toml.
pip/uv installs it automatically. This module verifies it is importable at
CLI startup and fails loudly if the install is broken.

No subprocess calls. No auto-install. The package manager handles installation.
"""

import sys


def ensure_memory_lib_installed() -> bool:
    """Verify amplihack-memory-lib is importable.

    This is a startup prerequisite check, not an installer. The library is
    declared as a mandatory dependency in pyproject.toml — the package manager
    (pip, uv, etc.) installs it when amplihack is installed.

    If the import fails, the installation is broken and we fail loudly with
    actionable repair instructions.

    Returns:
        True if the library is available.

    Raises:
        SystemExit: If the library cannot be imported (broken install).
    """
    try:
        import amplihack_memory  # type: ignore[import-untyped]  # noqa: F401

        return True
    except ImportError:
        print(
            "ERROR: amplihack-memory-lib is not importable.\n"
            "\n"
            "This is a required dependency that should have been installed\n"
            "automatically. Your installation may be broken.\n"
            "\n"
            "Repair with:\n"
            "  pip install --force-reinstall amplihack\n"
            "  # or:\n"
            "  pip install amplihack-memory-lib\n",
            file=sys.stderr,
        )
        # Return False instead of sys.exit so the CLI can still start
        # for commands that don't need memory (e.g. --help, version).
        return False
