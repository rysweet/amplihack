"""Security tests for amplihack.memory_auto_install.

Covers:
- SEC-02: subprocess command uses sys.executable, never bare "pip"
- SEC-04: pip install uses --require-hashes and a pinned version tag;
          hashes file exists on disk
- SEC-07: _sanitize_error() exists, strips absolute paths, and is used
          by _do_install when printing error messages

All tests in this file are expected to FAIL against the current
implementation because the features they specify are NOT YET implemented.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PKG = "amplihack.memory_auto_install"
_HASHES_FILE = (
    Path(__file__).parent.parent / "src" / "amplihack" / "memory_auto_install_hashes.txt"
)


def _make_completed(returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout="", stderr=stderr
    )


# ============================================================================
# SEC-02: sys.executable — no bare "pip" as the first command element
# ============================================================================


class TestSec02SysExecutable:
    """SEC-02: _do_install must use sys.executable, not the bare string 'pip'."""

    def test_do_install_first_arg_is_sys_executable(self):
        """_do_install([sys.executable, '-m', 'pip']) must pass sys.executable
        as the first element of the subprocess command, not a bare 'pip'."""
        import amplihack.memory_auto_install as mod

        captured_cmd: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            captured_cmd.append(list(cmd))
            return _make_completed(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            mod._do_install([sys.executable, "-m", "pip"])

        assert captured_cmd, "_do_install did not call subprocess.run"
        first_element = captured_cmd[0][0]
        assert first_element == sys.executable, (
            f"Expected sys.executable ({sys.executable!r}) as first element, "
            f"got {first_element!r}"
        )

    def test_do_install_command_does_not_start_with_bare_pip(self):
        """The bare string 'pip' must NOT appear as the first command element."""
        import amplihack.memory_auto_install as mod

        captured_cmd: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            captured_cmd.append(list(cmd))
            return _make_completed(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            mod._do_install([sys.executable, "-m", "pip"])

        assert captured_cmd, "_do_install did not call subprocess.run"
        first_element = captured_cmd[0][0]
        assert first_element != "pip", (
            "subprocess command must not start with the bare string 'pip'; "
            "use sys.executable instead"
        )

    def test_ensure_memory_lib_installed_delegates_sys_executable(self):
        """ensure_memory_lib_installed() must pass sys.executable to _do_install,
        not a hard-coded 'pip' string."""
        import amplihack.memory_auto_install as mod
        import builtins

        captured: list[list[str]] = []

        def fake_do_install(pip_cmd):
            captured.append(list(pip_cmd))
            return True

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "amplihack_memory":
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)

        with (
            patch(_PKG + "._do_install", side_effect=fake_do_install),
            patch(_PKG + "._is_arm64_interpreter", return_value=False),
            patch("builtins.__import__", side_effect=fake_import),
        ):
            mod.ensure_memory_lib_installed()

        if captured:
            assert captured[0][0] == sys.executable, (
                f"ensure_memory_lib_installed must pass sys.executable "
                f"({sys.executable!r}), got {captured[0][0]!r}"
            )


# ============================================================================
# SEC-04: --require-hashes, version pin, hashes file
# ============================================================================


class TestSec04HashVerification:
    """SEC-04: pip install must use --require-hashes and a pinned version tag."""

    def test_do_install_includes_require_hashes_flag(self):
        """--require-hashes must be present in the pip install command."""
        import amplihack.memory_auto_install as mod

        captured_cmd: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            captured_cmd.append(list(cmd))
            return _make_completed(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            mod._do_install([sys.executable, "-m", "pip"])

        assert captured_cmd, "_do_install did not call subprocess.run"
        assert "--require-hashes" in captured_cmd[0], (
            f"'--require-hashes' must appear in the pip install command; "
            f"got: {captured_cmd[0]!r}"
        )

    def test_do_install_install_url_contains_version_pin(self):
        """The install URL/specifier must contain a version tag (e.g. @v0.1.0)."""
        import amplihack.memory_auto_install as mod

        captured_cmd: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            captured_cmd.append(list(cmd))
            return _make_completed(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            mod._do_install([sys.executable, "-m", "pip"])

        assert captured_cmd, "_do_install did not call subprocess.run"
        full_cmd = " ".join(captured_cmd[0])
        assert "@v" in full_cmd, (
            f"Install command must contain a version pin (e.g. '@v0.1.0'); "
            f"got: {full_cmd!r}"
        )

    def test_hashes_file_exists(self):
        """src/amplihack/memory_auto_install_hashes.txt must exist on disk."""
        assert _HASHES_FILE.exists(), (
            f"Hashes file not found at {_HASHES_FILE}. "
            "Create src/amplihack/memory_auto_install_hashes.txt with the "
            "expected SHA-256 digests for the pinned amplihack-memory-lib."
        )

    def test_hashes_file_is_not_empty(self):
        """The hashes file must contain at least one hash entry."""
        if not _HASHES_FILE.exists():
            pytest.skip("Hashes file does not exist (covered by test_hashes_file_exists)")
        content = _HASHES_FILE.read_text(encoding="utf-8").strip()
        assert content, "memory_auto_install_hashes.txt must not be empty"

    def test_do_install_passes_hashes_file_or_inline_hash_to_pip(self):
        """_do_install must supply hash verification to pip (via -r or inline --hash)."""
        import amplihack.memory_auto_install as mod

        captured_cmd: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            captured_cmd.append(list(cmd))
            return _make_completed(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            mod._do_install([sys.executable, "-m", "pip"])

        assert captured_cmd, "_do_install did not call subprocess.run"
        full_cmd = " ".join(captured_cmd[0])
        has_hashes_ref = (
            "memory_auto_install_hashes" in full_cmd
            or "--hash=sha256:" in full_cmd
            or "--hash sha256:" in full_cmd
        )
        assert has_hashes_ref, (
            "pip install command must reference the hashes file or include "
            f"inline --hash=sha256: entries; got: {full_cmd!r}"
        )


# ============================================================================
# SEC-07: _sanitize_error() existence, behaviour, and usage
# ============================================================================


class TestSec07ErrorSanitization:
    """SEC-07: _sanitize_error must exist and strip absolute paths from messages."""

    def test_sanitize_error_exists(self):
        """_sanitize_error must be importable from memory_auto_install."""
        import amplihack.memory_auto_install as mod

        assert hasattr(mod, "_sanitize_error"), (
            "_sanitize_error() function is missing from memory_auto_install"
        )

    def test_sanitize_error_strips_unix_absolute_path(self):
        """Unix absolute paths like /home/user/.../site-packages must be removed."""
        import amplihack.memory_auto_install as mod

        raw = (
            "ERROR: Could not install packages due to an OSError: "
            "'/home/user/.local/lib/python3.11/site-packages/amplihack_memory'"
        )
        result = mod._sanitize_error(raw)
        assert "/home/user" not in result, (
            f"Unix absolute path must be stripped; got: {result!r}"
        )

    def test_sanitize_error_strips_windows_absolute_path(self):
        """Windows absolute paths like C:\\Users\\foo\\... must be removed."""
        import amplihack.memory_auto_install as mod

        raw = (
            "ERROR: Could not install: "
            "C:\\Users\\foo\\AppData\\Local\\Programs\\Python\\Python311"
            "\\Lib\\site-packages\\amplihack_memory"
        )
        result = mod._sanitize_error(raw)
        assert "C:\\Users\\foo" not in result, (
            f"Windows absolute path must be stripped; got: {result!r}"
        )

    def test_sanitize_error_preserves_non_path_content(self):
        """Non-path error text must survive sanitization intact."""
        import amplihack.memory_auto_install as mod

        raw = "pip install failed: network timeout after 120s"
        result = mod._sanitize_error(raw)
        assert "network timeout after 120s" in result, (
            f"Non-path content must not be removed; got: {result!r}"
        )

    def test_do_install_uses_sanitize_error_on_failure(self):
        """_do_install must call _sanitize_error() when formatting the failure message."""
        import amplihack.memory_auto_install as mod

        leaked_path = "/home/ci-runner/.local/lib/python3.11/site-packages"
        fake_result = _make_completed(
            returncode=1,
            stderr=f"ERROR: {leaked_path}/amplihack_memory not found",
        )

        sanitize_calls: list[str] = []

        def tracking_sanitize(msg: str) -> str:
            sanitize_calls.append(msg)
            return msg.replace(leaked_path, "<path>")

        with (
            patch("subprocess.run", return_value=fake_result),
            patch(_PKG + "._sanitize_error", side_effect=tracking_sanitize),
        ):
            mod._do_install([sys.executable, "-m", "pip"])

        assert sanitize_calls, (
            "_do_install must call _sanitize_error() when printing the pip "
            "failure message so that absolute paths are stripped"
        )

    def test_do_install_does_not_leak_path_in_output(self, capsys):
        """When pip fails, the printed error must not contain absolute paths."""
        import amplihack.memory_auto_install as mod

        leaked_path = "/home/ci-runner/.local/lib/python3.11/site-packages"
        fake_result = _make_completed(
            returncode=1,
            stderr=f"ERROR: {leaked_path}/amplihack_memory not found",
        )

        with patch("subprocess.run", return_value=fake_result):
            mod._do_install([sys.executable, "-m", "pip"])

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "/home/ci-runner" not in combined, (
            "Absolute path must not appear in printed output after sanitization; "
            f"got:\n{combined}"
        )
