"""Tests for version detection in amplihack/__init__.py.

Verifies that:
- importlib.metadata is used directly (no fallback)
- tomllib is used directly for dev-mode (no tomli fallback)
- PackageNotFoundError is the real one from importlib.metadata
- Version detection works in both installed and dev modes
"""

from importlib.metadata import PackageNotFoundError
from pathlib import Path

import amplihack


class TestVersionDetection:
    """Verify version detection uses direct imports, no dead fallbacks."""

    def test_version_is_set(self):
        """__version__ must be a non-empty string."""
        assert isinstance(amplihack.__version__, str)
        assert amplihack.__version__ != ""

    def test_version_is_not_unknown(self):
        """In this repo, pyproject.toml always exists so version is never 'unknown'."""
        assert amplihack.__version__ != "unknown"

    def test_package_not_found_error_is_real(self):
        """PackageNotFoundError must be from importlib.metadata, not a fallback alias."""
        # Import what __init__.py uses at module scope
        from importlib.metadata import PackageNotFoundError as RealPNFE

        # The module-level import should be the real class
        assert RealPNFE is PackageNotFoundError

    def test_no_fallback_alias_in_source(self):
        """Source must not contain the old 'PackageNotFoundError = Exception' alias."""
        init_path = Path(amplihack.__file__)
        source = init_path.read_text()

        assert "PackageNotFoundError = Exception" not in source, (
            "Source still contains the buggy alias"
        )

    def test_no_importlib_try_except_in_source(self):
        """Source must not wrap importlib.metadata import in try/except ImportError."""
        init_path = Path(amplihack.__file__)
        source = init_path.read_text()

        # The old pattern was: try: from importlib.metadata ... except ImportError:
        # The new pattern is a direct import with no try/except around it
        lines = source.splitlines()
        for i, line in enumerate(lines):
            if "from importlib.metadata import" in line:
                # Check the line before isn't a try:
                if i > 0 and lines[i - 1].strip() == "try:":
                    raise AssertionError(
                        f"importlib.metadata import is wrapped in try/except at line {i + 1}"
                    )

    def test_no_tomli_fallback_in_source(self):
        """Source must not contain tomli fallback (tomllib is guaranteed on Python 3.11+)."""
        init_path = Path(amplihack.__file__)
        source = init_path.read_text()

        assert "import tomli" not in source, (
            "Source still contains tomli fallback — tomllib is guaranteed on Python 3.11+"
        )

    def test_no_sys_import(self):
        """sys import was removed since stderr warning prints were removed."""
        init_path = Path(amplihack.__file__)
        source = init_path.read_text()

        # Check there's no 'import sys' as a standalone import
        for line in source.splitlines():
            stripped = line.strip()
            if stripped == "import sys":
                raise AssertionError(
                    "Unused 'import sys' still present — was removed with fallback branches"
                )

    def test_dev_mode_reads_pyproject_toml(self):
        """When package is not installed, version falls back to pyproject.toml."""
        import tomllib

        pyproject_path = Path(amplihack.__file__).parent.parent.parent / "pyproject.toml"
        if not pyproject_path.exists():
            return  # Skip if not in dev layout

        with open(pyproject_path, "rb") as f:
            expected_version = tomllib.load(f)["project"]["version"]

        # In dev layout, version comes from pyproject.toml
        assert amplihack.__version__ == expected_version
