"""Shared fixtures for auto-ultrathink tests."""

import sys
from pathlib import Path
from typing import Any

import pytest

# Add auto_ultrathink module to Python path for direct imports
AUTO_ULTRATHINK_PATH = Path(__file__).parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks" / "auto_ultrathink"
if AUTO_ULTRATHINK_PATH.exists():
    sys.path.insert(0, str(AUTO_ULTRATHINK_PATH))


@pytest.fixture
def setup_test_env(tmp_path, monkeypatch):
    """Setup test environment with temporary preferences and log files."""
    # Create temporary preferences file
    prefs_file = tmp_path / "prefs.md"
    prefs_file.write_text(
        """
# User Preferences

## Auto-UltraThink Configuration

```yaml
auto_ultrathink:
  mode: "ask"
  confidence_threshold: 0.80
  excluded_patterns: []
```
"""
    )

    # Create temporary log directory
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    # Set environment variables
    monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))
    monkeypatch.setenv("AMPLIHACK_LOG_DIR", str(log_dir))

    return {
        "prefs_file": prefs_file,
        "log_dir": log_dir,
        "tmp_path": tmp_path,
    }


@pytest.fixture
def create_preference_file(tmp_path):
    """Factory fixture to create preference files with custom settings."""

    def _create(
        mode: str = "ask",
        threshold: float = 0.80,
        excluded_patterns: list = None,
    ) -> Path:
        if excluded_patterns is None:
            excluded_patterns = []

        prefs_file = tmp_path / f"prefs_{mode}.md"
        prefs_file.write_text(
            f"""
# User Preferences

## Auto-UltraThink Configuration

```yaml
auto_ultrathink:
  mode: "{mode}"
  confidence_threshold: {threshold}
  excluded_patterns: {excluded_patterns}
```
"""
        )
        return prefs_file

    return _create


@pytest.fixture
def create_test_classification():
    """Factory fixture to create Classification objects for testing."""
    from dataclasses import dataclass

    @dataclass
    class Classification:
        needs_ultrathink: bool
        confidence: float
        reason: str
        matched_patterns: list

    def _create(
        needs_ultrathink: bool = True,
        confidence: float = 0.90,
        reason: str = "Test classification",
        matched_patterns: list = None,
    ) -> Classification:
        if matched_patterns is None:
            matched_patterns = ["test_pattern"]

        return Classification(
            needs_ultrathink=needs_ultrathink,
            confidence=confidence,
            reason=reason,
            matched_patterns=matched_patterns,
        )

    return _create


@pytest.fixture
def create_test_preference():
    """Factory fixture to create AutoUltraThinkPreference objects for testing."""
    from dataclasses import dataclass

    @dataclass
    class AutoUltraThinkPreference:
        mode: str
        confidence_threshold: float
        excluded_patterns: list

    def _create(
        mode: str = "ask",
        confidence_threshold: float = 0.80,
        excluded_patterns: list = None,
    ) -> AutoUltraThinkPreference:
        if excluded_patterns is None:
            excluded_patterns = []

        return AutoUltraThinkPreference(
            mode=mode,
            confidence_threshold=confidence_threshold,
            excluded_patterns=excluded_patterns,
        )

    return _create


@pytest.fixture
def create_test_decision():
    """Factory fixture to create Decision objects for testing."""
    from dataclasses import dataclass
    from enum import Enum

    class Action(Enum):
        INVOKE = "invoke"
        ASK = "ask"
        SKIP = "skip"

    @dataclass
    class Decision:
        action: Action
        reason: str
        classification: Any
        preference: Any

    def _create(
        action: str = "skip",
        reason: str = "Test reason",
        classification: Any = None,
        preference: Any = None,
    ) -> Decision:
        return Decision(
            action=Action[action.upper()],
            reason=reason,
            classification=classification,
            preference=preference,
        )

    return _create


@pytest.fixture
def create_test_result():
    """Factory fixture to create ExecutionResult objects for testing."""
    from dataclasses import dataclass

    class Action:
        INVOKE = "invoke"
        ASK = "ask"
        SKIP = "skip"

    @dataclass
    class ExecutionResult:
        modified_prompt: str
        action_taken: str
        user_choice: Any
        metadata: dict

    def _create(
        modified_prompt: str = "test prompt",
        action_taken: str = "skip",
        user_choice: Any = None,
        metadata: dict = None,
    ) -> ExecutionResult:
        if metadata is None:
            metadata = {}

        return ExecutionResult(
            modified_prompt=modified_prompt,
            action_taken=action_taken,
            user_choice=user_choice,
            metadata=metadata,
        )

    return _create


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock logger to prevent actual file writes during tests."""
    logged_entries = []

    def mock_log(*args, **kwargs):
        logged_entries.append({"args": args, "kwargs": kwargs})

    # This will be used by tests to verify logging was called
    return {"entries": logged_entries, "mock_fn": mock_log}


@pytest.fixture
def sample_prompts():
    """Sample prompts for testing classification."""
    return {
        "multi_file_feature": [
            "Add authentication to the API",
            "Implement user dashboard with database",
            "Create payment processing system",
            "Build REST API with PostgreSQL backend",
        ],
        "refactoring": [
            "Refactor the auth module",
            "Redesign the data layer",
            "Restructure project for modularity",
        ],
        "questions": [
            "What is UltraThink?",
            "How do I use the debugger?",
            "Explain the architecture",
            "Why is this failing?",
        ],
        "slash_commands": [
            "/analyze src/",
            "/ultrathink Add feature",
            "/fix import errors",
            "/improve code quality",
        ],
        "simple_edits": [
            "Change the variable name to X",
            "Update the comment in file.py",
            "Fix typo in README",
        ],
        "read_operations": [
            "Show me the config file",
            "List all the agents",
            "Find instances of function X",
            "Display the logs",
        ],
    }
