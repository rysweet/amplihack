# Root conftest.py for pytest configuration

import os

# Allow CI and recipe runners to skip kuzu tests that require a running Kuzu
# database or cmake build environment.  Set AMPLIHACK_SKIP_KUZU_TESTS=1 to
# exclude all kuzu-related test files from collection.
SKIP_KUZU = os.environ.get("AMPLIHACK_SKIP_KUZU_TESTS", "0") == "1"
collect_ignore_glob = ["**/test_*kuzu*.py", "**/tests/kuzu/**/*.py"] if SKIP_KUZU else []

# Enable pytest-asyncio plugin for async test support
pytest_plugins = ("pytest_asyncio",)
