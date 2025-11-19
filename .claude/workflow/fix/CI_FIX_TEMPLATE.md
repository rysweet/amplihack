# CI/CD Fix Template

**Usage**: 20% of all fixes - Pipeline configuration, dependency conflicts, build environment issues, deployment failures

## Problem Pattern Recognition

### Triggers

- GitHub Actions workflow failures
- Build process errors
- Deployment pipeline issues
- Environment setup failures
- Dependency resolution conflicts

### Error Indicators

```bash
# Common CI error patterns
"build failed"
"test failed"
"dependency conflict"
"environment not found"
"permission denied"
"timeout"
"image not found"
"network error"
```

## Quick Assessment (60 seconds)

### Step 1: Identify Failure Stage

```bash
# Check CI logs for failure point
# Build stage, test stage, deploy stage, etc.
gh run list --limit 5
gh run view [run-id] --log
```

### Step 2: Error Category

```bash
# Categorize the error type:
# - Build/compilation errors
# - Test failures
# - Environment issues
# - Dependency problems
# - Configuration errors
# - Infrastructure issues
```

### Step 3: Impact Assessment

- **Blocking**: PR cannot merge
- **Flaky**: Intermittent failures
- **Environmental**: Specific to CI environment
- **Systematic**: Affects all builds

## Solution Steps by Category

### Build/Compilation Errors

```yaml
# Check build configuration
name: Build
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup environment
        # Ensure correct versions
      - name: Install dependencies
        # Lock file consistency
      - name: Build
        # Clear build commands
```

### Dependency Resolution

```bash
# Python dependency fixes
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir

# Node.js dependency fixes
npm ci  # Use ci for CI environments
npm audit fix

# General dependency debugging
pip list --outdated
npm outdated
```

### Environment Issues

```yaml
# Fix environment configuration
env:
  NODE_VERSION: "18"
  PYTHON_VERSION: "3.9"

steps:
  - name: Setup Python
    uses: actions/setup-python@v4
    with:
      python-version: ${{ env.PYTHON_VERSION }}

  - name: Setup Node
    uses: actions/setup-node@v4
    with:
      node-version: ${{ env.NODE_VERSION }}
```

### Test Failures in CI

```bash
# Test environment differences
# Check for missing test data
# Verify test isolation
# Fix timing-dependent tests

# Common fixes:
pytest --maxfail=1 -v  # Stop on first failure
npm test -- --verbose  # Detailed output
```

### Configuration Errors

```yaml
# Common workflow configuration fixes
permissions:
  contents: read
  pull-requests: write

timeout-minutes: 30 # Prevent infinite runs

strategy:
  fail-fast: false # Continue other jobs
  matrix:
    os: [ubuntu-latest]
    python-version: ["3.9", "3.10", "3.11"]
```

## Validation Steps

### 1. Local Reproduction

```bash
# Try to reproduce CI failure locally
act  # Run GitHub Actions locally
docker run --rm -v $(pwd):/workspace ubuntu:latest bash
```

### 2. Incremental Testing

```bash
# Test individual components
docker build .  # Test build step
npm run test:ci  # Test CI-specific commands
```

### 3. Full Pipeline Test

```bash
# Push and monitor
git push origin feature-branch
gh run watch  # Monitor real-time
```

## Common Fix Patterns

### Pattern 1: Version Lock Issues

```yaml
# Before (causes conflicts)
dependencies:
  - "requests"
  - "flask"

# After (explicit versions)
dependencies:
  - "requests==2.31.0"
  - "flask==2.3.3"
```

### Pattern 2: Cache Issues

```yaml
# Add cache invalidation
- name: Cache dependencies
  uses: actions/cache@v3
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

### Pattern 3: Secrets Management

```yaml
# Fix secret access
env:
  API_KEY: ${{ secrets.API_KEY }}

steps:
  - name: Check secrets
    run: |
      if [ -z "$API_KEY" ]; then
        echo "Missing API_KEY secret"
        exit 1
      fi
```

### Pattern 4: Parallel Job Issues

```yaml
# Fix job dependencies
jobs:
  test:
    runs-on: ubuntu-latest
    # ...

  deploy:
    needs: test # Wait for test completion
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
```

## Integration Points

### With CI Diagnostic Workflow Agent

- Use this template for standard CI issues
- Escalate complex infrastructure problems
- Hand off deployment-specific issues

### With Fix Agent

- Apply QUICK mode for obvious config errors
- Use DIAGNOSTIC mode for unclear failures
- Escalate to COMPREHENSIVE for architecture changes

### With Main Workflow

- Use during Step 13 (Ensure PR is Mergeable)
- Integrate with Step 7 (Pre-commit hooks)
- Apply in Step 11 (Implement Review Feedback)

## Tool-Specific Guidance

### GitHub Actions

```yaml
# Standard debugging setup
- name: Debug Info
  run: |
    echo "Runner OS: ${{ runner.os }}"
    echo "Event: ${{ github.event_name }}"
    echo "Ref: ${{ github.ref }}"
    env
```

### Docker Issues

```dockerfile
# Common Dockerfile fixes
FROM python:3.9-slim

# Fix permission issues
RUN adduser --disabled-password app
USER app

# Fix dependency caching
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

### Test Environment

```bash
# Ensure test environment consistency
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export NODE_ENV=test
export CI=true
```

## Escalation Triggers

### When to Use CI Diagnostic Workflow Agent

- Multiple related CI failures
- Infrastructure-level issues
- Complex deployment problems
- Cross-service integration failures

### When to Use Full Workflow

- New CI pipeline needed
- Security configuration changes
- Multi-repository changes
- Breaking changes to build process

## Quick Reference

### 10-Minute Fix Checklist

- [ ] Check CI logs for specific error
- [ ] Identify failure category
- [ ] Apply relevant fix pattern
- [ ] Test locally if possible
- [ ] Push and monitor new run
- [ ] Verify all checks pass

### Common Quick Fixes

```bash
# Cache invalidation
git commit --allow-empty -m "Trigger CI rebuild"

# Dependency refresh
rm -rf node_modules package-lock.json
npm install

# Container rebuild
docker system prune -f
docker build --no-cache .
```

## Success Patterns

### High-Success Scenarios

- Dependency version conflicts (85% success)
- Environment variable issues (90% success)
- Configuration syntax errors (95% success)
- Cache invalidation needs (80% success)

### Challenging Scenarios

- Infrastructure failures (40% success)
- Third-party service issues (30% success)
- Complex timing issues (50% success)
- Cross-platform compatibility (60% success)

## Monitoring and Learning

### Metrics to Track

- CI fix success rate by error type
- Time from failure to resolution
- Recurrence rate of similar issues
- Impact on development velocity

### Continuous Improvement

- Build failure pattern library
- Automate common fixes
- Improve error detection
- Update templates based on new patterns

Remember: CI fixes should be minimal and focused. Avoid over-engineering solutions for simple configuration issues.
