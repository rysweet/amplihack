"""TDD tests for Bug #3309: Replace deprecated datetime.utcnow().

Python 3.12+ deprecates datetime.utcnow() because it returns a naive
datetime that's ambiguous. The fix replaces all occurrences with
datetime.now(timezone.utc) which returns a timezone-aware datetime.

These tests verify:
1. No production .py file uses datetime.utcnow()
2. Key files use datetime.now(timezone.utc) instead
3. Timestamp strings handle the +00:00 vs Z format correctly
"""

import re
from datetime import UTC
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

# Files that MUST NOT contain utcnow() after the fix
PRODUCTION_DIRS = [
    REPO_ROOT / "src",
    REPO_ROOT / "scripts",
    REPO_ROOT / ".claude" / "tools",
    REPO_ROOT / "docs" / "claude" / "tools",
    REPO_ROOT / "amplifier-bundle" / "tools",
]

# Specific files called out in the bug report
KEY_FILES = [
    REPO_ROOT / "src" / "amplihack" / "bundle_generator" / "builder.py",
    REPO_ROOT / "src" / "amplihack" / "bundle_generator" / "packager.py",
    REPO_ROOT / "src" / "amplihack" / "bundle_generator" / "exceptions.py",
    REPO_ROOT / "scripts" / "validate_gh_pages_links.py",
    REPO_ROOT / ".claude" / "tools" / "amplihack" / "generate_workflow_report.py",
    REPO_ROOT / ".claude" / "tools" / "amplihack" / "profile_management" / "index.py",
    REPO_ROOT / ".claude" / "tools" / "amplihack" / "update_prefs.py",
]

# Mirror pairs: source → [mirrors]
MIRROR_PAIRS = {
    REPO_ROOT / ".claude" / "tools" / "amplihack": [
        REPO_ROOT / "amplifier-bundle" / "tools" / "amplihack",
        REPO_ROOT / "docs" / "claude" / "tools" / "amplihack",
    ],
}

UTCNOW_PATTERN = re.compile(r"\.utcnow\b")


def _find_py_files(*dirs: Path) -> list[Path]:
    """Collect all .py files under given directories, excluding venvs."""
    files = []
    for d in dirs:
        if not d.exists():
            continue
        for f in d.rglob("*.py"):
            parts = f.parts
            if any(p in (".venv", "venv", "__pycache__", ".git", "node_modules") for p in parts):
                continue
            files.append(f)
    return files


@pytest.mark.unit
class TestNoUtcnowInProduction:
    """Zero occurrences of datetime.utcnow() in production code."""

    def test_no_utcnow_in_src(self):
        """src/ directory must have zero utcnow() calls."""
        violations = []
        for f in _find_py_files(REPO_ROOT / "src"):
            content = f.read_text()
            for i, line in enumerate(content.splitlines(), 1):
                if UTCNOW_PATTERN.search(line):
                    violations.append(f"{f.relative_to(REPO_ROOT)}:{i}: {line.strip()}")
        assert not violations, f"Found {len(violations)} utcnow() call(s) in src/:\n" + "\n".join(
            violations
        )

    def test_no_utcnow_in_scripts(self):
        """scripts/ directory must have zero utcnow() calls."""
        violations = []
        for f in _find_py_files(REPO_ROOT / "scripts"):
            content = f.read_text()
            for i, line in enumerate(content.splitlines(), 1):
                if UTCNOW_PATTERN.search(line):
                    violations.append(f"{f.relative_to(REPO_ROOT)}:{i}: {line.strip()}")
        assert not violations, (
            f"Found {len(violations)} utcnow() call(s) in scripts/:\n" + "\n".join(violations)
        )

    def test_no_utcnow_in_claude_tools(self):
        """.claude/tools/ must have zero utcnow() calls."""
        violations = []
        for f in _find_py_files(REPO_ROOT / ".claude" / "tools"):
            content = f.read_text()
            for i, line in enumerate(content.splitlines(), 1):
                if UTCNOW_PATTERN.search(line):
                    violations.append(f"{f.relative_to(REPO_ROOT)}:{i}: {line.strip()}")
        assert not violations, (
            f"Found {len(violations)} utcnow() call(s) in .claude/tools/:\n" + "\n".join(violations)
        )

    def test_no_utcnow_in_amplifier_bundle_tools(self):
        """amplifier-bundle/tools/ mirrors must have zero utcnow() calls."""
        violations = []
        for f in _find_py_files(REPO_ROOT / "amplifier-bundle" / "tools"):
            content = f.read_text()
            for i, line in enumerate(content.splitlines(), 1):
                if UTCNOW_PATTERN.search(line):
                    violations.append(f"{f.relative_to(REPO_ROOT)}:{i}: {line.strip()}")
        assert not violations, (
            f"Found {len(violations)} utcnow() call(s) in amplifier-bundle/tools/:\n"
            + "\n".join(violations)
        )

    def test_no_utcnow_in_docs_tools(self):
        """docs/claude/tools/ mirrors must have zero utcnow() calls."""
        violations = []
        for f in _find_py_files(REPO_ROOT / "docs" / "claude" / "tools"):
            content = f.read_text()
            for i, line in enumerate(content.splitlines(), 1):
                if UTCNOW_PATTERN.search(line):
                    violations.append(f"{f.relative_to(REPO_ROOT)}:{i}: {line.strip()}")
        assert not violations, (
            f"Found {len(violations)} utcnow() call(s) in docs/claude/tools/:\n"
            + "\n".join(violations)
        )


