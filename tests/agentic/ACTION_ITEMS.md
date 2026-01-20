# Action Items for PR #1973

**Date**: 2026-01-20
**Status**: ✅ Tests complete, ready for CI setup

---

## 🎯 IMMEDIATE ACTIONS REQUIRED

### 1. Add ANTHROPIC_API_KEY to GitHub Secrets

**Where**: https://github.com/rysweet/amplihack/settings/secrets/actions

**Steps**:
1. Click **"New repository secret"**
2. Name: `ANTHROPIC_API_KEY`
3. Value: Your Anthropic API key (get from https://console.anthropic.com)
4. Click **"Add secret"**

**Why**: The Claude Code CLI needs authentication to run. Without this secret, CI tests will fail with:
```
Error: No API key found
```

---

### 2. Decide: Push to Main or Feature Branch?

**Current Situation**:
- We have 5 commits on `main` branch
- PR #1973 is on `feat/issue-1948-plugin-architecture` branch

**Option A: Push to Main (Simplest)**
```bash
git push origin main
```

**Option B: Move to Feature Branch (For PR)**
```bash
# Checkout feature branch
git checkout feat/issue-1948-plugin-architecture

# Cherry-pick our commits
git cherry-pick 367b1e4a  # Deploy fix
git cherry-pick 3b6043be  # ESSENTIAL_DIRS fix
git cherry-pick c3aa27b5  # Agentic tests
git cherry-pick 8abb7ebf  # CI workflow
git cherry-pick a2fbe1be  # CI documentation

# Push to feature branch
git push origin feat/issue-1948-plugin-architecture

# Reset main back to origin
git checkout main
git reset --hard origin/main
```

**Recommendation**: **Option B** - Move to feature branch so tests are part of PR #1973.

---

### 3. Update PR #1973 Description

Add this section to the PR description:

```markdown
## ✅ Automated Testing

This PR includes comprehensive automated TUI testing using PTY virtualization.

### Test Command (UVX)

\`\`\`bash
uvx --refresh --from git+https://github.com/rysweet/amplihack@feat/issue-1948-plugin-architecture amplihack
\`\`\`

### Automated Test Result

\`\`\`
✓ TEST PASSED: amplihack plugin detected!
\`\`\`

**Evidence**: Plugin appears in Claude Code's `/plugin` command:
\`\`\`
❯ amplihack Plugin · inline · ✔ enabled
\`\`\`

### Test Files

- `tests/agentic/test-claude-plugin-pty.js` - PTY-based automated test
- `tests/agentic/run-plugin-test.sh` - Shell-based alternative
- `.github/workflows/plugin-test.yml` - CI/CD automation

See `tests/agentic/README.md` for testing instructions.

### CI/CD Setup

⚠️ **REQUIRES**: `ANTHROPIC_API_KEY` secret in repository settings
See `tests/agentic/CI_REQUIREMENTS.md` for setup instructions.
\`\`\`
```

---

## 🔍 VERIFICATION STEPS

### After Adding API Key to Secrets

1. Push commits to feature branch
2. Go to **Actions** tab: https://github.com/rysweet/amplihack/actions
3. Find "Claude Code Plugin Test" workflow
4. Click on latest run
5. Verify both jobs:
   - `test-plugin` (PTY-based) - should ✅ pass
   - `test-plugin-shell` (expect-based) - should ✅ pass
6. Download artifacts to see evidence

### If CI Fails

1. **Check logs** in Actions tab
2. **Download evidence artifacts**:
   - `plugin-test-evidence` (from PTY test)
   - `shell-test-evidence` (from shell test)
3. **Review**:
   - `output.txt` - Full terminal capture
   - `REPORT.md` - Test summary
4. **Debug locally**:
   ```bash
   export ANTHROPIC_API_KEY="your-key"
   cd tests/agentic
   npm install
   node test-claude-plugin-pty.js
   ```

---

## 📊 What Gets Tested in CI

| Test Step | PTY Job | Shell Job |
|-----------|---------|-----------|
| Install amplihack via UVX | ✅ | ✅ |
| Verify AMPLIHACK.md deployed | ✅ | ✅ |
| Verify 80+ skills deployed | ✅ | ✅ |
| Verify plugin.json | ✅ | ✅ |
| Launch Claude Code with PTY | ✅ | ✅ |
| Send /plugin command | ✅ | ✅ |
| Detect "amplihack" | ✅ | ✅ |
| Upload evidence | ✅ | ✅ |

---

## 🎯 SUCCESS METRICS

### Local Test: ✅ PASSED
```
✓ TEST PASSED: amplihack plugin detected!
Evidence: tests/agentic/evidence/pty-test-1768925248693/
```

### Expected CI Result: ✅ PASS (after API key added)
```
✓ test-plugin job completed
✓ test-plugin-shell job completed
✓ Evidence artifacts uploaded
✓ Test summaries in workflow logs
```

---

## 🚀 THE ONE COMMAND TO TEST

**Copy-paste this to test the PR branch:**

```bash
uvx --refresh --from git+https://github.com/rysweet/amplihack@feat/issue-1948-plugin-architecture amplihack
```

**Then verify:**
```bash
claude --plugin-dir ~/.amplihack/.claude/ --add-dir /tmp
# Type: /plugin
# Press: Tab (go to Installed)
# See: ❯ amplihack Plugin · inline · ✔ enabled
```

---

## 🏴‍☠️ READY TO SAIL!

**All code committed**: ✅
**Tests passing locally**: ✅
**Documentation complete**: ✅
**CI workflow created**: ✅

**BLOCKERS**:
- ⚠️ Need ANTHROPIC_API_KEY in GitHub secrets
- ⚠️ May want to move commits to feature branch

**Once API key is added, CI will automatically test every push!** ⚓

---

*Generated 2026-01-20 - amplihack agentic testing complete*
