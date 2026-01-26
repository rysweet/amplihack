"""
Shared pytest fixtures for plugin tests.

Provides common test fixtures and utilities for all plugin tests.
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def plugin_source(tmp_path):
    """
    Create a minimal plugin source directory for testing.

    Returns:
        Path: Path to plugin source with basic .claude/ structure
    """
    plugin_dir = tmp_path / "amplihack_source"
    claude_dir = plugin_dir / ".claude"

    # Create basic structure
    (claude_dir / "context").mkdir(parents=True)
    (claude_dir / "context" / "PHILOSOPHY.md").write_text("# Development Philosophy")
    (claude_dir / "context" / "PROJECT.md").write_text("# Project Context")

    (claude_dir / "tools").mkdir(parents=True)
    hook_script = claude_dir / "tools" / "hook.sh"
    hook_script.write_text("#!/bin/bash\necho 'Hook executed'")
    hook_script.chmod(0o755)

    (claude_dir / "agents" / "amplihack").mkdir(parents=True)
    (claude_dir / "agents" / "amplihack" / "architect.md").write_text("# Architect Agent")

    # Create base settings
    settings = {
        "version": "1.0.0",
        "hooks": {"PreRun": "${CLAUDE_PLUGIN_ROOT}/tools/hook.sh"},
        "lspServers": {},
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2))

    return plugin_dir


@pytest.fixture
def plugin_home(tmp_path):
    """
    Create a plugin home directory (simulates ~/.amplihack/).

    Returns:
        Path: Path to plugin home directory
    """
    return tmp_path / "home" / ".amplihack"


@pytest.fixture
def old_installation(tmp_path):
    """
    Create an old-style amplihack installation for migration testing.

    Returns:
        Path: Path to old .claude/ directory in project
    """
    project_dir = tmp_path / "old_project"
    claude_dir = project_dir / ".claude"

    # Create old-style structure
    (claude_dir / "context").mkdir(parents=True)
    (claude_dir / "context" / "PHILOSOPHY.md").write_text("# Philosophy")
    (claude_dir / "context" / "USER_PREFERENCES.md").write_text("# User Preferences")

    (claude_dir / "agents" / "amplihack").mkdir(parents=True)
    (claude_dir / "agents" / "amplihack" / "builder.md").write_text("# Builder")

    (claude_dir / "agents" / "custom").mkdir(parents=True)
    (claude_dir / "agents" / "custom" / "my_agent.md").write_text("# My Custom Agent")

    (claude_dir / "runtime").mkdir(parents=True)
    (claude_dir / "runtime" / "session.json").write_text('{"session_id": "test123"}')

    (claude_dir / "logs").mkdir(parents=True)
    (claude_dir / "logs" / "app.log").write_text("Log entry")

    # Old settings (no variables)
    settings = {"version": "0.9.0", "hooks": {"PreRun": ".claude/tools/hook.sh"}}
    (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2))

    return project_dir


@pytest.fixture
def python_project(tmp_path):
    """
    Create a Python project for LSP detection testing.

    Returns:
        Path: Path to Python project root
    """
    project = tmp_path / "python_project"
    project.mkdir()

    # Python manifest
    (project / "requirements.txt").write_text("flask\nrequests\npytest")

    # Python files
    (project / "main.py").write_text("""
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
""")

    src_dir = project / "src" / "mypackage"
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text("")
    (src_dir / "module.py").write_text("def helper(): pass")

    return project


@pytest.fixture
def typescript_project(tmp_path):
    """
    Create a TypeScript project for LSP detection testing.

    Returns:
        Path: Path to TypeScript project root
    """
    project = tmp_path / "typescript_project"
    project.mkdir()

    # package.json with TypeScript
    package_json = {
        "name": "test-project",
        "version": "1.0.0",
        "dependencies": {"typescript": "^5.0.0", "react": "^18.0.0"},
    }
    (project / "package.json").write_text(json.dumps(package_json, indent=2))

    # TypeScript files
    (project / "index.ts").write_text("""
