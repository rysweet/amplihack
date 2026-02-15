"""Pytest configuration and fixtures for amplihack-memory-lib tests."""

import shutil

import pytest


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Ensure each test uses isolated temporary storage.

    This fixture:
    - Creates unique temp directory for each test
    - Cleans up after test completes
    - Prevents database locking between tests
    """
    # Create unique storage path for this test
    storage_path = tmp_path / "test_memory"
    storage_path.mkdir(parents=True, exist_ok=True)

    yield storage_path

    # Cleanup: Remove all test databases
    if storage_path.exists():
        shutil.rmtree(storage_path, ignore_errors=True)


@pytest.fixture
def temp_storage(tmp_path):
    """Provide explicit temporary storage path for tests that need it."""
    storage_path = tmp_path / "explicit_memory"
    storage_path.mkdir(parents=True, exist_ok=True)
    yield storage_path
    if storage_path.exists():
        shutil.rmtree(storage_path, ignore_errors=True)
