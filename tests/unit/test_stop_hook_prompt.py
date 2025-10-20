"""
Unit tests for StopHook.read_continuation_prompt() method.

Tests custom prompt reading including:
- File existence checking
- Content validation
- Length constraints
- Error handling
- Unicode handling
"""


def test_unit_prompt_001_no_custom_prompt_file_exists(stop_hook):
    """UNIT-PROMPT-001: No custom prompt file exists."""
    # Expected: Returns DEFAULT_CONTINUATION_PROMPT
    from stop import DEFAULT_CONTINUATION_PROMPT

    result = stop_hook.read_continuation_prompt()

    assert result == DEFAULT_CONTINUATION_PROMPT

    # Verify log message
    log_content = stop_hook.log_file.read_text()
    assert "No custom continuation prompt file - using default" in log_content


def test_unit_prompt_002_custom_prompt_file_exists_with_valid_content(stop_hook, custom_prompt):
    """UNIT-PROMPT-002: Custom prompt file exists with valid content."""
    # Create custom prompt
    content = "Continue working on tasks"
    custom_prompt(content)

    # Expected: Returns the custom content
    result = stop_hook.read_continuation_prompt()

    assert result == content

    # Verify log message includes character count
    log_content = stop_hook.log_file.read_text()
    assert f"Using custom continuation prompt ({len(content)} chars)" in log_content


def test_unit_prompt_003_custom_prompt_file_is_empty(stop_hook, custom_prompt):
    """UNIT-PROMPT-003: Custom prompt file is empty."""
    # Create empty prompt file
    custom_prompt("   \n\t  ")  # Only whitespace

    from stop import DEFAULT_CONTINUATION_PROMPT

    # Expected: Returns DEFAULT_CONTINUATION_PROMPT
    result = stop_hook.read_continuation_prompt()

    assert result == DEFAULT_CONTINUATION_PROMPT

    # Verify log message
    log_content = stop_hook.log_file.read_text()
    assert "Custom continuation prompt file is empty - using default" in log_content


def test_unit_prompt_004_custom_prompt_exceeds_1000_characters(stop_hook, custom_prompt):
    """UNIT-PROMPT-004: Custom prompt exceeds 1000 characters."""
    # Create prompt with 1001 characters
    long_prompt = "a" * 1001
    custom_prompt(long_prompt)

    from stop import DEFAULT_CONTINUATION_PROMPT

    # Expected: Returns DEFAULT_CONTINUATION_PROMPT
    result = stop_hook.read_continuation_prompt()

    assert result == DEFAULT_CONTINUATION_PROMPT

    # Verify log message
    log_content = stop_hook.log_file.read_text()
    assert "Custom prompt too long" in log_content
    assert "1001 chars" in log_content
    assert "WARNING" in log_content


def test_unit_prompt_005_custom_prompt_between_500_1000_characters(stop_hook, custom_prompt):
    """UNIT-PROMPT-005: Custom prompt between 500-1000 characters."""
    # Create prompt with 750 characters
    medium_prompt = "b" * 750
    custom_prompt(medium_prompt)

    # Expected: Returns the 750 character string with warning
    result = stop_hook.read_continuation_prompt()

    assert result == medium_prompt

    # Verify log message shows warning but uses the prompt
    log_content = stop_hook.log_file.read_text()
    assert "Custom prompt is long (750 chars)" in log_content
    assert "WARNING" in log_content
    assert "consider shortening" in log_content


def test_unit_prompt_006_permission_error_reading_custom_prompt(stop_hook, monkeypatch):
    """UNIT-PROMPT-006: Permission error reading custom prompt."""
    # Create prompt file
    stop_hook.continuation_prompt_file.touch()

    # Mock read_text to raise PermissionError
    def mock_read_text(*args, **kwargs):
        raise PermissionError("Access denied")

    monkeypatch.setattr(stop_hook.continuation_prompt_file, "read_text", mock_read_text)

    from stop import DEFAULT_CONTINUATION_PROMPT

    # Expected: Returns DEFAULT_CONTINUATION_PROMPT
    result = stop_hook.read_continuation_prompt()

    assert result == DEFAULT_CONTINUATION_PROMPT

    # Verify log message
    log_content = stop_hook.log_file.read_text()
    assert "Error reading custom prompt" in log_content
    assert "using default" in log_content


def test_unit_prompt_007_oserror_reading_custom_prompt(stop_hook, monkeypatch):
    """UNIT-PROMPT-007: OSError reading custom prompt."""
    # Create prompt file
    stop_hook.continuation_prompt_file.touch()

    # Mock read_text to raise OSError
    def mock_read_text(*args, **kwargs):
        raise OSError("I/O error")

    monkeypatch.setattr(stop_hook.continuation_prompt_file, "read_text", mock_read_text)

    from stop import DEFAULT_CONTINUATION_PROMPT

    # Expected: Returns DEFAULT_CONTINUATION_PROMPT
    result = stop_hook.read_continuation_prompt()

    assert result == DEFAULT_CONTINUATION_PROMPT

    # Verify log message
    log_content = stop_hook.log_file.read_text()
    assert "Error reading custom prompt" in log_content
    assert "using default" in log_content


def test_unit_prompt_008_unicode_decode_error_reading_custom_prompt(stop_hook, monkeypatch):
    """UNIT-PROMPT-008: Unicode decode error reading custom prompt."""
    # Create prompt file
    stop_hook.continuation_prompt_file.touch()

    # Mock read_text to raise UnicodeDecodeError
    def mock_read_text(*args, **kwargs):
        raise UnicodeDecodeError("utf-8", b"\xff\xff", 0, 1, "invalid start byte")

    monkeypatch.setattr(stop_hook.continuation_prompt_file, "read_text", mock_read_text)

    from stop import DEFAULT_CONTINUATION_PROMPT

    # Expected: Returns DEFAULT_CONTINUATION_PROMPT
    result = stop_hook.read_continuation_prompt()

    assert result == DEFAULT_CONTINUATION_PROMPT

    # Verify log message
    log_content = stop_hook.log_file.read_text()
    assert "Error reading custom prompt" in log_content
    assert "using default" in log_content


def test_unit_prompt_009_custom_prompt_with_special_characters(stop_hook, custom_prompt):
    """UNIT-PROMPT-009: Custom prompt with special characters."""
    # Create prompt with Unicode, newlines, quotes
    special_prompt = 'Continue with "quoted text" and\nnewlines\t日本語'
    custom_prompt(special_prompt)

    # Expected: Returns the exact content (stripped)
    result = stop_hook.read_continuation_prompt()

    # Should match the stripped version
    assert result == special_prompt.strip()
    assert "日本語" in result
    assert '"quoted text"' in result
