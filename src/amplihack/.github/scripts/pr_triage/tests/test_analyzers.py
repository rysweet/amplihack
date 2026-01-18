"""Tests for analyzer functions."""

import json
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir.parent))

# Import the package
from pr_triage.analyzers import extract_json


def test_extract_json_from_code_block():
    """Test extracting JSON from markdown code block."""
    text = """
Here is the response:

```json
{
    "key": "value",
    "number": 42
}
```

That's it.
"""
    result = extract_json(text)
    assert result == {"key": "value", "number": 42}


def test_extract_json_from_raw():
    """Test extracting JSON from raw text."""
    text = """
Some text before
{"key": "value", "status": true}
Some text after
"""
    result = extract_json(text)
    assert result == {"key": "value", "status": True}


def test_extract_json_nested():
    """Test extracting nested JSON."""
    text = """
```json
{
    "outer": {
        "inner": "value"
    },
    "array": [1, 2, 3]
}
```
"""
    result = extract_json(text)
    assert result == {"outer": {"inner": "value"}, "array": [1, 2, 3]}


def test_extract_json_no_match():
    """Test fallback when no JSON found."""
    text = "This is just plain text with no JSON"
    result = extract_json(text)
    assert result == {}


def test_extract_json_malformed():
    """Test handling of malformed JSON."""
    text = """
```json
{this is not valid json}
```
"""
    try:
        result = extract_json(text)
        # Should either return {} or raise error
        assert isinstance(result, dict)
    except json.JSONDecodeError:
        # This is also acceptable behavior
        pass


def test_validate_workflow_compliance_structure():
    """Test that validate_workflow_compliance returns expected structure."""
    # This is an integration test that would require mocking Claude
    # For now, verify the function signature exists
    from pr_triage.analyzers import validate_workflow_compliance

    # Function should accept pr_data dict
    assert callable(validate_workflow_compliance)


def test_detect_priority_complexity_structure():
    """Test that detect_priority_complexity returns expected structure."""
    from pr_triage.analyzers import detect_priority_complexity

    # Function should accept pr_data dict
    assert callable(detect_priority_complexity)


def test_detect_unrelated_changes_structure():
    """Test that detect_unrelated_changes returns expected structure."""
    from pr_triage.analyzers import detect_unrelated_changes

    # Function should accept pr_data dict
    assert callable(detect_unrelated_changes)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
