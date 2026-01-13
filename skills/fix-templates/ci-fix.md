# CI/CD Fix Template

> **Coverage**: ~20% of all fixes
> **Target Time**: 30-60 seconds assessment, 2-5 minutes resolution

## Problem Pattern Recognition

### Trigger Indicators

```
Error patterns in logs:
- "workflow", "pipeline", "action", "job"
- "build failed", "deploy failed"
- "exit code 1", "process exited with"
- "Error: Process completed with exit code"
- "##[error]", "::error::"
```

### Error Categories

| Category | Frequency | Indicators |
|----------|-----------|------------|
| Pipeline Config | 35% | YAML syntax, invalid workflow, unknown action |
| Dependencies | 30% | pip install failed, npm ci failed, cache miss |
| Build Scripts | 20% | command not found, permission denied, script error |
| Deployment | 15% | authentication failed, push rejected, timeout |

## Quick Assessment (30-60 sec)

### Step 1: Identify Failure Stage

```bash
# Check which job/step failed
# Look for: "Job XXX failed" or step with red X

# Key questions:
# 1. Which workflow file? (.github/workflows/*.yml)
# 2. Which job failed?
# 3. Which step in that job?
# 4. First error message (ignore cascading failures)
```

### Step 2: Categorize the Error

```
Pipeline Config → YAML syntax, action reference, permissions
Dependencies   → install commands, lockfile, cache
Build Scripts  → test/build/lint commands, missing tools
Deployment     → secrets, auth, target environment
```

## Solution Steps by Category

### Pipeline Config Issues

**YAML Syntax Errors**
```yaml
# Common fixes:
# 1. Indentation (use 2 spaces, not tabs)
# 2. Quotes around special characters: "${{ secrets.TOKEN }}"
# 3. Multiline strings use |
run: |
  echo "line 1"
  echo "line 2"
```

**Action Reference Errors**
```yaml
# Wrong: uses: actions/checkout  (missing version)
# Right: uses: actions/checkout@v4

# Wrong: uses: ./my-action  (path issues)
# Right: uses: ./.github/actions/my-action
```

**Permissions Issues**
```yaml
# Add explicit permissions
permissions:
  contents: read
  packages: write
  id-token: write  # For OIDC
```

### Dependency Issues

**Python Dependencies**
```yaml
# Cache dependencies properly
- uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'

# Use lockfile for reproducibility
- run: pip install -r requirements.txt
# Or with uv:
- run: uv pip install -r requirements.txt
```

**Node Dependencies**
```yaml
# Use npm ci (not npm install) for CI
- run: npm ci

# Cache node_modules
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'
```

**Lockfile Mismatches**
```bash
# Regenerate lockfile locally:
pip freeze > requirements.txt
# Or:
npm install && git add package-lock.json
```

### Build Script Issues

**Command Not Found**
```yaml
# Ensure tool is installed
- run: pip install ruff
- run: ruff check .

# Or use action that includes tool
- uses: astral-sh/ruff-action@v1
```

**Permission Denied**
```yaml
# Make script executable
- run: chmod +x ./scripts/build.sh && ./scripts/build.sh

# Or run with interpreter
- run: bash ./scripts/build.sh
```

**Path Issues**
```yaml
# Use relative paths from repo root
- run: python src/main.py
  working-directory: ${{ github.workspace }}
```

### Deployment Issues

**Authentication Failures**
```yaml
# Check secret is set (Settings > Secrets > Actions)
# Use correct secret name
env:
  API_KEY: ${{ secrets.API_KEY }}

# For OIDC (preferred):
permissions:
  id-token: write
  contents: read
```

**Push Rejected**
```yaml
# Token needs write permission
- uses: actions/checkout@v4
  with:
    token: ${{ secrets.PAT_TOKEN }}  # Not GITHUB_TOKEN
    persist-credentials: true
```

## GitHub Actions Specific Fixes

### Common Workflow Patterns

**Matrix Strategy Failures**
```yaml
strategy:
  fail-fast: false  # Don't cancel other jobs on failure
  matrix:
    os: [ubuntu-latest, macos-latest]
    python: ['3.10', '3.11', '3.12']
```

**Conditional Steps**
```yaml
# Only run on main branch
- run: ./deploy.sh
  if: github.ref == 'refs/heads/main'

# Only on PR
- run: ./pr-check.sh
  if: github.event_name == 'pull_request'
```

**Artifact Upload/Download**
```yaml
# Upload
- uses: actions/upload-artifact@v4
  with:
    name: build-output
    path: dist/

# Download (in later job)
- uses: actions/download-artifact@v4
  with:
    name: build-output
```

### Self-Hosted Runner Issues

```yaml
# Specify correct labels
runs-on: [self-hosted, linux, x64]

# Clean workspace
- run: rm -rf ${{ github.workspace }}/*
  if: always()
```

## Validation Steps

### Pre-Push Validation

```bash
# Validate workflow syntax locally
# Install: pip install check-jsonschema
check-jsonschema --schemafile https://json.schemastore.org/github-workflow .github/workflows/*.yml

# Or use act to run locally
act -n  # Dry run
act push  # Simulate push event
```

### Post-Fix Validation

```bash
# 1. Push fix and wait for CI
git push

# 2. Check workflow run
gh run watch

# 3. If failed, get logs
gh run view --log-failed
```

### Quick Debugging Commands

```bash
# View recent workflow runs
gh run list

# View specific run
gh run view <run-id>

# View failed step logs
gh run view <run-id> --log-failed

# Re-run failed jobs
gh run rerun <run-id> --failed
```

## Escalation Criteria

### Escalate When

- Infrastructure issues (GitHub Actions outage)
- Secret rotation needed
- Self-hosted runner problems
- Complex matrix/reusable workflow issues
- Cross-repository workflow dependencies

### Information to Gather

```
1. Workflow file and job/step that failed
2. Complete error message (first error, not cascading)
3. Recent changes to workflow or dependencies
4. Is this a new workflow or regression?
5. Does it fail consistently or intermittently?
```

## Quick Reference

### Fastest Fixes (< 1 min)

| Problem | Fix |
|---------|-----|
| YAML indentation | Fix spacing (2 spaces) |
| Missing action version | Add `@v4` to action |
| Secret not found | Check secret name in Settings |
| Cache miss | Clear cache, re-run |

### Common Error → Solution

```
"Node.js 12 actions are deprecated"
→ Update actions to v4 versions

"Resource not accessible by integration"
→ Add permissions block to workflow

"No such file or directory"
→ Check working-directory, use relative paths

"Exit code 1" (generic)
→ Read the actual command output above this line
```
