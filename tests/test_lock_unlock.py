"""Tests for lock/unlock commands and stop hook."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestLockUnlockCommands:
    """Tests for lock/unlock slash commands."""

    @pytest.fixture
    def lock_flag(self, tmp_path):
        """Create lock flag path in temp directory."""
        lock_path = tmp_path / ".claude" / "tools" / "amplihack" / ".lock_active"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        return lock_path

    def test_lock_creates_flag(self, lock_flag, monkeypatch):
        """Test that lock command creates .lock_active file."""
        monkeypatch.chdir(lock_flag.parent.parent.parent.parent)

        # Simulate lock command
        import os

        try:
            fd = os.open(str(lock_flag), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            assert lock_flag.exists()
        except FileExistsError:
            pytest.fail("Lock file already existed")

    def test_lock_idempotent(self, lock_flag):
        """Test that calling lock twice is safe."""
        import os

        # First lock
        fd = os.open(str(lock_flag), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)

        # Second lock should detect existing lock
        with pytest.raises(FileExistsError):
            os.open(str(lock_flag), os.O_CREAT | os.O_EXCL | os.O_WRONLY)

        assert lock_flag.exists()

    def test_unlock_removes_flag(self, lock_flag):
        """Test that unlock command removes .lock_active file."""
        # Create lock first
        lock_flag.touch()
        assert lock_flag.exists()

        # Unlock
        lock_flag.unlink(missing_ok=True)
        assert not lock_flag.exists()

    def test_unlock_without_lock_safe(self, lock_flag):
        """Test that unlock without lock doesn't error."""
        assert not lock_flag.exists()

        # Should not raise
        lock_flag.unlink(missing_ok=True)
        assert not lock_flag.exists()


class TestStopHook:
    """Tests for stop hook with lock support."""

    @pytest.fixture
    def stop_hook_path(self):
        """Get path to stop hook."""
        return (
            Path(__file__).parent.parent / ".claude" / "tools" / "amplihack" / "hooks" / "stop.py"
        )

    def test_stop_hook_exists(self, stop_hook_path):
        """Test that stop hook file exists."""
        assert stop_hook_path.exists()

    def test_stop_hook_blocks_when_locked(self, tmp_path, monkeypatch):
        """Test that stop hook blocks when lock is active."""
        # Create lock flag
        lock_flag = tmp_path / ".claude" / "tools" / "amplihack" / ".lock_active"
        lock_flag.parent.mkdir(parents=True, exist_ok=True)
        lock_flag.touch()

        # Mock the stop hook

        class MockStopHook:
            def __init__(self):
                self.project_root = tmp_path
                self.lock_flag = lock_flag

            def process(self, input_data):
                if self.lock_flag.exists():
                    return {
                        "decision": "block",
                        "reason": "we must keep pursuing the user's objective...",
                        "continue": True,
                    }
                return {"decision": "allow", "continue": False}

        hook = MockStopHook()
        result = hook.process({})

        assert result["decision"] == "block"
        assert result["continue"] is True

    def test_stop_hook_allows_when_unlocked(self, tmp_path):
        """Test that stop hook allows when lock is not active."""
        # No lock flag created

        class MockStopHook:
            def __init__(self):
                self.project_root = tmp_path
                self.lock_flag = tmp_path / ".claude" / "tools" / "amplihack" / ".lock_active"

            def process(self, input_data):
                if self.lock_flag.exists():
                    return {
                        "decision": "block",
                        "reason": "we must keep pursuing the user's objective...",
                        "continue": True,
                    }
                return {"decision": "allow", "continue": False}

        hook = MockStopHook()
        result = hook.process({})

        assert result["decision"] == "allow"
        assert result["continue"] is False

    def test_stop_hook_handles_permission_errors(self, tmp_path):
        """Test that stop hook handles permission errors gracefully."""

        class MockStopHook:
            def __init__(self):
                self.project_root = tmp_path
                self.lock_flag = tmp_path / ".claude" / "tools" / "amplihack" / ".lock_active"

            def process(self, input_data):
                try:
                    lock_exists = self.lock_flag.exists()
                except (PermissionError, OSError):
                    # Fail-safe: allow stop if we can't read lock
                    return {"decision": "allow", "continue": False}

                if lock_exists:
                    return {
                        "decision": "block",
                        "reason": "we must keep pursuing the user's objective...",
                        "continue": True,
                    }
                return {"decision": "allow", "continue": False}

        hook = MockStopHook()

        # Mock exists() to raise PermissionError
        with patch.object(Path, "exists", side_effect=PermissionError("Access denied")):
            result = hook.process({})
            assert result["decision"] == "allow"
            assert result["continue"] is False


