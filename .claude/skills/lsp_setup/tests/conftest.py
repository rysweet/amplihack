"""
Pytest fixtures for LSP Auto-Configuration tests.

Provides common test fixtures and utilities following TDD principles.
"""

import pytest
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, MagicMock


@pytest.fixture
def mock_project_root(tmp_path: Path) -> Path:
    """Create a temporary project root directory."""
    return tmp_path


@pytest.fixture
def mock_env_file(mock_project_root: Path) -> Path:
    """Create a mock .env file path."""
    env_file = mock_project_root / ".env"
    return env_file


@pytest.fixture
def sample_python_files(mock_project_root: Path) -> List[Path]:
    """Create sample Python files for language detection."""
    files = []
    for name in ["main.py", "utils.py", "tests/test_main.py"]:
        file_path = mock_project_root / name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("# Python code")
        files.append(file_path)
    return files


@pytest.fixture
def sample_typescript_files(mock_project_root: Path) -> List[Path]:
    """Create sample TypeScript files for language detection."""
    files = []
    for name in ["index.ts", "utils.ts", "tests/test.ts"]:
        file_path = mock_project_root / name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("// TypeScript code")
        files.append(file_path)
    return files


@pytest.fixture
def sample_mixed_language_files(mock_project_root: Path) -> Dict[str, List[Path]]:
    """Create a project with multiple languages."""
    files = {
        "python": [],
        "typescript": [],
        "javascript": [],
        "rust": [],
    }

    # Python files
    for name in ["main.py", "utils.py"]:
        file_path = mock_project_root / name
        file_path.write_text("# Python")
        files["python"].append(file_path)

    # TypeScript files
    for name in ["index.ts", "types.ts"]:
        file_path = mock_project_root / name
        file_path.write_text("// TypeScript")
        files["typescript"].append(file_path)

    # JavaScript files
    for name in ["app.js", "config.js"]:
        file_path = mock_project_root / name
        file_path.write_text("// JavaScript")
        files["javascript"].append(file_path)

    # Rust files
    for name in ["main.rs", "lib.rs"]:
        file_path = mock_project_root / "src" / name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("// Rust")
        files["rust"].append(file_path)

    return files


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for external command testing."""
    mock = MagicMock()
    mock.return_value.returncode = 0
    mock.return_value.stdout = ""
    mock.return_value.stderr = ""
    return mock


@pytest.fixture
def mock_shutil_which():
    """Mock shutil.which for binary detection."""
    return MagicMock()


@pytest.fixture
def installed_lsp_binaries() -> Dict[str, str]:
    """Simulate installed LSP binaries."""
    return {
        "pyright": "/usr/local/bin/pyright",
        "typescript-language-server": "/usr/local/bin/typescript-language-server",
        "rust-analyzer": "/usr/local/bin/rust-analyzer",
    }


@pytest.fixture
def missing_lsp_binaries() -> Dict[str, None]:
    """Simulate missing LSP binaries."""
    return {
        "pyright": None,
        "typescript-language-server": None,
        "rust-analyzer": None,
    }


@pytest.fixture
def mock_npx_cclsp_success(mock_subprocess_run):
    """Mock successful npx cclsp install."""
    def mock_run(cmd, *args, **kwargs):
        result = Mock()
        if "cclsp" in cmd and "list" in cmd:
            result.returncode = 0
            result.stdout = "python\ntypescript\nrust\n"
            result.stderr = ""
        elif "cclsp" in cmd and "install" in cmd:
            result.returncode = 0
            result.stdout = "Successfully installed plugin"
            result.stderr = ""
        else:
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
        return result

    mock_subprocess_run.side_effect = mock_run
    return mock_subprocess_run


@pytest.fixture
def mock_npx_cclsp_failure(mock_subprocess_run):
    """Mock failed npx cclsp install."""
    def mock_run(cmd, *args, **kwargs):
        result = Mock()
        if "cclsp" in cmd:
            result.returncode = 1
            result.stdout = ""
            result.stderr = "Failed to install plugin"
        else:
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
        return result

    mock_subprocess_run.side_effect = mock_run
    return mock_subprocess_run


@pytest.fixture
def language_to_lsp_mapping() -> Dict[str, Dict[str, str]]:
    """Standard mapping of languages to LSP servers."""
    return {
        "python": {
            "binary": "pyright",
            "plugin": "python",
            "install_guide": "npm install -g pyright",
        },
        "typescript": {
            "binary": "typescript-language-server",
            "plugin": "typescript",
            "install_guide": "npm install -g typescript-language-server",
        },
        "javascript": {
            "binary": "typescript-language-server",
            "plugin": "typescript",
            "install_guide": "npm install -g typescript-language-server",
        },
        "rust": {
            "binary": "rust-analyzer",
            "plugin": "rust",
            "install_guide": "rustup component add rust-analyzer",
        },
        "go": {
            "binary": "gopls",
            "plugin": "go",
            "install_guide": "go install golang.org/x/tools/gopls@latest",
        },
    }


@pytest.fixture
def mock_platform_system():
    """Mock platform.system() for platform-specific tests."""
    return MagicMock(return_value="Darwin")  # Default to macOS
