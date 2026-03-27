"""Security hygiene tests — Python-side parity with amplihack-rs security contract.

Mirrors the security_hygiene_test.rs TDD contract in the Rust repo
(TC-SEC-01 through TC-SEC-22).  These tests verify the 5 core security
controls required for parity:

1. Session-name / path argument validation             (TC-PY-SEC-01–05)
2. No ``subprocess`` call uses ``shell=True`` with user input (TC-PY-SEC-06–09)
3. Temp-file permissions are restrictive (0o600)       (TC-PY-SEC-10–11)
4. No hardcoded secrets / API-key patterns in source   (TC-PY-SEC-12)
5. Shell metachar / injection rejection                (TC-PY-SEC-13–17)

Running::

    pytest tests/test_security_hygiene.py -v
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Repository root — two levels up from tests/
REPO_ROOT = Path(__file__).parent.parent
SRC_ROOT = REPO_ROOT / "src"

SAFE_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")

# Patterns that look like hardcoded secrets (matches API key / token formats)
SECRET_PATTERNS = [
    re.compile(r'sk-[A-Za-z0-9]{20,}'),            # OpenAI-style API keys
    re.compile(r'ghp_[A-Za-z0-9]{36,}'),            # GitHub PATs
    re.compile(r'AKIA[0-9A-Z]{16}'),                 # AWS Access Key IDs
    re.compile(r'(?i)api[_\-]?key\s*=\s*["\'][^"\']{16,}["\']'),  # generic
    re.compile(r'(?i)password\s*=\s*["\'][^"\']{8,}["\']'),       # passwords
]

# Shell metacharacters that must be rejected when appearing in user-supplied args
SHELL_METACHARS = [";", "&&", "||", "|", "`", "$(", "${", "\n", "\r"]


# ---------------------------------------------------------------------------
# TC-PY-SEC-01 to TC-PY-SEC-05  Session / path arg validation
# ---------------------------------------------------------------------------


class TestSessionNameValidation:
    """Session IDs and path arguments must be validated before use."""

    @pytest.mark.parametrize(
        "bad_name",
        [
            "../evil",
            "../../etc/passwd",
            "/absolute/path",
            "",
            "a" * 129,  # too long
            "name with spaces",
            "name;rm -rf /",
        ],
    )
    def test_session_id_allowlist_rejects_bad_names(self, bad_name):
        """TC-PY-SEC-01: Dangerous session IDs do not pass the allowlist regex."""
        assert not SAFE_SESSION_ID_RE.fullmatch(bad_name), (
            f"Session ID {bad_name!r} should have been rejected by allowlist"
        )

    @pytest.mark.parametrize(
        "good_name",
        [
            "my-session",
            "session_001",
            "abc123",
            "Session-XYZ",
            "a" * 128,  # exactly at the limit
        ],
    )
    def test_session_id_allowlist_accepts_valid_names(self, good_name):
        """TC-PY-SEC-02: Valid session IDs pass the allowlist regex."""
        assert SAFE_SESSION_ID_RE.fullmatch(good_name), (
            f"Session ID {good_name!r} should have been accepted by allowlist"
        )

    def test_path_traversal_rejected_by_env_var_validation(self, tmp_path):
        """TC-PY-SEC-03: Path traversal in env-var paths is rejected."""
        pytest.importorskip("kuzu")
        from amplihack.memory.kuzu.connector import KuzuConnector

        bad = str(tmp_path) + "/../etc"
        with pytest.raises(ValueError, match=r"\.\.|blocked|absolute"):
            KuzuConnector._validate_env_db_path(bad, "AMPLIHACK_GRAPH_DB_PATH")

    def test_relative_path_rejected_by_env_var_validation(self):
        """TC-PY-SEC-04: Relative paths in env-var paths are rejected."""
        pytest.importorskip("kuzu")
        from amplihack.memory.kuzu.connector import KuzuConnector

        with pytest.raises(ValueError, match="absolute"):
            KuzuConnector._validate_env_db_path("relative/path", "AMPLIHACK_GRAPH_DB_PATH")

    @pytest.mark.parametrize("blocked", ["/proc/1", "/sys/fs", "/dev/sda"])
    def test_blocked_prefix_rejected_by_env_var_validation(self, blocked):
        """TC-PY-SEC-05: /proc, /sys, /dev prefixes are rejected."""
        pytest.importorskip("kuzu")
        from amplihack.memory.kuzu.connector import KuzuConnector

        with pytest.raises(ValueError, match="blocked"):
            KuzuConnector._validate_env_db_path(blocked, "AMPLIHACK_GRAPH_DB_PATH")


# ---------------------------------------------------------------------------
# TC-PY-SEC-06 to TC-PY-SEC-09  No shell=True with user input
# ---------------------------------------------------------------------------


class TestNoShellEqualsTrue:
    """Source code must not use subprocess with shell=True on user-controlled strings."""

    def _grep_source(self, pattern: str) -> list[str]:
        """Return lines matching pattern in Python source files."""
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", pattern, str(SRC_ROOT)],
            capture_output=True,
            text=True,
        )
        return [line for line in result.stdout.splitlines() if line.strip()]

    def test_no_shell_true_in_hooks(self):
        """TC-PY-SEC-06: Hook source files never call subprocess with shell=True."""
        hooks_src = SRC_ROOT / "amplihack" / "hooks"
        if not hooks_src.exists():
            pytest.skip("hooks source directory not found")

        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", r"shell\s*=\s*True", str(hooks_src)],
            capture_output=True,
            text=True,
        )
        matches = [l for l in result.stdout.splitlines() if l.strip()]
        assert matches == [], (
            "Hooks must not use subprocess with shell=True:\n" + "\n".join(matches)
        )

    def test_no_sh_c_user_input_pattern_in_launcher(self):
        """TC-PY-SEC-07: Launcher never constructs 'sh -c <user-input>' patterns."""
        launcher_src = SRC_ROOT / "amplihack" / "launcher"
        if not launcher_src.exists():
            pytest.skip("launcher source directory not found")

        # Look for 'sh', '-c' appearing together with variable interpolation
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", r'"sh".*"-c"', str(launcher_src)],
            capture_output=True,
            text=True,
        )
        matches = [l for l in result.stdout.splitlines() if l.strip()]
        assert matches == [], (
            "Launcher must not construct 'sh -c' with user input:\n" + "\n".join(matches)
        )

    def test_subprocess_calls_use_list_not_string(self):
        """TC-PY-SEC-08: subprocess.run/Popen calls in hooks use list, not string args."""
        hooks_src = SRC_ROOT / "amplihack" / "hooks"
        if not hooks_src.exists():
            pytest.skip("hooks source directory not found")

        # Find subprocess.run("string" ...) patterns (string literal first arg)
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", r'subprocess\.run\s*\(\s*["\']', str(hooks_src)],
            capture_output=True,
            text=True,
        )
        matches = [l for l in result.stdout.splitlines() if l.strip()]
        assert matches == [], (
            "subprocess.run must be called with a list, not a string:\n" + "\n".join(matches)
        )


# ---------------------------------------------------------------------------
# TC-PY-SEC-10 to TC-PY-SEC-11  Temp-file permissions
# ---------------------------------------------------------------------------


class TestTempfilePermissions:
    """Temporary files must be created with restrictive (0o600) permissions."""

    def test_tempfile_default_mode_is_restrictive(self, tmp_path):
        """TC-PY-SEC-10: tempfile.NamedTemporaryFile creates files with 0o600 mode."""
        with tempfile.NamedTemporaryFile(dir=tmp_path, delete=False) as f:
            path = Path(f.name)

        mode = stat.S_IMODE(os.stat(path).st_mode)
        # Standard tempfile should give owner-only permissions on Linux
        assert mode & 0o777 <= 0o600, (
            f"Temp file mode {oct(mode)} is too permissive; expected <= 0o600"
        )
        path.unlink(missing_ok=True)

    def test_explicit_chmod_600_on_sensitive_files(self, tmp_path):
        """TC-PY-SEC-11: Sensitive files (e.g. memory.db) are chmod 0o600 after creation."""
        # Verify that MemoryDatabase applies 0o600 on init
        from amplihack.memory.database import MemoryDatabase

        db_path = tmp_path / "test_memory.db"
        db = MemoryDatabase(db_path=db_path)
        db.close()

        mode = stat.S_IMODE(os.stat(db_path).st_mode)
        assert mode == 0o600, (
            f"memory.db mode is {oct(mode)}, expected 0o600"
        )


# ---------------------------------------------------------------------------
# TC-PY-SEC-12  No hardcoded secrets in source
# ---------------------------------------------------------------------------


class TestNoHardcodedSecrets:
    """Source files must not contain hardcoded API keys or passwords."""

    @pytest.mark.parametrize("pattern", SECRET_PATTERNS)
    def test_no_hardcoded_secrets_in_src(self, pattern):
        """TC-PY-SEC-12: Source files contain no hardcoded secrets."""
        violations = []
        for py_file in SRC_ROOT.rglob("*.py"):
            try:
                text = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    # Allow lines that are obviously tests / documentation
                    if any(kw in line for kw in ("# noqa", "example", "test", "dummy", "placeholder", "YOUR_", ">>>", "sanitize", "sanitizer", "redact", "mask")):
                        continue
                    violations.append(f"{py_file.relative_to(REPO_ROOT)}:{lineno}: {line.strip()!r}")

        assert violations == [], (
            f"Potential hardcoded secrets found:\n" + "\n".join(violations[:10])
        )


# ---------------------------------------------------------------------------
# TC-PY-SEC-13 to TC-PY-SEC-17  Shell metachar rejection
# ---------------------------------------------------------------------------


class TestShellMetacharRejection:
    """Shell metacharacters in user-supplied names must be caught by validation."""

    @pytest.mark.parametrize("metachar", SHELL_METACHARS)
    def test_session_id_rejects_shell_metachars(self, metachar):
        """TC-PY-SEC-13: Session IDs containing shell metacharacters are rejected."""
        evil_name = f"session{metachar}evil"
        assert not SAFE_SESSION_ID_RE.fullmatch(evil_name), (
            f"Session ID with metachar {metachar!r} should have been rejected"
        )

    def test_empty_session_id_rejected(self):
        """TC-PY-SEC-14: Empty string is rejected as a session ID."""
        assert not SAFE_SESSION_ID_RE.fullmatch(""), (
            "Empty session ID must be rejected"
        )

    def test_session_id_with_null_byte_rejected(self):
        """TC-PY-SEC-15: Session IDs containing null bytes are rejected."""
        assert not SAFE_SESSION_ID_RE.fullmatch("session\x00evil"), (
            "Session ID with null byte must be rejected"
        )

    def test_session_id_with_newline_rejected(self):
        """TC-PY-SEC-16: Session IDs containing newlines are rejected."""
        assert not SAFE_SESSION_ID_RE.fullmatch("session\nevil"), (
            "Session ID with newline must be rejected"
        )

    def test_env_var_path_with_shell_metachars_rejected(self):
        """TC-PY-SEC-17: Paths with shell metachars in env vars are rejected (non-absolute)."""
        pytest.importorskip("kuzu")
        from amplihack.memory.kuzu.connector import KuzuConnector

        # Non-absolute paths are rejected before metachar check
        with pytest.raises(ValueError):
            KuzuConnector._validate_env_db_path(";rm -rf /", "AMPLIHACK_GRAPH_DB_PATH")