export function greet(name: string): string {
    return `Hello, ${name}!`;
}
""")

    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "app.tsx").write_text("""
import React from 'react';

export const App: React.FC = () => {
    return <div>Hello</div>;
};
""")

    return project


@pytest.fixture
def multipage_project(tmp_path):
    """
    Create a multi-language project for LSP detection testing.

    Returns:
        Path: Path to multi-language project root
    """
    project = tmp_path / "fullstack_project"
    project.mkdir()

    # Python backend
    backend = project / "backend"
    backend.mkdir()
    (backend / "requirements.txt").write_text("fastapi\nuvicorn")
    (backend / "main.py").write_text("from fastapi import FastAPI")

    # TypeScript frontend
    frontend = project / "frontend"
    frontend.mkdir()
    frontend_package = {"dependencies": {"typescript": "^5.0.0", "react": "^18.0.0"}}
    (frontend / "package.json").write_text(json.dumps(frontend_package, indent=2))
    (frontend / "index.tsx").write_text("console.log('app');")

    # Rust microservice
    microservice = project / "microservice"
    microservice.mkdir()
    (microservice / "Cargo.toml").write_text("""
[package]
name = "microservice"
version = "0.1.0"
""")

    return project


@pytest.fixture
def sample_settings():
    """
    Provide sample settings dictionary for testing.

    Returns:
        dict: Sample settings structure
    """
    return {
        "version": "1.0.0",
        "hooks": {
            "PreRun": "${CLAUDE_PLUGIN_ROOT}/tools/pre_run.sh",
            "PostRun": "${CLAUDE_PLUGIN_ROOT}/tools/post_run.sh",
        },
        "lspServers": {"python": {"command": "pylsp", "args": []}},
        "exclude": ["node_modules", ".git", ".venv"],
    }


@pytest.fixture
def sample_variables():
    """
    Provide sample variable substitution dictionary.

    Returns:
        dict: Sample variables for substitution
    """
    return {
        "CLAUDE_PLUGIN_ROOT": "/home/user/.amplihack/.claude",
        "PROJECT_ROOT": "/home/user/projects/myproject",
    }


# Helper functions for tests


def create_minimal_plugin(path: Path) -> Path:
    """
    Create a minimal plugin structure for testing.

    Args:
        path: Base path to create plugin in

    Returns:
        Path to created .claude/ directory
    """
    claude_dir = path / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text('{"version": "1.0"}')
    return claude_dir


def assert_settings_equal(actual: dict, expected: dict, ignore_keys=None):
    """
    Assert two settings dictionaries are equal, optionally ignoring keys.

    Args:
        actual: Actual settings dict
        expected: Expected settings dict
        ignore_keys: List of keys to ignore in comparison
    """
    if ignore_keys:
        actual = {k: v for k, v in actual.items() if k not in ignore_keys}
        expected = {k: v for k, v in expected.items() if k not in ignore_keys}

    assert actual == expected, f"Settings mismatch:\nActual: {actual}\nExpected: {expected}"


def assert_file_exists(path: Path, message: str = None):
    """
    Assert that a file exists with optional custom message.

    Args:
        path: Path to check
        message: Optional custom error message
    """
    assert path.exists(), message or f"File does not exist: {path}"


def assert_dir_structure(base_path: Path, expected_structure: dict):
    """
    Assert that directory structure matches expected structure.

    Args:
        base_path: Base directory to check
        expected_structure: Dict describing expected structure
            Example: {"dir1": {"file1.txt": None, "subdir": {}}}
    """
    for name, content in expected_structure.items():
        path = base_path / name
        assert path.exists(), f"Expected path does not exist: {path}"

        if isinstance(content, dict):
            assert path.is_dir(), f"Expected directory but found file: {path}"
            assert_dir_structure(path, content)
        else:
            assert path.is_file(), f"Expected file but found directory: {path}"
