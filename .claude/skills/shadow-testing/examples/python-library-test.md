# Example: Testing Python Library Changes

This example shows testing a Python library's uncommitted changes with a dependent project.

## Scenario

You're working on `myorg/data-processor` library and want to test changes with the CLI tool that depends on it before pushing.

## Local Changes

```python
# ~/repos/data-processor/src/data_processor/core.py
# You've added a new parameter to process()
def process(data, validate=True):  # NEW: validate parameter
    if validate:
        check_schema(data)
    return transform(data)
```

This is a breaking change if callers don't pass `validate`. Test with the dependent CLI tool before pushing.

## Setup Shadow

### Using Amplifier

```python
# Create shadow with your local changes
result = shadow.create(
    local_sources=["~/repos/data-processor:myorg/data-processor"]
)

shadow_id = result.output["shadow_id"]
print(f"Created shadow: {shadow_id}")
print(f"Snapshot commit: {result.output['snapshot_commits']['myorg/data-processor']}")
```

### Using Standalone CLI

```bash
amplifier-shadow create \
    --local ~/repos/data-processor:myorg/data-processor \
    --name test-breaking-change

# Note the snapshot commit from output for verification
```

## Test the Change

```bash
# Install dependent CLI tool (will use YOUR local data-processor)
amplifier-shadow exec test-breaking-change "
    cd /workspace &&
    git clone https://github.com/myorg/data-cli &&
    cd data-cli &&
    uv venv && . .venv/bin/activate &&
    uv pip install git+https://github.com/myorg/data-processor &&
    pytest tests/
"
```

### Verify Local Source Used

```bash
# Check what commit was installed
amplifier-shadow exec test-breaking-change "
    pip show data-processor | grep Location
"

# Should show installed from git with your snapshot commit SHA
```

## Expected Outcomes

### If Tests Pass

```
✓ All tests passed
Your breaking change is backward compatible OR
dependent project already handles the new parameter
Safe to push!
```

### If Tests Fail

```
✗ Tests failed in test_process.py::test_basic_process
TypeError: process() got an unexpected keyword argument 'validate'

Action required:
1. Update data-processor to make validate optional (validate=True as default)
2. OR update data-cli to pass validate parameter
3. Test again in shadow
```

## Cleanup

```bash
amplifier-shadow destroy test-breaking-change
```

## Alternative: Use Pre-Cloned Workspace

Shadow automatically clones local sources to `/workspace/{org}/{repo}`:

```bash
amplifier-shadow exec test-breaking-change "
    cd /workspace/myorg/data-processor &&
    pip install -e . &&
    pytest
"
```

This is faster than cloning via git URL.
