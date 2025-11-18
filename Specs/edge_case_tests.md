# Module: Edge Case Tests for Syntax Validation

## Purpose

Ensure zero false positives in syntax validation. Valid Python code with merge-conflict-like patterns (strings with "=====", comments with "<<<") must pass validation.

## Contract

### Inputs
- **Test fixtures**: Valid Python code containing patterns that might trigger false positives
- **Validator**: The `check_syntax.py` module being tested

### Outputs
- **pytest pass/fail**: All edge cases must pass validation
- **Confidence**: 100% certainty that valid code won't be rejected

### Side Effects
- None (read-only validation)

## Dependencies

- `pytest` - Test framework
- `tempfile` - Temporary file creation for test cases
- Built-in `check_syntax` module being tested

## Implementation Notes

### Test Categories

#### Category 1: Valid Code with Merge Conflict Markers in Strings
```python
@pytest.mark.order(3)
@pytest.mark.edge_case
class TestValidCodeWithSpecialPatterns:
    """Ensure valid code with special patterns passes."""

    def test_equals_in_string_literal(self, tmp_path):
        """String containing '=======' should pass."""
        code = '''
def render_separator():
    """Return a separator line."""
    return "=" * 70

def test_data():
    """Test data with equals."""
    data = "======"
    return data
'''
        # Validate and assert passes

    def test_angles_in_string_literal(self, tmp_path):
        """String containing '<<<' and '>>>' should pass."""
        code = '''
def format_heredoc():
    """Format heredoc marker."""
    return "<<<EOF"

def format_chevron():
    """Format chevron."""
    return ">>> result"
'''
        # Validate and assert passes

    def test_pipes_in_string_literal(self, tmp_path):
        """String containing '|||' should pass."""
        code = '''
def separator():
    """Pipe separator."""
    return "|||||||"
'''
        # Validate and assert passes
```

#### Category 2: Valid Code with Markers in Comments
```python
    def test_angles_in_comment(self, tmp_path):
        """Comments containing '<<<' should pass."""
        code = '''
# This is a comment with <<< marker
def function():
    # Another comment with >>> marker
    pass
'''
        # Validate and assert passes

    def test_doctest_markers(self, tmp_path):
        """Doctest markers ('>>>') should pass."""
        code = '''
def add(a, b):
    """Add two numbers.

    >>> add(2, 3)
    5
    >>> add(-1, 1)
    0
    """
    return a + b
'''
        # Validate and assert passes
```

#### Category 3: Valid Code with Complex String Formatting
```python
    def test_multiline_string_with_equals(self, tmp_path):
        """Multiline strings with '=' should pass."""
        code = '''
def banner():
    """Return banner."""
    return """
    ========================================
    Welcome to the Application
    ========================================
    """
'''
        # Validate and assert passes

    def test_fstring_with_equals(self, tmp_path):
        """F-strings with '=' should pass."""
        code = '''
def debug(x):
    """Debug print."""
    print(f"{x=}")  # Python 3.8+ f-string debug syntax
    return f"Value: {x}"
'''
        # Validate and assert passes
```

#### Category 4: Actual Merge Conflicts (Should Fail)
```python
    def test_real_merge_conflict_fails(self, tmp_path):
        """Real merge conflict markers should fail."""
        code = '''
def function():
<<<<<<< HEAD
    return "version 1"
=======
    return "version 2"
>>>>>>> branch
'''
        # Validate and assert FAILS with SyntaxError
        # This is correct behavior - real merge conflicts are invalid syntax
```

### Test Implementation Pattern

