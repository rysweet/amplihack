"""Tests for quality configuration."""

import os
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from amplihack.quality.config import QualityConfig


class TestQualityConfig:
    """Tests for QualityConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = QualityConfig()

        assert config.enabled is True
        assert config.fast_mode is True
        assert config.fast_mode_timeout == 5
        assert config.full_mode_timeout == 30
        assert config.validators == ["python", "shell", "markdown", "yaml", "json"]
        assert "**/__pycache__/**" in config.exclude
        assert config.severity == ["error", "warning"]

    def test_timeout_property_fast_mode(self):
        """Test timeout property in fast mode."""
        config = QualityConfig(fast_mode=True, fast_mode_timeout=10)
        assert config.timeout == 10

    def test_timeout_property_full_mode(self):
        """Test timeout property in full mode."""
        config = QualityConfig(fast_mode=False, full_mode_timeout=30)
        assert config.timeout == 30

    def test_env_override_enabled(self):
        """Test environment variable override for enabled."""
        config = QualityConfig(enabled=True)
        os.environ["AMPLIHACK_QUALITY_ENABLED"] = "false"
        try:
            config._apply_env_overrides()
            assert config.enabled is False
        finally:
            del os.environ["AMPLIHACK_QUALITY_ENABLED"]

    def test_env_override_fast_mode(self):
        """Test environment variable override for fast_mode."""
        config = QualityConfig(fast_mode=False)
        os.environ["AMPLIHACK_QUALITY_FAST_MODE"] = "true"
        try:
            config._apply_env_overrides()
            assert config.fast_mode is True
        finally:
            del os.environ["AMPLIHACK_QUALITY_FAST_MODE"]

    def test_env_override_timeouts(self):
        """Test environment variable overrides for timeouts."""
        config = QualityConfig()
        os.environ["AMPLIHACK_QUALITY_FAST_TIMEOUT"] = "10"
        os.environ["AMPLIHACK_QUALITY_FULL_TIMEOUT"] = "60"
        try:
            config._apply_env_overrides()
            assert config.fast_mode_timeout == 10
            assert config.full_mode_timeout == 60
        finally:
            del os.environ["AMPLIHACK_QUALITY_FAST_TIMEOUT"]
            del os.environ["AMPLIHACK_QUALITY_FULL_TIMEOUT"]
