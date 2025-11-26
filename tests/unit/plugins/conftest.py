"""Pytest fixtures for plugin system tests.

Provides automatic cleanup between tests to ensure isolation.
"""

import importlib
import sys

import pytest


@pytest.fixture(autouse=True)
def clean_plugin_state():
    """Automatically clear plugin system state before and after each test."""
    from src.amplihack.plugins import loader
    from src.amplihack.plugins.registry import PluginRegistry

    # Clear before test
    registry = PluginRegistry()
    registry.clear()
    if hasattr(loader, "_plugin_cache"):
        loader._plugin_cache.clear()

    # Reload HelloPlugin to re-trigger decorator registration
    # This ensures HelloPlugin is registered for integration tests that need it
    if "src.amplihack.plugins.builtin.hello" in sys.modules:
        try:
            import src.amplihack.plugins.builtin.hello

            importlib.reload(src.amplihack.plugins.builtin.hello)
        except Exception:
            pass  # OK if reload fails

    yield

    # Clear after test
    registry.clear()
    if hasattr(loader, "_plugin_cache"):
        loader._plugin_cache.clear()