```python
def validate_code_string(code: str, should_pass: bool = True) -> None:
    """Helper to validate code string.

    Args:
        code: Python code to validate
        should_pass: Whether validation should succeed

    Raises:
        AssertionError: If validation result doesn't match expectation
    """
    import ast
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = Path(f.name)

    try:
        # Use same validation logic as check_syntax.py
        with open(temp_file, 'r') as f:
            ast.parse(f.read(), filename=str(temp_file))

        if should_pass:
            # Success - code is valid as expected
            pass
        else:
            # Should have failed but didn't
            raise AssertionError(f"Expected syntax error but code passed: {code}")

    except SyntaxError:
        if should_pass:
            # Should have passed but failed - FALSE POSITIVE
            raise AssertionError(f"Valid code rejected (false positive): {code}")
        else:
            # Correctly detected invalid syntax
            pass
    finally:
        temp_file.unlink()
```

### Comprehensive Edge Case Matrix

| Pattern | Location | Expected | Test Name |
|---------|----------|----------|-----------|
| `=====` | String literal | Pass | `test_equals_in_string_literal` |
| `<<<` | String literal | Pass | `test_angles_in_string_literal` |
| `>>>` | String literal | Pass | `test_angles_in_string_literal` |
| `=====` | Comment | Pass | `test_equals_in_comment` |
| `<<<` | Comment | Pass | `test_angles_in_comment` |
| `>>>` | Doctest | Pass | `test_doctest_markers` |
| `=====` | Multiline string | Pass | `test_multiline_string_with_equals` |
| `{x=}` | F-string | Pass | `test_fstring_with_equals` |
| Merge conflict | Top-level | Fail | `test_real_merge_conflict_fails` |

## Test Requirements

### Functional Tests
1. **All valid patterns pass**: No false positives
2. **Real conflicts fail**: No false negatives
3. **Helper function works**: `validate_code_string()` is reliable

### Coverage Requirements
1. **String literals**: All quote styles (', ", ''', """)
2. **Comments**: Single-line (#) and multi-line (docstrings)
3. **F-strings**: Including debug syntax (`{x=}`)
4. **Raw strings**: `r"..."` with special characters
5. **Byte strings**: `b"..."` with special characters

### Performance Requirements
1. **Fast execution**: All edge case tests < 100ms total
2. **No flakiness**: 100% pass rate (deterministic)

### Documentation Requirements
Each test must have:
1. **Clear docstring**: What pattern is being tested
2. **Example code**: Show the pattern inline
3. **Rationale**: Why this might trigger false positive

## False Positive Prevention Strategy

### Why AST Parsing Prevents False Positives

AST parsing (`ast.parse()`) only looks at Python syntax structure, not string/comment contents:

```python
# This code:
code = "<<<<<<< HEAD"

# Parses to AST:
Module(
    body=[
        Assign(
            targets=[Name(id='code')],
            value=Constant(value='<<<<<<< HEAD')  # String content ignored
        )
    ]
)
```

The string content `'<<<<<<< HEAD'` is just data to the parser. Only syntactically invalid code (like bare `<<<<<<< HEAD` at top level) causes `SyntaxError`.

### Verification Strategy

For each edge case:
1. **Confirm valid**: Manually verify code is valid Python
2. **Test with python**: `python -m py_compile file.py`
3. **Test with ast**: `ast.parse(open(file).read())`
4. **Test with validator**: `check_syntax.py file.py`

All four methods must agree.

## Success Metrics

1. **Zero false positives**: All valid code passes (100%)
2. **Zero false negatives**: All invalid code fails (100%)
3. **Comprehensive coverage**: All identified edge cases tested
4. **Documentation**: Each test clearly explains why it exists

## Integration with Test Suite

```python
# In test_code_quality.py or test_syntax.py

@pytest.mark.order(3)  # After basic tests (1) and performance (2)
@pytest.mark.edge_case
class TestSyntaxEdgeCases:
    """Edge case tests for syntax validation - ensure zero false positives."""

    # All edge case tests go here
    pass
```

## Continuous Improvement

When new edge cases are discovered:
1. **Document**: Add to this spec
2. **Test**: Add test case
3. **Verify**: Ensure passes before adding to suite
4. **Commit**: "Add edge case test for [pattern]"

Track discovered edge cases in `.claude/context/DISCOVERIES.md`.
