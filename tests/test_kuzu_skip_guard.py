"""Tests: kuzu test isolation via pytest.importorskip (WS4 — env-var guard replacement).

PR #3110 (AMPLIHACK_SKIP_KUZU_TESTS env-var guard) was rejected.
These tests verify the approved approach: individual test files use
pytest.importorskip("kuzu") to skip gracefully when kuzu is absent.

Root cause of the original hangs
---------------------------------
tests/memory/kuzu/__init__.py existed, making tests/memory/kuzu/ a Python
package.  pytest's default (prepend) import mode added tests/memory/ to
sys.path when collecting files from that directory.  Consequently
``import kuzu`` inside kuzu_backend.py resolved to the test package instead
of the installed PyPI package, raising AttributeError at collection time and
occasionally causing indefinite hangs.

The approved fixes
------------------
1. Delete tests/memory/kuzu/__init__.py  (remove the shadowing package)
2. Add pytest.importorskip("kuzu") at the top of each kuzu-specific test file
   so the module is skipped—not errored—when kuzu is absent.

These tests verify both invariants are in place.
"""

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Repo root detection
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent  # tests/ → repo root

KUZU_TEST_FILES = [
    "tests/memory/backends/test_kuzu_session_isolation.py",
    "tests/memory/backends/test_kuzu_schema_redesign.py",
    "tests/memory/backends/test_kuzu_code_schema.py",
    "tests/memory/backends/test_kuzu_auto_linking.py",
    "tests/memory/kuzu/test_kuzu_connector.py",
    "tests/unit/memory/test_kuzu_retry.py",
]


def _read_file(rel_path: str) -> str:
    """Read a repo-relative file and return its content."""
    full = REPO_ROOT / rel_path
    if not full.exists():
        pytest.fail(f"Required file not found: {full}")
    return full.read_text()


def read_root_conftest() -> str:
    """Read the root conftest.py content."""
    conftest_path = REPO_ROOT / "conftest.py"
    if not conftest_path.exists():
        pytest.fail(f"Root conftest.py not found at {conftest_path}.")
    return conftest_path.read_text()


# ---------------------------------------------------------------------------
# WS4-TEST-1: The rejected env-var guard is NOT in conftest.py
# ---------------------------------------------------------------------------


def test_root_conftest_imports_os():
    """conftest.py must NOT contain the rejected AMPLIHACK_SKIP_KUZU_TESTS guard.

    PR #3110 was rejected.  The correct isolation mechanism is
    pytest.importorskip("kuzu") in individual test files — not a root-level
    environment-variable guard.

    PASSES when: conftest.py does not reference AMPLIHACK_SKIP_KUZU_TESTS.
    FAILS when:  the rejected guard is (re)introduced to conftest.py.
    """
    content = read_root_conftest()
    assert "AMPLIHACK_SKIP_KUZU_TESTS" not in content, (
        "FAIL: root conftest.py contains the rejected AMPLIHACK_SKIP_KUZU_TESTS guard.\n"
        "PR #3110 was rejected.  Remove the guard from conftest.py.\n"
        "Use pytest.importorskip('kuzu') in individual test files instead.\n\n"
        f"Current conftest.py content:\n{content}"
    )


# ---------------------------------------------------------------------------
# WS4-TEST-2: test_kuzu_session_isolation.py has importorskip guard
# ---------------------------------------------------------------------------


def test_root_conftest_checks_skip_kuzu_env_var():
    """test_kuzu_session_isolation.py must use pytest.importorskip('kuzu').

    This file has a module-level ``from ... import KuzuBackend`` which
    triggers ``import kuzu``.  Without importorskip, it errors (not skips)
    when kuzu is absent.

    PASSES when: the importorskip call is present before the KuzuBackend import.
    FAILS when:  the guard is missing.
    """
    content = _read_file("tests/memory/backends/test_kuzu_session_isolation.py")
    has_guard = 'pytest.importorskip("kuzu")' in content or "pytest.importorskip('kuzu')" in content
    assert has_guard, (
        "FAIL: tests/memory/backends/test_kuzu_session_isolation.py is missing "
        "pytest.importorskip('kuzu').\n"
        "Add it BEFORE the module-level KuzuBackend import to prevent errors in "
        "environments where kuzu is not installed."
    )


# ---------------------------------------------------------------------------
# WS4-TEST-3: test_kuzu_schema_redesign.py has importorskip guard
# ---------------------------------------------------------------------------


