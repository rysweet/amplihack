# Kuzu Test Configuration

The `amplihack` test suite includes tests that import `kuzu` — a C++ graph
database with a Python binding. In environments where `kuzu` is not installed
(e.g., CI without cmake, containers), these tests should skip gracefully rather
than hang or error.

This document explains the approved isolation mechanism and the root cause that
was fixed.

## Contents

- [How kuzu tests skip gracefully](#how-kuzu-tests-skip-gracefully)
- [Root cause: package shadowing bug](#root-cause-package-shadowing-bug)
- [Which test files are guarded](#which-test-files-are-guarded)
- [Verify the skip works](#verify-the-skip-works)
- [Related](#related)

---

## How kuzu tests skip gracefully

Each kuzu-specific test file has `pytest.importorskip("kuzu")` near the top:

```python
import pytest

pytest.importorskip("kuzu")  # skips entire module if kuzu not installed

from src.amplihack.memory.backends.kuzu_backend import KuzuBackend
```

When `kuzu` is not installed, `pytest.importorskip` raises `Skipped` during
collection, and the entire module is skipped cleanly — no error, no hang.

This is the standard pytest pattern for optional-dependency tests and requires
no environment variables or conftest configuration.

> **Note:** PR #3110, which proposed an `AMPLIHACK_SKIP_KUZU_TESTS` environment
> variable guard in `conftest.py`, was rejected. The `pytest.importorskip`
> approach in individual files is simpler, more portable, and follows standard
> pytest conventions.

---

## Root cause: package shadowing bug

The original hang was caused by `tests/memory/kuzu/__init__.py` existing.

**How it happened:**

1. `tests/memory/kuzu/__init__.py` made `tests/memory/kuzu/` a Python package.
2. pytest's default (prepend) import mode added `tests/memory/` to `sys.path`
   when collecting files from that directory.
3. `import kuzu` in `kuzu_backend.py` resolved to `tests/memory/kuzu/` (the
   test package) instead of the installed PyPI `kuzu` package.
4. The test package had no `Database` attribute → `AttributeError` at collection
   time, causing hangs.

**The fix:** `tests/memory/kuzu/__init__.py` and
`tests/memory/kuzu/indexing/__init__.py` were deleted. Without `__init__.py`,
pytest adds `tests/memory/kuzu/` itself (not `tests/memory/`) to `sys.path`,
and there is no `kuzu` package name to shadow there.

---

## Which test files are guarded

All kuzu-specific test files carry `pytest.importorskip("kuzu")`:

| File                                                   | Notes                                               |
| ------------------------------------------------------ | --------------------------------------------------- |
| `tests/memory/backends/test_kuzu_session_isolation.py` | Guard placed before module-level KuzuBackend import |
| `tests/memory/backends/test_kuzu_schema_redesign.py`   |                                                     |
| `tests/memory/backends/test_kuzu_code_schema.py`       |                                                     |
| `tests/memory/backends/test_kuzu_auto_linking.py`      |                                                     |
| `tests/memory/kuzu/test_kuzu_connector.py`             |                                                     |
| `tests/unit/memory/test_kuzu_retry.py`                 |                                                     |

The guard coverage is verified by `tests/test_kuzu_skip_guard.py` (WS4 tests).

---

## Verify the skip works

When kuzu is installed, all tests collect and run normally:

```sh
pytest --collect-only -q tests/memory/backends/test_kuzu_session_isolation.py
```

To simulate a missing kuzu installation, temporarily rename the package and
confirm the module is skipped (not errored):

```sh
pytest --collect-only -q tests/memory/backends/test_kuzu_schema_redesign.py
# With kuzu absent: "1 skipped" not "ERROR"
```

Collection time for all kuzu tests must be under 10 seconds:

```sh
time pytest --collect-only -q tests/memory/ tests/unit/memory/
```

---

## Related

- [conftest.py](../conftest.py) — Root pytest configuration (minimal, no kuzu-specific guards)
- [pytest importorskip docs](https://docs.pytest.org/en/stable/reference/pytest.html#pytest.importorskip)
- [kuzu Python bindings](https://docs.kuzudb.com/client-apis/python/) — upstream library
- [Ladybug Migration Guide](LADYBUG_MIGRATION_GUIDE.md) — `kuzu_store` → `ladybug_store` upgrade

> **Note:** The `KuzuGraphStore` class (in `amplihack.memory.ladybug_store`)
> now imports `ladybug` with a fallback to `kuzu`. The backend-level test files
> listed above still test `kuzu_backend.py` which imports `kuzu` directly — those
> are separate from the `KuzuGraphStore` migration.