@pytest.mark.unit
class TestKeyFilesUseTimezoneAware:
    """Each key file must import timezone and use datetime.now(timezone.utc)."""

    @pytest.mark.parametrize("filepath", KEY_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
    def test_key_file_has_no_utcnow(self, filepath: Path):
        """Specific file from bug report must not use utcnow()."""
        if not filepath.exists():
            pytest.skip(f"{filepath.relative_to(REPO_ROOT)} does not exist (may be deleted)")
        content = filepath.read_text()
        violations = []
        for i, line in enumerate(content.splitlines(), 1):
            if UTCNOW_PATTERN.search(line):
                violations.append(f"  line {i}: {line.strip()}")
        assert not violations, (
            f"{filepath.relative_to(REPO_ROOT)} still uses utcnow():\n" + "\n".join(violations)
        )

    @pytest.mark.parametrize("filepath", KEY_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
    def test_key_file_imports_timezone(self, filepath: Path):
        """Files that use datetime must import timezone."""
        if not filepath.exists():
            pytest.skip(f"{filepath.relative_to(REPO_ROOT)} does not exist")
        content = filepath.read_text()
        # Only check files that actually use datetime.now()
        if "datetime.now(" not in content and "datetime.datetime.now(" not in content:
            pytest.skip("File doesn't use datetime.now() — no timezone import needed")
        assert "timezone" in content or "UTC" in content, (
            f"{filepath.relative_to(REPO_ROOT)} uses datetime.now() but doesn't import timezone or UTC"
        )


@pytest.mark.unit
class TestBundleGeneratorExceptionTimestamp:
    """BundleGeneratorError.timestamp must be timezone-aware."""

    def test_exception_timestamp_is_timezone_aware(self):
        """BundleGeneratorError().timestamp must have tzinfo set."""
        from amplihack.bundle_generator.exceptions import BundleGeneratorError

        err = BundleGeneratorError("test error")
        assert err.timestamp.tzinfo is not None, (
            "BundleGeneratorError.timestamp is naive (no tzinfo) — "
            "must use datetime.now(timezone.utc)"
        )

    def test_exception_timestamp_is_utc(self):
        """BundleGeneratorError().timestamp must be in UTC."""

        from amplihack.bundle_generator.exceptions import BundleGeneratorError

        err = BundleGeneratorError("test error")
        assert err.timestamp.tzinfo == UTC, "BundleGeneratorError.timestamp is not UTC"

    def test_exception_to_dict_timestamp_format(self):
        """to_dict() timestamp must be a valid ISO format string."""
        from amplihack.bundle_generator.exceptions import BundleGeneratorError

        err = BundleGeneratorError("test error")
        d = err.to_dict()
        ts = d["timestamp"]
        # Should be parseable and contain timezone info (+00:00 or Z)
        assert "+" in ts or "Z" in ts, (
            f"Timestamp '{ts}' lacks timezone indicator — "
            "datetime.now(timezone.utc).isoformat() produces +00:00"
        )


@pytest.mark.unit
class TestToolMirrorsSynced:
    """After fixing utcnow in .claude/tools/, mirrors must be updated too."""

    @pytest.mark.parametrize(
        "source_dir,mirror_dirs",
        list(MIRROR_PAIRS.items()),
        ids=lambda x: str(x.relative_to(REPO_ROOT)) if isinstance(x, Path) else "mirrors",
    )
    def test_tool_mirrors_have_no_utcnow(self, source_dir: Path, mirror_dirs: list[Path]):
        """Mirror directories must also have zero utcnow() after sync."""
        for mirror_dir in mirror_dirs:
            violations = []
            for f in _find_py_files(mirror_dir):
                content = f.read_text()
                for i, line in enumerate(content.splitlines(), 1):
                    if UTCNOW_PATTERN.search(line):
                        violations.append(f"{f.relative_to(REPO_ROOT)}:{i}: {line.strip()}")
            assert not violations, (
                f"Mirror {mirror_dir.relative_to(REPO_ROOT)} still has utcnow():\n"
                + "\n".join(violations)
            )
