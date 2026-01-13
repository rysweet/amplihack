# Agent Input Validation Rules

Guidelines for agents to validate input before processing to prevent wasted work and unclear failures.

---

## Core Principle

**Validate early, fail fast, fail clearly.**

Never start complex operations on invalid input. Check everything upfront and report all problems at once.

---

## Validation Phases

### Phase 1: Existence Checks

Before any processing, verify required inputs exist:

```python
def validate_exists(request: AgentRequest) -> list[str]:
    """Check that required inputs exist."""
    errors = []
    
    # Required fields
    if not request.target_path:
        errors.append("target_path is required")
    
    # File existence
    if request.target_path and not Path(request.target_path).exists():
        errors.append(f"Target path does not exist: {request.target_path}")
    
    # Required context
    if not request.context.get("user_intent"):
        errors.append("user_intent context is required")
    
    return errors
```

### Phase 2: Format Validation

Verify inputs are in expected format:

```python
def validate_format(request: AgentRequest) -> list[str]:
    """Check input formats."""
    errors = []
    
    # Path format
    if request.target_path:
        try:
            Path(request.target_path).resolve()
        except Exception as e:
            errors.append(f"Invalid path format: {e}")
    
    # Expected file types
    if request.target_path and not request.target_path.endswith(('.py', '.js', '.ts')):
        errors.append(f"Unsupported file type: {request.target_path}")
    
    # JSON structure
    if request.config:
        try:
            json.loads(request.config) if isinstance(request.config, str) else request.config
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON config: {e}")
    
    return errors
```

### Phase 3: Semantic Validation

Verify inputs make sense together:

```python
def validate_semantic(request: AgentRequest) -> list[str]:
    """Check semantic validity."""
    errors = []
    
    # Conflicting options
    if request.mode == "create" and request.target_path and Path(request.target_path).exists():
        errors.append(f"Cannot create: {request.target_path} already exists (use mode='update')")
    
    if request.mode == "update" and request.target_path and not Path(request.target_path).exists():
        errors.append(f"Cannot update: {request.target_path} does not exist (use mode='create')")
    
    # Logical constraints
    if request.max_lines and request.max_lines < 10:
        errors.append("max_lines must be at least 10")
    
    # Permission checks
    if request.target_path:
        parent = Path(request.target_path).parent
        if not os.access(parent, os.W_OK):
            errors.append(f"No write permission for directory: {parent}")
    
    return errors
```

---

## Validation Response Format

Always report validation failures in a structured, actionable way:

### Good Validation Response

```markdown
## Validation Failed

Cannot proceed with request. Please fix the following issues:

### Missing Required Inputs
- `target_path`: Required but not provided
- `user_intent`: Required in context but missing

### Format Errors  
- `config`: Invalid JSON at position 45 - unexpected comma

### Semantic Errors
- Cannot use `mode=update` when target file doesn't exist

### How to Fix
1. Provide `target_path` parameter
2. Add `user_intent` to the context
3. Fix JSON syntax in config
4. Either create the file first or use `mode=create`
```

### Bad Validation Response

```markdown
Error: Invalid input
```

---

## Input Categories

### Required vs Optional

```python
REQUIRED_INPUTS = {
    "target_path": "Path to file or directory to operate on",
    "operation": "What action to perform",
}

OPTIONAL_INPUTS = {
    "config": "Additional configuration (default: {})",
    "dry_run": "Preview changes without applying (default: false)",
    "verbose": "Include detailed output (default: false)",
}
```

### Input Types by Agent

| Agent Type | Required | Optional |
|------------|----------|----------|
| Builder | target_path, spec | config, tests |
| Reviewer | file_paths | focus_areas, severity |
| Analyzer | target_path OR code | depth, include_dependencies |
| Tester | target_path | coverage_threshold, test_types |

---

## Validation Patterns

### Pattern 1: Collect All Errors

**Wrong**: Stop at first error
```python
if not path:
    raise ValueError("path required")
if not path.exists():  # Never reached if path missing
    raise ValueError("path not found")
```

**Right**: Collect all errors
```python
errors = []
if not path:
    errors.append("path required")
elif not path.exists():  # Only check if path provided
    errors.append(f"path not found: {path}")

if errors:
    raise ValidationError(errors)
```

### Pattern 2: Provide Context

**Wrong**: Generic message
```python
errors.append("invalid format")
```

**Right**: Specific, actionable message
```python
errors.append(f"Invalid date format '{value}'. Expected YYYY-MM-DD, got '{value}'")
```

### Pattern 3: Suggest Fixes

**Wrong**: Just report problem
```python
errors.append("File not found: config.yaml")
```

**Right**: Report and suggest
```python
errors.append(
    f"File not found: config.yaml. "
    f"Create it with: cp config.example.yaml config.yaml"
)
```

### Pattern 4: Validate Early

**Wrong**: Validate during processing
```python
def process_files(files):
    results = []
    for f in files:
        if not f.exists():  # Fails mid-operation
            raise FileNotFoundError(f)
        results.append(process(f))
    return results
```

**Right**: Validate before processing
```python
def process_files(files):
    # Validate all upfront
    missing = [f for f in files if not f.exists()]
    if missing:
        raise ValidationError(f"Files not found: {missing}")
    
    # Now safe to process
    return [process(f) for f in files]
```

---

## Agent-Specific Validation

### Builder Agent

```python
def validate_builder_input(request):
    errors = []
    
    # Must have either spec or target to infer from
    if not request.spec and not request.target_path:
        errors.append("Either 'spec' or 'target_path' required")
    
    # Spec must be parseable
    if request.spec:
        if not isinstance(request.spec, (str, dict)):
            errors.append("spec must be string (markdown) or dict")
    
    # Target must be writable
    if request.target_path:
        parent = Path(request.target_path).parent
        if parent.exists() and not os.access(parent, os.W_OK):
            errors.append(f"Cannot write to {parent}")
    
    return errors
```

### Reviewer Agent

```python
def validate_reviewer_input(request):
    errors = []
    
    # Must have something to review
    if not request.file_paths and not request.code:
        errors.append("Either 'file_paths' or 'code' required")
    
    # Files must exist
    if request.file_paths:
        missing = [f for f in request.file_paths if not Path(f).exists()]
        if missing:
            errors.append(f"Files not found: {', '.join(missing)}")
    
    # Focus areas must be valid
    valid_focus = {"security", "performance", "style", "bugs", "all"}
    if request.focus_areas:
        invalid = set(request.focus_areas) - valid_focus
        if invalid:
            errors.append(f"Invalid focus areas: {invalid}. Valid: {valid_focus}")
    
    return errors
```

---

## Validation Checklist

Before processing any agent request:

- [ ] All required inputs provided?
- [ ] Input types correct (string, list, dict)?
- [ ] Paths exist and are accessible?
- [ ] Permissions sufficient for operation?
- [ ] No conflicting options?
- [ ] Values within valid ranges?
- [ ] All errors collected and reported together?
- [ ] Error messages include fix suggestions?

---

## Error Message Template

```
## Validation Error: [Brief Summary]

**Operation**: [What was attempted]
**Status**: Cannot proceed

### Issues Found

1. **[Category]**: [Specific problem]
   - Expected: [What was expected]
   - Received: [What was provided]
   - Fix: [How to resolve]

2. **[Category]**: [Specific problem]
   ...

### Quick Fix

[Single command or action that fixes the most common case]
```
