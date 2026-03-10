"""Fleet test configuration.

Sets AZLIN_PATH for the test environment so get_azlin_path() works
even when azlin is not on PATH.
"""

import os
import shutil

import pytest


@pytest.fixture(autouse=True)
def set_azlin_path(monkeypatch):
    """Ensure AZLIN_PATH is set for all fleet tests.

    Checks in order: existing AZLIN_PATH env var, shutil.which, known location.
    """
    if os.environ.get("AZLIN_PATH"):
        return  # Already set

    which_path = shutil.which("azlin")
    if which_path:
        monkeypatch.setenv("AZLIN_PATH", which_path)
        return

    # Known development location
    dev_path = "/home/azureuser/src/azlin/.venv/bin/azlin"
    if os.path.exists(dev_path):
        monkeypatch.setenv("AZLIN_PATH", dev_path)
        return

    # Use a dummy path for tests that mock subprocess anyway
    monkeypatch.setenv("AZLIN_PATH", "/usr/bin/azlin")