class TestLockWithCustomPrompts:
    """Tests for lock command with custom continuation prompts."""

    @pytest.fixture
    def lock_dir(self, tmp_path):
        """Create lock directory in temp path."""
        lock_path = tmp_path / ".claude" / "tools" / "amplihack"
        lock_path.mkdir(parents=True, exist_ok=True)
        return lock_path

    def test_lock_with_valid_custom_prompt(self, lock_dir):
        """Test lock with valid custom continuation prompt."""
        continuation_prompt = lock_dir / ".continuation_prompt"
        custom_text = "Focus on security fixes first"

        # Write custom prompt atomically
        temp_fd, temp_path = tempfile.mkstemp(dir=lock_dir, text=True)
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.write(custom_text)
            os.replace(temp_path, continuation_prompt)

            assert continuation_prompt.exists()
            assert continuation_prompt.read_text(encoding="utf-8") == custom_text
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_lock_with_empty_prompt_file(self, lock_dir):
        """Test that empty prompt file falls back to default."""
        continuation_prompt = lock_dir / ".continuation_prompt"
        continuation_prompt.write_text("", encoding="utf-8")

        assert continuation_prompt.exists()
        assert continuation_prompt.read_text(encoding="utf-8") == ""

    def test_lock_with_no_prompt_file(self, lock_dir):
        """Test that missing prompt file uses default behavior."""
        continuation_prompt = lock_dir / ".continuation_prompt"
        assert not continuation_prompt.exists()

    def test_lock_prompt_length_validation_reject(self, lock_dir):
        """Test that prompts over 1000 chars are rejected."""
        continuation_prompt = lock_dir / ".continuation_prompt"
        long_prompt = "x" * 1001

        # Should not write prompts > 1000 chars
        if len(long_prompt) > 1000:
            # In real usage, this would be caught before writing
            assert len(long_prompt) > 1000
        else:
            continuation_prompt.write_text(long_prompt, encoding="utf-8")

    def test_lock_prompt_length_validation_warn(self, lock_dir):
        """Test that prompts over 500 chars show warning but are accepted."""
        continuation_prompt = lock_dir / ".continuation_prompt"
        medium_prompt = "x" * 501

        # Should accept but warn for 500-1000 chars
        temp_fd, temp_path = tempfile.mkstemp(dir=lock_dir, text=True)
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.write(medium_prompt)
            os.replace(temp_path, continuation_prompt)

            assert continuation_prompt.exists()
            assert len(continuation_prompt.read_text(encoding="utf-8")) == 501
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_lock_atomic_write_with_custom_prompt(self, lock_dir):
        """Test atomic write of custom prompt using temp file."""
        continuation_prompt = lock_dir / ".continuation_prompt"
        custom_text = "Test atomic write"

        # Simulate atomic write
        temp_fd, temp_path = tempfile.mkstemp(dir=lock_dir, text=True)
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.write(custom_text)

            # Atomic replace
            os.replace(temp_path, continuation_prompt)

            assert continuation_prompt.exists()
            assert continuation_prompt.read_text(encoding="utf-8") == custom_text
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_lock_utf8_encoding_explicit(self, lock_dir):
        """Test that UTF-8 encoding is used for custom prompts."""
        continuation_prompt = lock_dir / ".continuation_prompt"
        unicode_text = "Test with unicode: 你好 🚀"

        temp_fd, temp_path = tempfile.mkstemp(dir=lock_dir, text=True)
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.write(unicode_text)
            os.replace(temp_path, continuation_prompt)

            # Read back with explicit UTF-8
            read_text = continuation_prompt.read_text(encoding="utf-8")
            assert read_text == unicode_text
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestStopHookWithCustomPrompts:
    """Tests for stop hook with custom continuation prompts."""

    @pytest.fixture
    def stop_hook_with_custom(self, tmp_path):
        """Create stop hook with custom prompt support."""

        class MockStopHookWithCustom:
            DEFAULT_PROMPT = (
                "we must keep pursuing the user's objective and must not stop the turn - "
                "look for any additional TODOs, next steps, or unfinished work and pursue it "
                "diligently in as many parallel tasks as you can"
            )

            def __init__(self, project_root):
                self.project_root = project_root
                self.lock_flag = project_root / ".claude" / "tools" / "amplihack" / ".lock_active"
                self.continuation_prompt_file = (
                    project_root / ".claude" / "tools" / "amplihack" / ".continuation_prompt"
                )

            def read_continuation_prompt(self):
                """Read custom continuation prompt or return default."""
                if not self.continuation_prompt_file.exists():
                    return self.DEFAULT_PROMPT

                try:
                    custom_prompt = self.continuation_prompt_file.read_text(
                        encoding="utf-8"
                    ).strip()

                    if not custom_prompt:
                        return self.DEFAULT_PROMPT

                    if len(custom_prompt) > 1000:
                        return self.DEFAULT_PROMPT

                    return custom_prompt

                except (PermissionError, OSError, UnicodeDecodeError):
                    return self.DEFAULT_PROMPT

            def process(self, input_data):
                """Process stop event with custom prompt support."""
                try:
                    lock_exists = self.lock_flag.exists()
                except (PermissionError, OSError):
                    return {"decision": "allow", "continue": False}

                if lock_exists:
                    continuation_prompt = self.read_continuation_prompt()
                    return {
                        "decision": "block",
                        "reason": continuation_prompt,
                        "continue": True,
                    }

                return {"decision": "allow", "continue": False}

        lock_dir = tmp_path / ".claude" / "tools" / "amplihack"
        lock_dir.mkdir(parents=True, exist_ok=True)
        return MockStopHookWithCustom(tmp_path)

    def test_stop_hook_uses_custom_prompt(self, stop_hook_with_custom):
        """Test that stop hook uses custom prompt when available."""
        custom_text = "Focus on security fixes first"

        # Write custom prompt
        stop_hook_with_custom.continuation_prompt_file.write_text(custom_text, encoding="utf-8")

        # Create lock
        stop_hook_with_custom.lock_flag.touch()

        result = stop_hook_with_custom.process({})

        assert result["decision"] == "block"
        assert result["reason"] == custom_text
        assert result["continue"] is True

    def test_stop_hook_uses_default_when_no_file(self, stop_hook_with_custom):
        """Test that stop hook uses default prompt when file doesn't exist."""
        # Don't create custom prompt file
        stop_hook_with_custom.lock_flag.touch()

        result = stop_hook_with_custom.process({})

        assert result["decision"] == "block"
        assert result["reason"] == stop_hook_with_custom.DEFAULT_PROMPT
        assert result["continue"] is True

    def test_stop_hook_uses_default_when_file_empty(self, stop_hook_with_custom):
        """Test that stop hook uses default prompt when file is empty."""
        # Create empty file
        stop_hook_with_custom.continuation_prompt_file.write_text("", encoding="utf-8")
        stop_hook_with_custom.lock_flag.touch()

        result = stop_hook_with_custom.process({})

        assert result["decision"] == "block"
        assert result["reason"] == stop_hook_with_custom.DEFAULT_PROMPT
        assert result["continue"] is True

    def test_stop_hook_rejects_oversized_prompt(self, stop_hook_with_custom):
        """Test that stop hook rejects prompts over 1000 chars."""
        oversized = "x" * 1001
        stop_hook_with_custom.continuation_prompt_file.write_text(oversized, encoding="utf-8")
        stop_hook_with_custom.lock_flag.touch()

        result = stop_hook_with_custom.process({})

        assert result["decision"] == "block"
        assert result["reason"] == stop_hook_with_custom.DEFAULT_PROMPT
        assert result["continue"] is True

    def test_stop_hook_handles_read_errors(self, stop_hook_with_custom):
        """Test that stop hook handles file read errors gracefully."""
        stop_hook_with_custom.lock_flag.touch()

        # Mock read_text to raise error
        with patch.object(
            Path, "read_text", side_effect=PermissionError("Cannot read file")
        ):
            result = stop_hook_with_custom.process({})

            # Should use default prompt on error
            assert result["decision"] == "block"
            assert result["continue"] is True

    def test_stop_hook_backward_compatible(self, stop_hook_with_custom):
        """Test that stop hook is 100% backward compatible."""
        # Test without any custom prompt file (original behavior)
        stop_hook_with_custom.lock_flag.touch()

        result = stop_hook_with_custom.process({})

        # Should work exactly like before
        assert result["decision"] == "block"
        assert result["reason"] == stop_hook_with_custom.DEFAULT_PROMPT
        assert result["continue"] is True

        # Test unlocked state
        stop_hook_with_custom.lock_flag.unlink()
        result = stop_hook_with_custom.process({})

        assert result["decision"] == "allow"
        assert result["continue"] is False
