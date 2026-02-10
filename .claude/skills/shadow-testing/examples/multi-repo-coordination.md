# Example: Multi-Repository Coordination

This example shows testing coordinated changes across multiple repositories.

## Scenario

You're working on two repositories:
- `myorg/api-client` - HTTP client library
- `myorg/cli-tool` - CLI that depends on api-client

Both have uncommitted changes that must work together.

## Local Changes

**api-client** (breaking change):
```python
# Old API
client.get(endpoint)

# New API (renamed for clarity)
client.fetch(endpoint)  # BREAKING: renamed from get()
```

**cli-tool** (updated to use new API):
```python
# Updated to use new fetch() method
def download(url):
    return client.fetch(url)  # Changed from client.get()
```

## Setup Shadow with Both Repos

### Using Amplifier

```python
result = shadow.create(local_sources=[
    "~/repos/api-client:myorg/api-client",
    "~/repos/cli-tool:myorg/cli-tool"
])

print("Snapshot commits:")
for repo, commit in result.output['snapshot_commits'].items():
    print(f"  {repo}: {commit}")
```

### Using Standalone CLI

```bash
amplifier-shadow create \
    --local ~/repos/api-client:myorg/api-client \
    --local ~/repos/cli-tool:myorg/cli-tool \
    --name multi-test

# Output shows both snapshot commits for verification
```

## Test Coordinated Changes

```bash
# Install cli-tool (which depends on api-client)
# Both will use YOUR local snapshots
amplifier-shadow exec multi-test "
    cd /workspace &&
    git clone https://github.com/myorg/cli-tool test-cli &&
    cd test-cli &&
    uv venv && . .venv/bin/activate &&
    
    # This installs BOTH local snapshots via git dependencies
    uv pip install -e . &&
    
    # Run full test suite
    pytest tests/ -v
"
```

## Verification

Verify both local sources are being used:

```bash
amplifier-shadow exec multi-test "
    cd test-cli &&
    pip list | grep -E 'api-client|cli-tool'
"

# Should show both installed from git with your snapshot commits
```

## Expected Outcomes

### Success Case

```
✓ cli-tool tests pass
✓ api-client is using your local snapshot (commit abc1234)
✓ cli-tool is using your local snapshot (commit def5678)

Both changes are compatible - safe to push!
```

### Failure Case

```
✗ Tests fail: AttributeError: 'Client' object has no attribute 'fetch'

Diagnosis: api-client wasn't actually installed from your local source.
Possible causes:
- UV cache hit (run with --refresh)
- Git URL rewriting not working
- Wrong org/repo name in local_sources
```

## Troubleshooting

If only one repo uses local source:

```bash
# Check git URL rewriting config
amplifier-shadow exec multi-test "git config --list | grep insteadOf"

# Should show rules for BOTH repositories
```

## Cleanup

```bash
amplifier-shadow destroy multi-test
```

## Pro Tip: Iterative Testing

Shadow environments are cheap to create/destroy:

```bash
# Run 1: Test coordinated changes
amplifier-shadow create --local ... --name test
amplifier-shadow exec test "pytest"  # Fails

# Fix locally on host

# Run 2: Destroy and recreate (fast)
amplifier-shadow destroy test
amplifier-shadow create --local ... --name test
amplifier-shadow exec test "pytest"  # Passes!

# Commit both repos with confidence
```