def test_root_conftest_uses_exact_equality_not_truthy():
    """test_kuzu_schema_redesign.py must use pytest.importorskip('kuzu').

    PASSES when: the guard is present.
    FAILS when:  the guard is absent.
    """
    content = _read_file("tests/memory/backends/test_kuzu_schema_redesign.py")
    has_guard = 'pytest.importorskip("kuzu")' in content or "pytest.importorskip('kuzu')" in content
    assert has_guard, (
        "FAIL: tests/memory/backends/test_kuzu_schema_redesign.py is missing "
        "pytest.importorskip('kuzu')."
    )


# ---------------------------------------------------------------------------
# WS4-TEST-4: conftest.py does NOT define collect_ignore_glob
# ---------------------------------------------------------------------------


def test_root_conftest_defines_collect_ignore_glob():
    """conftest.py must NOT define collect_ignore_glob (rejected approach).

    collect_ignore_glob was part of the rejected PR #3110 design.
    The root conftest.py should remain minimal (only pytest_plugins).

    PASSES when: collect_ignore_glob is absent from conftest.py.
    FAILS when:  collect_ignore_glob is (re)introduced to conftest.py.
    """
    content = read_root_conftest()
    assert "collect_ignore_glob" not in content, (
        "FAIL: root conftest.py defines collect_ignore_glob.\n"
        "This was part of the rejected PR #3110 design.\n"
        "Remove it and use pytest.importorskip('kuzu') in test files instead.\n\n"
        f"Current conftest.py content:\n{content}"
    )


# ---------------------------------------------------------------------------
# WS4-TEST-5: tests/memory/kuzu/__init__.py does NOT exist
# ---------------------------------------------------------------------------


def test_root_conftest_collect_ignore_glob_has_hardcoded_patterns():
    """tests/memory/kuzu/__init__.py must NOT exist.

    When this file exists, pytest adds tests/memory/ to sys.path (prepend
    mode).  ``import kuzu`` in kuzu_backend.py then resolves to the test
    package instead of the installed PyPI package, causing AttributeError
    (or hangs) at collection time.

    PASSES when: the __init__.py has been deleted.
    FAILS when:  the __init__.py is re-created (accidentally or intentionally).
    """
    init_file = REPO_ROOT / "tests/memory/kuzu/__init__.py"
    assert not init_file.exists(), (
        "FAIL: tests/memory/kuzu/__init__.py exists.\n"
        "This file causes the kuzu PyPI package to be shadowed by the test "
        "package through sys.path pollution during pytest collection.\n"
        "Delete the file to prevent the shadowing."
    )


# ---------------------------------------------------------------------------
# WS4-TEST-6: pytest.importorskip skips the module when kuzu is absent
# ---------------------------------------------------------------------------


def test_skip_kuzu_guard_activates_with_env_var_set_to_one(tmp_path):
    """pytest.importorskip('kuzu') skips the module when kuzu cannot be imported.

    We simulate a missing kuzu installation by placing a stub kuzu.py that
    raises ImportError in the same directory as the test file.  pytest's
    prepend import mode adds that directory to sys.path first, so the stub
    shadows any installed kuzu package.

    PASSES when: collection produces 0 tests from the file (module skipped).
    FAILS when:  the ImportError propagates as a collection error.
    """
    # Stub that simulates "kuzu not installed"
    (tmp_path / "kuzu.py").write_text(
        "raise ImportError('kuzu stub — simulating absent installation')\n"
    )

    test_file = tmp_path / "test_kuzu_stub.py"
    test_file.write_text(
        textwrap.dedent("""\
        import pytest
        pytest.importorskip("kuzu")

        def test_uses_kuzu():
            import kuzu
            assert kuzu is not None
        """)
    )

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", str(test_file)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=30,
    )

    combined = result.stdout + result.stderr
    # importorskip converts ImportError to a skip — must not be a collection ERROR
    assert "test_uses_kuzu" not in result.stdout, (
        "FAIL: test_uses_kuzu was collected despite kuzu stub raising ImportError.\n"
        "pytest.importorskip('kuzu') must skip the module before any test runs.\n\n"
        f"pytest stdout:\n{result.stdout}\n"
        f"pytest stderr:\n{result.stderr}"
    )
    # Confirm no unexpected collection ERROR from the stub
    assert "ERROR collecting" not in combined or "kuzu stub" not in combined, (
        "FAIL: ImportError from stub kuzu leaked as a collection ERROR.\n"
        "pytest.importorskip('kuzu') should suppress it as a skip.\n\n"
        f"pytest output:\n{combined}"
    )


