# File: amplifier-bundle/recipes/tests/conftest.py
"""
Session-scoped fixtures for recipe push-diverged-remote fix tests.
Loads both workflow YAML files once and exposes them as line arrays and
raw content strings to minimize I/O during the test run.
"""
import pathlib
import pytest

RECIPES_DIR = pathlib.Path(__file__).parent.parent

DEFAULT_WORKFLOW_PATH = RECIPES_DIR / "default-workflow.yaml"
CONSENSUS_WORKFLOW_PATH = RECIPES_DIR / "consensus-workflow.yaml"


@pytest.fixture(scope="session")
def default_workflow_path():
    return DEFAULT_WORKFLOW_PATH


@pytest.fixture(scope="session")
def consensus_workflow_path():
    return CONSENSUS_WORKFLOW_PATH


@pytest.fixture(scope="session")
def default_workflow_content():
    return DEFAULT_WORKFLOW_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def consensus_workflow_content():
    return CONSENSUS_WORKFLOW_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def default_workflow_lines(default_workflow_content):
    return default_workflow_content.splitlines()


@pytest.fixture(scope="session")
def consensus_workflow_lines(consensus_workflow_content):
    return consensus_workflow_content.splitlines()
