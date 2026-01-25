"""Pytest configuration and fixtures for meta-delegation tests.

Provides common fixtures and utilities for all test modules.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def temp_working_dir(tmp_path):
    """Create temporary working directory for tests."""
    working_dir = tmp_path / "meta_delegation_test"
    working_dir.mkdir()
    return working_dir


@pytest.fixture
def sample_code_files(temp_working_dir):
    """Create sample code files in working directory."""
    # Create main module
    (temp_working_dir / "app.py").write_text(
        """
def main():
    \"\"\"Main application entry point.\"\"\"
    print("Hello, World!")

def process_data(data):
    \"\"\"Process input data.\"\"\"
    return data.upper()
"""
    )

    # Create utility module
    (temp_working_dir / "utils.py").write_text(
        """
def helper_function():
    \"\"\"Helper utility function.\"\"\"
    return "helper"
"""
    )

    return temp_working_dir


@pytest.fixture
def sample_test_files(temp_working_dir):
    """Create sample test files in working directory."""
    # Create test file
    (temp_working_dir / "test_app.py").write_text(
        """
import pytest
from app import main, process_data

def test_main():
    \"\"\"Test main function.\"\"\"
    assert main() is None

def test_process_data():
    \"\"\"Test data processing.\"\"\"
    assert process_data("hello") == "HELLO"
"""
    )

    return temp_working_dir


@pytest.fixture
def sample_documentation(temp_working_dir):
    """Create sample documentation files."""
    (temp_working_dir / "README.md").write_text(
        """
# Sample Project

This is a sample project for testing meta-delegation.

## Features

- Feature A
- Feature B

## Usage

```python
from app import main
main()
```
"""
    )

    (temp_working_dir / "architecture.md").write_text(
        """
# Architecture

## System Design

The system follows a modular architecture...

## Components

- App module
- Utils module
"""
    )

    return temp_working_dir


@pytest.fixture
def sample_config_files(temp_working_dir):
    """Create sample configuration files."""
    (temp_working_dir / "config.yaml").write_text(
        """
app_name: test_app
version: 1.0.0
settings:
  debug: true
  log_level: INFO
"""
    )

    (temp_working_dir / "config.json").write_text(
        """
{
  "api_key": "test_key",
  "endpoint": "http://localhost:8000"
}
"""
    )

    return temp_working_dir


@pytest.fixture
def mock_subprocess():
    """Create mock subprocess object."""
    process = Mock()
    process.pid = 12345
    process.poll.return_value = None  # Running
    process.returncode = None
    process.communicate.return_value = ("output", "")
    process.wait.return_value = 0
    return process


@pytest.fixture
def mock_platform_cli():
    """Create mock platform CLI."""
    cli = Mock()
    cli.platform_name = "claude-code"
    cli.validate_installation.return_value = True
    cli.get_version.return_value = "1.0.0"
    cli.format_prompt.return_value = "Formatted prompt"

    mock_process = Mock(pid=123)
    cli.spawn_subprocess.return_value = mock_process

    cli.parse_output.return_value = {"stdout": "output"}

    return cli


@pytest.fixture
def sample_evidence_items():
    """Create sample evidence items."""
    try:
        from amplihack.meta_delegation.evidence_collector import EvidenceItem
    except ImportError:
        # Return mock objects if module not implemented
        pytest.skip("evidence_collector not implemented")

    return [
        EvidenceItem(
            type="code_file",
            path="app.py",
            content="def main(): pass",
            excerpt="def main()...",
            size_bytes=50,
            timestamp=datetime.now(),
            metadata={"language": "python"},
        ),
        EvidenceItem(
            type="test_file",
            path="test_app.py",
            content="def test_main(): assert True",
            excerpt="def test_main()...",
            size_bytes=60,
            timestamp=datetime.now(),
            metadata={"language": "python"},
        ),
        EvidenceItem(
            type="documentation",
            path="README.md",
            content="# Project Documentation",
            excerpt="# Project...",
            size_bytes=30,
            timestamp=datetime.now(),
            metadata={"format": "markdown"},
        ),
    ]


@pytest.fixture
def sample_test_scenarios():
    """Create sample test scenarios."""
    try:
        from amplihack.meta_delegation.scenario_generator import TestScenario
    except ImportError:
        pytest.skip("scenario_generator not implemented")

    return [
        TestScenario(
            name="Valid user registration",
            category="happy_path",
            description="User registers with valid email and password",
            preconditions=["API server running", "Database available"],
            steps=[
                "Send POST request to /api/users",
                "Include valid email and password",
                "Receive response",
            ],
            expected_outcome="201 Created with user ID",
            priority="high",
            tags=["api", "auth", "registration"],
        ),
        TestScenario(
            name="Duplicate email registration",
            category="error_handling",
            description="Attempt to register with existing email",
            preconditions=["User with email exists"],
            steps=[
                "Send POST request with duplicate email",
                "Receive error response",
            ],
            expected_outcome="409 Conflict with error message",
            priority="high",
            tags=["api", "auth", "validation"],
        ),
        TestScenario(
            name="Maximum username length",
            category="boundary_conditions",
            description="Register with username at max length",
            preconditions=["API server running"],
            steps=[
                "Generate 255 character username",
                "Send registration request",
            ],
            expected_outcome="201 Created or 400 with validation error",
            priority="medium",
            tags=["api", "validation", "boundary"],
        ),
    ]


@pytest.fixture
def execution_log_with_success():
    """Sample execution log showing successful completion."""
    return """
