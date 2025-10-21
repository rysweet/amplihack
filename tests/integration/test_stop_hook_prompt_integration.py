"""
Integration tests for custom prompt integration.

Tests custom prompt file lifecycle and content changes.
"""

import json


def test_integ_prompt_001_default_to_custom_prompt_transition(
    captured_subprocess, temp_project_root
):
    """INTEG-PROMPT-001: Default prompt to custom prompt transition."""
    input_data = {"session_id": "test"}

    # Create lock file
    lock_file = temp_project_root / ".claude/tools/amplihack/.lock_active"
    lock_file.touch()

    # Step 1: Execute with no custom prompt file
    result1 = captured_subprocess(input_data, lock_active=True)
    assert result1.returncode == 0
    output1 = json.loads(result1.stdout)
    assert output1["decision"] == "block"
    # Should use default prompt
    assert "user's objective" in output1["reason"]
    assert "TODOs" in output1["reason"]

    # Step 2: Create custom prompt file
    prompt_file = temp_project_root / ".claude/tools/amplihack/.continuation_prompt"
    prompt_file.write_text("Custom work prompt", encoding="utf-8")

    # Step 3: Execute again
    result2 = captured_subprocess(input_data, lock_active=True)
    assert result2.returncode == 0
    output2 = json.loads(result2.stdout)
    assert output2["decision"] == "block"
    # Should use custom prompt
    assert output2["reason"] == "Custom work prompt"


def test_integ_prompt_002_custom_prompt_file_updated_during_execution(
    captured_subprocess, temp_project_root
):
    """INTEG-PROMPT-002: Custom prompt file updated during execution."""
    input_data = {"session_id": "test"}

    # Create lock file
    lock_file = temp_project_root / ".claude/tools/amplihack/.lock_active"
    lock_file.touch()

    # Step 1: Create custom prompt "Version 1"
    prompt_file = temp_project_root / ".claude/tools/amplihack/.continuation_prompt"
    prompt_file.write_text("Version 1", encoding="utf-8")

    # Step 2: Execute hook - verify uses "Version 1"
    result1 = captured_subprocess(input_data, lock_active=True)
    assert result1.returncode == 0
    output1 = json.loads(result1.stdout)
    assert output1["reason"] == "Version 1"

    # Step 3: Update prompt to "Version 2"
    prompt_file.write_text("Version 2", encoding="utf-8")

    # Step 4: Execute hook - verify uses "Version 2"
    result2 = captured_subprocess(input_data, lock_active=True)
    assert result2.returncode == 0
    output2 = json.loads(result2.stdout)
    assert output2["reason"] == "Version 2"


def test_integ_prompt_003_custom_prompt_file_deleted_during_lock_active(
    captured_subprocess, temp_project_root
):
    """INTEG-PROMPT-003: Custom prompt file deleted during lock active."""
    input_data = {"session_id": "test"}

    # Step 1: Create lock and custom prompt
    lock_file = temp_project_root / ".claude/tools/amplihack/.lock_active"
    lock_file.touch()

    prompt_file = temp_project_root / ".claude/tools/amplihack/.continuation_prompt"
    prompt_file.write_text("Custom prompt", encoding="utf-8")

    # Step 2: Execute hook - verify uses custom
    result1 = captured_subprocess(input_data, lock_active=True)
    assert result1.returncode == 0
    output1 = json.loads(result1.stdout)
    assert output1["reason"] == "Custom prompt"

    # Step 3: Delete custom prompt
    prompt_file.unlink()

    # Step 4: Execute hook - verify falls back to default
    result2 = captured_subprocess(input_data, lock_active=True)
    assert result2.returncode == 0
    output2 = json.loads(result2.stdout)
    # Should use default prompt
    assert "user's objective" in output2["reason"]
    assert "TODOs" in output2["reason"]


def test_integ_prompt_004_custom_prompt_with_edge_case_content(
    captured_subprocess, temp_project_root
):
    """INTEG-PROMPT-004: Custom prompt with edge case content."""
    input_data = {"session_id": "test"}

    # Create lock file
    lock_file = temp_project_root / ".claude/tools/amplihack/.lock_active"
    lock_file.touch()

    # Create prompt with special content
    prompt_file = temp_project_root / ".claude/tools/amplihack/.continuation_prompt"

    # Test 1: Very long line (but under 1000 char limit)
    long_line = "a" * 500
    prompt_file.write_text(long_line, encoding="utf-8")

    result1 = captured_subprocess(input_data, lock_active=True)
    assert result1.returncode == 0
    output1 = json.loads(result1.stdout)
    assert output1["reason"] == long_line

    # Test 2: Special Unicode
    unicode_content = 'Continue with 日本語 émojis 🚀 and "quotes"'
    prompt_file.write_text(unicode_content, encoding="utf-8")

    result2 = captured_subprocess(input_data, lock_active=True)
    assert result2.returncode == 0
    output2 = json.loads(result2.stdout)
    assert output2["reason"] == unicode_content

    # Test 3: Control characters (newlines get stripped)
    control_content = "Line1\nLine2\tTab"
    prompt_file.write_text(control_content, encoding="utf-8")

    result3 = captured_subprocess(input_data, lock_active=True)
    assert result3.returncode == 0
    output3 = json.loads(result3.stdout)
    # Content gets stripped but newlines/tabs remain in middle
    assert "Line1" in output3["reason"]
    assert "Line2" in output3["reason"]
