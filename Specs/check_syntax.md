# Module: Pre-commit Syntax Checker

## Purpose

Validate Python file syntax using AST parsing before allowing commits. Prevents syntax errors from reaching CI.

## Contract

### Inputs
- **files**: List[str] - Python file paths to validate (from pre-commit)
- **Exit codes**:
  - 0: All files valid
  - 1: Syntax errors found

### Outputs
- **stdout**: Error messages with file:line:column format
- **stderr**: None (errors go to stdout for pre-commit integration)

### Side Effects
- None (read-only validation)

## Dependencies

- Python stdlib only:
  - `ast` - AST parsing
  - `pathlib` - File path handling
  - `sys` - Exit codes
  - `argparse` - CLI argument parsing

## Implementation Notes

### Core Algorithm
```python
def validate_file(filepath: str) -> Optional[str]:
    """Validate single file syntax.

    Returns:
        None if valid, error message if invalid
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read(), filename=filepath)
        return None
    except SyntaxError as e:
        return f"{filepath}:{e.lineno}:{e.offset}: {e.msg}"
```

### Performance Optimization
- Use multiprocessing for > 10 files
- Early exit on first error (fail fast)
- Memory-efficient (stream file contents, don't store)

### Integration Points
1. **Pre-commit hook**: Called by `.pre-commit-config.yaml`
2. **CLI**: `python scripts/pre-commit/check_syntax.py file1.py file2.py`
3. **Programmatic**: Importable as module for testing

## Pre-commit Configuration

```yaml
- repo: local
  hooks:
    - id: check-python-syntax
      name: Check Python Syntax
      entry: python scripts/pre-commit/check_syntax.py
      language: system
      types: [python]
      pass_filenames: true
```

## Test Requirements

### Unit Tests (in test_code_quality.py)
1. **Valid file**: Should return 0
2. **Syntax error**: Should return 1 and show error location
3. **Multiple files**: Should validate all and aggregate errors
4. **Empty file**: Should pass
5. **UTF-8 BOM**: Should handle gracefully

### Performance Tests
1. **50 files**: < 500ms
2. **Full codebase**: < 2s
3. **Single file**: < 50ms

### Edge Cases
1. **Valid code with "======"**: `test_data = "======"` - Should pass
2. **Valid code with "<<<"**: `# Comment with <<<` - Should pass
3. **Valid code with ">>>"**: `# Doctest marker >>>` - Should pass
4. **Merge conflict markers**: Should fail (invalid syntax anyway)

### Test Ordering
- Use `@pytest.mark.order(1)` to run syntax tests first
- Add dependency: `pytest-order` if not present

## Error Message Format

Follow standard compiler format for IDE integration:
```
filename.py:42:10: invalid syntax
```

This format is recognized by:
- VS Code
- PyCharm
- vim
- emacs
- pre-commit output formatting

## Success Metrics

1. **Speed**: < 500ms for 50 files on CI hardware
2. **Accuracy**: Zero false positives, 100% syntax error detection
3. **Integration**: Works seamlessly with existing pre-commit setup
4. **Usability**: Clear error messages with exact location