Starting task execution...
[INFO] Initializing modules
[INFO] Creating files:
  - app.py
  - test_app.py
  - README.md
[INFO] Running tests...
PASS test_app.py::test_main
PASS test_app.py::test_process_data
All tests passed (2/2)
[SUCCESS] Task completed successfully
"""


@pytest.fixture
def execution_log_with_failure():
    """Sample execution log showing test failures."""
    return """
Starting task execution...
[INFO] Creating files...
[INFO] Running tests...
FAIL test_app.py::test_main - AssertionError
PASS test_app.py::test_process_data
[ERROR] 1 test failed
Task completed with errors
"""


@pytest.fixture
def sample_goal_and_criteria():
    """Sample goal and success criteria for testing."""
    return {
        "goal": """
Create a user authentication API with the following features:
- User registration endpoint
- Login endpoint with JWT tokens
- Logout endpoint
- Token refresh endpoint
""",
        "success_criteria": """
- POST /api/register endpoint accepts email and password
- POST /api/login returns JWT token
- POST /api/logout invalidates token
- POST /api/refresh refreshes expired token
- All endpoints have tests
- Tests pass
- README documents API usage
""",
    }


@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Cleanup temporary files after each test."""
    yield
    # Cleanup happens automatically with tmp_path fixture


@pytest.fixture
def mock_persona_strategy():
    """Create mock persona strategy."""
    try:
        from amplihack.meta_delegation.persona import PersonaStrategy
    except ImportError:
        pytest.skip("persona module not implemented")

    return PersonaStrategy(
        name="test_persona",
        communication_style="direct",
        thoroughness_level="balanced",
        evidence_collection_priority=["code_file", "test_file", "documentation"],
        prompt_template="Goal: {goal}\nCriteria: {success_criteria}",
    )


@pytest.fixture
def mock_evaluation_result():
    """Create mock evaluation result."""
    try:
        from amplihack.meta_delegation.success_evaluator import EvaluationResult
    except ImportError:
        pytest.skip("success_evaluator not implemented")

    return EvaluationResult(
        score=85,
        notes="All major criteria met. Minor documentation gaps.",
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires multiple modules)"
    )
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test (slow)")
    config.addinivalue_line(
        "markers", "requires_platform: mark test as requiring specific platform CLI"
    )
