# CI/CD Requirements for Plugin Testing

**Date**: 2026-01-20
**Workflow**: `.github/workflows/plugin-test.yml`

---

## 🔑 Required GitHub Secrets

### ANTHROPIC_API_KEY

**Purpose**: Claude Code CLI requires an API key to authenticate.

**Setup Instructions**:

1. Go to your GitHub repository
2. Navigate to: **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Set:
   - **Name**: `ANTHROPIC_API_KEY`
   - **Value**: Your Anthropic API key (from https://console.anthropic.com)
5. Click **Add secret**

**Why Required**:
- Claude Code needs authentication to connect to Anthropic API
- Without it, `claude` command will fail with auth error
- Test will show: `Auth conflict: Using ANTHROPIC_API_KEY...`

---

## 🔧 CI Environment Setup

### Dependencies Installed by Workflow

The GitHub Actions workflow automatically installs:

1. **Node.js 18** (for node-pty)
2. **Python 3.11** (for pipx/uv)
3. **pipx** (Python package installer)
4. **uv** (fast Python package installer via pipx)
5. **Claude Code CLI** (via npm)
6. **node-pty** (for PTY virtualization)
7. **expect** (for shell-based test alternative)

### Manual Steps (if running locally)

```bash
# Install pipx and uv
pip install pipx
pipx install uv

# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Install node-pty
cd tests/agentic
npm install

# Set API key
export ANTHROPIC_API_KEY="your-key-here"
```

---

## 🎯 CI Test Jobs

### Job 1: test-plugin (PTY-based)

**Purpose**: Automated test using node-pty for PTY virtualization

**Steps**:
1. Install dependencies
2. Install amplihack from branch via UVX
3. Verify plugin deployment
4. Run PTY test (`node test-claude-plugin-pty.js`)
5. Upload evidence artifacts

**Requirements**:
- ✅ Node.js 18+ (for node-pty)
- ✅ Python 3.11+ (for uvx)
- ✅ ANTHROPIC_API_KEY secret
- ✅ Ubuntu runner (Linux)

### Job 2: test-plugin-shell (expect-based)

**Purpose**: Alternative test using expect (no Node.js compilation)

**Steps**:
1. Install dependencies (expect)
2. Run shell test (`./run-plugin-test.sh`)
3. Upload evidence artifacts

**Requirements**:
- ✅ Python 3.11+ (for uvx)
- ✅ expect package
- ✅ ANTHROPIC_API_KEY secret
- ✅ Ubuntu runner (Linux)

---

## ⚠️ Known CI Limitations

### 1. Claude Code Requires API Key

**Issue**: Tests will fail if `ANTHROPIC_API_KEY` is not set in GitHub secrets.

**Error Message**:
```
Error: No API key found. Please set ANTHROPIC_API_KEY or run `claude login`
```

**Solution**: Add ANTHROPIC_API_KEY to repository secrets (see above).

### 2. Interactive TUI in CI

**Issue**: CI environments are non-interactive by default.

**Solution**: We use PTY virtualization (node-pty) which creates a virtual terminal that works in CI.

**Why it works**:
- PTY makes Claude Code think it's in a real terminal
- No display/X11 required
- Fully automated interaction

### 3. Timing Sensitivity

**Issue**: CI runners might be slower than local machines.

**Solution**:
- Tests use generous timeouts (3-5 second waits)
- `continue-on-error: true` for initial testing phase
- Evidence artifacts uploaded even on failure

### 4. Network Access

**Issue**: CI needs to fetch from GitHub (git+https://...).

**Solution**: GitHub Actions runners have internet access by default.

---

## 📊 Expected CI Behavior

### Success Scenario

```yaml
✓ Checkout code
✓ Setup Node.js
✓ Setup Python
✓ Install pipx and uv
✓ Install Claude Code CLI
✓ Install test dependencies (node-pty)
✓ Install amplihack from branch
✓ Verify plugin deployment
✓ Run PTY test
  → ✓ TEST PASSED: amplihack plugin detected!
✓ Upload test evidence
```

### Failure Scenarios

#### Missing API Key
```
✗ Install Claude Code CLI
  Error: ANTHROPIC_API_KEY not set
```

**Fix**: Add secret to repository settings

#### node-pty Compilation Failure
```
✗ Install test dependencies (node-pty)
  Error: Could not compile native module
```

**Fix**: Usually works on ubuntu-latest runner. Check Node.js version.

#### Plugin Not Installed
```
✗ Run PTY test
  Error: Plugin directory not found
```

**Fix**: Check uvx installation step succeeded

---

## 🔍 Debugging CI Failures

### Step 1: Check Workflow Logs

Go to: **Actions** tab > **Claude Code Plugin Test** > Click failed run

### Step 2: Download Evidence Artifacts

1. Scroll to bottom of workflow run
2. Download `plugin-test-evidence` artifact
3. Extract and check `output.txt` and `REPORT.md`

### Step 3: Check Secrets

Verify `ANTHROPIC_API_KEY` is set:
- Settings > Secrets > Actions
- Should see `ANTHROPIC_API_KEY` in list (value is hidden)

### Step 4: Run Locally

```bash
# Clone and checkout branch
git clone https://github.com/rysweet/amplihack.git
cd amplihack
git checkout feat/issue-1948-plugin-architecture

# Set API key
export ANTHROPIC_API_KEY="your-key-here"

# Run test
cd tests/agentic
npm install
node test-claude-plugin-pty.js
```

---

## 🎛️ CI Configuration Options

### Disable Tests Temporarily

Add to workflow file:
```yaml
if: false  # Disable entire job
```

### Test Only on PR (Not Push)

```yaml
on:
  pull_request:
    branches:
      - main
  # Remove push trigger
```

### Test Only When Tests Change

```yaml
on:
  push:
    paths:
      - 'tests/agentic/**'
      - '.github/workflows/plugin-test.yml'
```

---

## 📋 Pre-Merge Checklist

Before merging PR #1973, verify:

- [ ] ANTHROPIC_API_KEY secret added to repository
- [ ] Workflow file in `.github/workflows/plugin-test.yml`
- [ ] Local test passes: `node test-claude-plugin-pty.js`
- [ ] CI test passes (or runs with evidence uploaded)
- [ ] Evidence artifacts viewable in Actions tab
- [ ] Test documentation complete

---

## 🔮 Future Enhancements

### 1. Cache Plugin Installation

```yaml
- name: Cache amplihack installation
  uses: actions/cache@v3
  with:
    path: ~/.amplihack
    key: amplihack-${{ github.sha }}
```

### 2. Matrix Testing

Test across multiple platforms:
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
```

### 3. Test Multiple Branches

```yaml
strategy:
  matrix:
    branch: [main, feat/issue-1948-plugin-architecture]
```

### 4. Scheduled Tests

Run tests daily:
```yaml
on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight
```

---

## 📞 Support

**If CI tests fail:**

1. Check workflow logs in Actions tab
2. Download evidence artifacts
3. Review `CI_REQUIREMENTS.md` (this file)
4. Check GitHub secrets are set
5. Run test locally with same Node/Python versions

**Common Issues**:
- Missing ANTHROPIC_API_KEY secret
- node-pty compilation issues (rare on ubuntu-latest)
- Network issues fetching from GitHub
- Timing issues (increase sleep times in test)

---

**🏴‍☠️ Important Note**:

The tests use `continue-on-error: true` during initial CI setup. Once CI is stable with ANTHROPIC_API_KEY configured, change to `continue-on-error: false` to enforce test passing.

---

*Generated for PR #1973 - Claude Code Plugin Architecture*
*2026-01-20*
