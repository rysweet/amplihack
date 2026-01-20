"""Unit tests for OverrideManager."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest


def test_imports():
    """Test that override manager imports work."""
    from amplifier_hook_tool_gate import OverrideManager

    assert OverrideManager is not None


def test_no_override_file():
    """Test behavior when no override file exists."""
    from amplifier_hook_tool_gate import OverrideManager

    # Temporarily override the path to non-existent location
    original_file = OverrideManager.OVERRIDE_FILE
    try:
        OverrideManager.OVERRIDE_FILE = Path("/tmp/nonexistent_override_test.json")

        active, reason = OverrideManager.is_override_active()
        assert not active
        assert "no override file" in reason.lower()
    finally:
        OverrideManager.OVERRIDE_FILE = original_file


def test_valid_override():
    """Test that valid override is recognized."""
    from amplifier_hook_tool_gate import OverrideManager

    with tempfile.TemporaryDirectory() as tmpdir:
        override_file = Path(tmpdir) / "override.json"

        # Create valid override
        override_data = {
            "enabled": True,
            "reason": "Emergency hotfix for production",
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=30)).isoformat(),
            "created_by": "user",
        }

        with open(override_file, "w") as f:
            json.dump(override_data, f)

        # Temporarily override the path
        original_file = OverrideManager.OVERRIDE_FILE
        try:
            OverrideManager.OVERRIDE_FILE = override_file

            active, reason = OverrideManager.is_override_active()
            assert active
            assert reason == "Emergency hotfix for production"
        finally:
            OverrideManager.OVERRIDE_FILE = original_file


def test_expired_override():
    """Test that expired override is cleaned up."""
    from amplifier_hook_tool_gate import OverrideManager

    with tempfile.TemporaryDirectory() as tmpdir:
        override_file = Path(tmpdir) / "override.json"

        # Create expired override
        override_data = {
            "enabled": True,
            "reason": "Old override",
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "expires_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "created_by": "user",
        }

        with open(override_file, "w") as f:
            json.dump(override_data, f)

        # Temporarily override the path
        original_file = OverrideManager.OVERRIDE_FILE
        try:
            OverrideManager.OVERRIDE_FILE = override_file

            active, reason = OverrideManager.is_override_active()
            assert not active
            assert "expired" in reason.lower()

            # File should be deleted
            assert not override_file.exists()
        finally:
            OverrideManager.OVERRIDE_FILE = original_file


def test_invalid_override_source():
    """Test that non-user override is rejected."""
    from amplifier_hook_tool_gate import OverrideManager

    with tempfile.TemporaryDirectory() as tmpdir:
        override_file = Path(tmpdir) / "override.json"

        # Create override with wrong source
        override_data = {
            "enabled": True,
            "reason": "AI attempted override",
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=30)).isoformat(),
            "created_by": "ai",  # Wrong!
        }

        with open(override_file, "w") as f:
            json.dump(override_data, f)

        # Temporarily override the path
        original_file = OverrideManager.OVERRIDE_FILE
        try:
            OverrideManager.OVERRIDE_FILE = override_file

            active, reason = OverrideManager.is_override_active()
            assert not active
            assert "invalid override source" in reason.lower()
        finally:
            OverrideManager.OVERRIDE_FILE = original_file


def test_override_usage_recording():
    """Test that override usage is audited."""
    from amplifier_hook_tool_gate import OverrideManager

    with tempfile.TemporaryDirectory() as tmpdir:
        audit_file = Path(tmpdir) / "audit.jsonl"

        # Temporarily override the audit path
        original_audit = OverrideManager.AUDIT_FILE
        try:
            OverrideManager.AUDIT_FILE = audit_file

            # Record usage
            OverrideManager.record_override_usage(
                "write_file", {"session_id": "test_123", "override_reason": "Emergency"}
            )

            # Verify audit file created
            assert audit_file.exists()

            # Verify content
            with open(audit_file) as f:
                lines = f.readlines()
            assert len(lines) == 1

            entry = json.loads(lines[0])
            assert entry["tool_name"] == "write_file"
            assert entry["session_id"] == "test_123"
        finally:
            OverrideManager.AUDIT_FILE = original_audit


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