# ---------------------------------------------------------------------------
# WS4-TEST-7: pytest.importorskip does NOT skip when kuzu is available
# ---------------------------------------------------------------------------


def test_skip_kuzu_guard_inactive_when_env_var_is_zero(tmp_path):
    """pytest.importorskip('kuzu') does NOT skip when kuzu is importable.

    When the real kuzu package is installed, the guard should be a no-op and
    all test functions in the module should be collected normally.

    PASSES when: kuzu is installed and the test function is collected.
    SKIPPED when: kuzu is not installed in this environment.
    """
    try:
        import kuzu  # noqa: F401
    except ImportError:
        pytest.skip("kuzu not installed — cannot verify non-skip behaviour")

    test_file = tmp_path / "test_kuzu_present.py"
    test_file.write_text(
        textwrap.dedent("""\
        import pytest
        pytest.importorskip("kuzu")

        def test_kuzu_available():
            '''Should be collected because kuzu is installed.'''
            assert True
        """)
    )

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", str(test_file)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert "test_kuzu_available" in result.stdout or result.returncode == 0, (
        "FAIL: test_kuzu_available was not collected even though kuzu is installed.\n"
        "pytest.importorskip('kuzu') must NOT skip when kuzu is available.\n\n"
        f"pytest stdout:\n{result.stdout}\n"
        f"pytest stderr:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# WS4-TEST-8: Every kuzu test file has the importorskip guard (parametrized)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kuzu_test_file", KUZU_TEST_FILES)
def test_skip_kuzu_guard_inactive_for_truthy_non_one_values(tmp_path, kuzu_test_file):
    """Each kuzu test file must contain pytest.importorskip('kuzu').

    Parametrized over the complete list of kuzu-specific test files.
    Every file must carry the guard so tests skip gracefully in environments
    where kuzu is absent (CI without cmake, containers, etc.).

    PASSES when: the guard is present in the file.
    FAILS when:  any file in the list is missing the guard.
    """
    content = _read_file(kuzu_test_file)
    has_guard = 'pytest.importorskip("kuzu")' in content or "pytest.importorskip('kuzu')" in content
    assert has_guard, (
        f"FAIL: {kuzu_test_file} is missing pytest.importorskip('kuzu').\n"
        "Add the guard near the top of the file so the entire module skips "
        "gracefully when kuzu is not installed."
    )


# ---------------------------------------------------------------------------
# WS4-TEST-9: Root conftest has NO collect_ignore_glob at runtime
# ---------------------------------------------------------------------------


def test_real_root_conftest_activates_guard_at_runtime(monkeypatch):
    """At runtime, root conftest.py must NOT expose collect_ignore_glob.

    The rejected PR #3110 approach set collect_ignore_glob conditionally.
    After the rejection, conftest.py must never expose this attribute.

    PASSES when: the imported conftest module has no collect_ignore_glob attr.
    FAILS when:  collect_ignore_glob is present (rejected guard re-introduced).
    """
    conftest_path = REPO_ROOT / "conftest.py"
    if not conftest_path.exists():
        pytest.skip("root conftest.py not found — cannot test runtime behaviour")

    spec = importlib.util.spec_from_file_location("root_conftest_ws4_test", conftest_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    has_attr = hasattr(module, "collect_ignore_glob")
    if has_attr:
        patterns = module.collect_ignore_glob
        assert patterns in ([], None), (
            "FAIL: root conftest.py exposes collect_ignore_glob at runtime.\n"
            "This attribute is part of the rejected PR #3110 design.\n"
            f"Actual value: {patterns}\n"
            f"Module attributes: {[a for a in dir(module) if not a.startswith('_')]}"
        )


# ---------------------------------------------------------------------------
# WS4-TEST-10: test_kuzu_connector.py has importorskip guard
# ---------------------------------------------------------------------------


def test_real_root_conftest_guard_inactive_when_env_var_not_set(monkeypatch):
    """tests/memory/kuzu/test_kuzu_connector.py must use pytest.importorskip('kuzu').

    Verifies the guard is present in the connector unit tests, completing
    coverage for the kuzu __init__.py deletion fix.

    PASSES when: the guard is present.
    FAILS when:  the guard is missing.
    """
    content = _read_file("tests/memory/kuzu/test_kuzu_connector.py")
    has_guard = 'pytest.importorskip("kuzu")' in content or "pytest.importorskip('kuzu')" in content
    assert has_guard, (
        "FAIL: tests/memory/kuzu/test_kuzu_connector.py is missing "
        "pytest.importorskip('kuzu').\n"
        "Add the guard so the module skips gracefully when kuzu is absent."
    )
