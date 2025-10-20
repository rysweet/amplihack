"""
Unit tests for JSON serialization.

Tests that output is properly JSON serializable and parseable.
"""

import json


def test_unit_json_001_output_dict_is_json_serializable_allow_case(stop_hook):
    """UNIT-JSON-001: Output dict is JSON serializable - allow case."""
    # Input
    input_data = {"session_id": "test"}

    # Get output
    output = stop_hook.process(input_data)

    # Expected: json.dumps({}) succeeds
    json_str = json.dumps(output)
    assert json_str == "{}"

    # Verify it can be parsed back
    parsed = json.loads(json_str)
    assert parsed == {}


def test_unit_json_002_output_dict_is_json_serializable_block_case(stop_hook, active_lock):
    """UNIT-JSON-002: Output dict is JSON serializable - block case."""
    # Input
    input_data = {"session_id": "test"}

    # Get output
    output = stop_hook.process(input_data)

    # Expected: json.dumps() produces valid JSON
    json_str = json.dumps(output)
    assert isinstance(json_str, str)

    # Verify it can be parsed back
    parsed = json.loads(json_str)
    assert parsed["decision"] == "block"
    assert "reason" in parsed
    assert isinstance(parsed["reason"], str)


def test_unit_json_003_output_parseable_by_claude_code(stop_hook, active_lock):
    """UNIT-JSON-003: Output parseable by Claude Code."""
    # Input
    input_data = {"session_id": "test"}

    # Get output
    output = stop_hook.process(input_data)

    # Expected: Schema validation passes
    assert isinstance(output, dict)

    # When blocking, must have decision and reason
    if "decision" in output:
        assert output["decision"] == "block"
        assert "reason" in output
        assert isinstance(output["reason"], str)
        assert len(output["reason"]) > 0

        # API compliance: no extra fields
        allowed_fields = {"decision", "reason"}
        assert set(output.keys()).issubset(allowed_fields)


def test_unit_json_004_unicode_in_reason_field(stop_hook, active_lock, custom_prompt):
    """UNIT-JSON-004: Unicode in reason field."""
    # Create custom prompt with Unicode
    custom_prompt("Continue with 日本語 and émojis 🚀")

    # Input
    input_data = {"session_id": "test"}

    # Get output
    output = stop_hook.process(input_data)

    # Expected: Properly serialized with UTF-8
    json_str = json.dumps(output, ensure_ascii=False)
    assert "日本語" in json_str
    assert "émojis" in json_str
    assert "🚀" in json_str

    # Verify it can be parsed back
    parsed = json.loads(json_str)
    assert "日本語" in parsed["reason"]
    assert "émojis" in parsed["reason"]
    assert "🚀" in parsed["reason"]
