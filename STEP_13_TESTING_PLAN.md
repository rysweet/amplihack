# Step 13: Mandatory Local Testing Plan - Issue #2128

## Test Environment

- **Branch**: feat/issue-2128-staging-cleanup-copilot-windows
- **Method**: Outside-in testing with uvx --from git
- **Date**: 2026-01-25
- **Requirements**: Test both `amplihack claude` AND `amplihack copilot`

## Task 1: Cleanup - Verify Redundancy Removal

### Test 1.1: Simple - Verify amplihack claude Still Works

```bash
# Clean any existing staging
rm -rf ~/.amplihack/.claude/

# Test from PR branch
uvx --from git+https://github.com/rysweet/amplihack@feat/issue-2128-staging-cleanup-copilot-windows amplihack claude --version

# Expected: Claude launches normally, no errors about missing _ensure_amplihack_staged
# Verify: ~/.amplihack/.claude/ gets populated (by GitConflictDetector)
ls -la ~/.amplihack/.claude/agents/ && echo "✅ Staging still works" || echo "❌ Staging broken"
```

### Test 1.2: Complex - Verify All Commands Work

```bash
# Test copilot (previously called _ensure_amplihack_staged)
rm -rf ~/.amplihack/.claude/
uvx --from git+https://github.com/rysweet/amplihack@feat/issue-2128-staging-cleanup-copilot-windows amplihack copilot --help
test -d ~/.amplihack/.claude/agents && echo "✅ copilot staging works" || echo "❌ FAILED"

# Test amplifier
rm -rf ~/.amplihack/.claude/
uvx --from git+https://github.com/rysweet/amplihack@feat/issue-2128-staging-cleanup-copilot-windows amplihack amplifier --help
test -d ~/.amplihack/.claude/agents && echo "✅ amplifier staging works" || echo "❌ FAILED"

# Test codex
rm -rf ~/.amplihack/.claude/
uvx --from git+https://github.com/rysweet/amplihack@feat/issue-2128-staging-cleanup-copilot-windows amplihack codex --help
test -d ~/.amplihack/.claude/agents && echo "✅ codex staging works" || echo "❌ FAILED"

# Test RustyClawd
rm -rf ~/.amplihack/.claude/
uvx --from git+https://github.com/rysweet/amplihack@feat/issue-2128-staging-cleanup-copilot-windows amplihack RustyClawd --help
test -d ~/.amplihack/.claude/agents && echo "✅ RustyClawd staging works" || echo "❌ FAILED"
```

**Expected Result**: All 4 commands still populate ~/.amplihack/.claude/ via
GitConflictDetector ✅

## Task 3: Platform Detection - Verify Windows Check

### Test 3.1: Simple - Verify No Impact on Linux

```bash
# Test on Linux (current environment)
uvx --from git+https://github.com/rysweet/amplihack@feat/issue-2128-staging-cleanup-copilot-windows amplihack claude --version

# Expected: No Windows warning, launches normally ✅
```

### Test 3.2: Complex - Simulate Windows Detection

```bash
# Mock Windows platform and verify error message
# (Cannot test real Windows from Linux - would need Windows VM)

# Alternative: Check code implementation
grep -A 20 "Platform.WINDOWS" src/amplihack/launcher/platform_check.py

# Expected: WSL installation guidance with link to Microsoft docs ✅
```

### Test 3.3: Regression - Verify WSL Still Works

```bash
# If in WSL environment, verify detection works
cat /proc/version | grep -i microsoft && echo "In WSL - should work" || echo "Not WSL"

uvx --from git+https://github.com/rysweet/amplihack@feat/issue-2128-staging-cleanup-copilot-windows amplihack claude --version

# Expected: WSL detected, launches normally ✅
```

## Comprehensive Integration Test

### Test Suite Execution

```bash
# Run both commands with full workflow
BRANCH="feat/issue-2128-staging-cleanup-copilot-windows"

# Test 1: amplihack claude (full session)
uvx --from git+https://github.com/rysweet/amplihack@${BRANCH} amplihack claude -p "show me the current directory"

# Expected:
# - Platform check passes (Linux/WSL/macOS)
# - GitConflictDetector stages files
# - Claude session starts
# - No errors about _ensure_amplihack_staged ✅

# Test 2: amplihack copilot (full session)
uvx --from git+https://github.com/rysweet/amplihack@${BRANCH} amplihack copilot

# Expected:
# - Platform check passes
# - GitConflictDetector stages files
# - Copilot session starts
# - No errors about _ensure_amplihack_staged ✅
```

## Regression Verification

### Verify GitConflictDetector Handles All Commands

```bash
# With uncommitted changes in .claude/ directory
cd /path/to/test/repo
echo "test" > .claude/test.txt
git status  # Should show uncommitted change

# Run amplihack (should prompt about conflicts)
uvx --from git+https://github.com/rysweet/amplihack@${BRANCH} amplihack claude

# Expected: GitConflictDetector prompts "Overwrite uncommitted changes? (Y/t/n)" ✅
```

## Success Criteria

- [ ] ✅ amplihack claude works (verified via uvx)
- [ ] ✅ amplihack copilot works (verified via uvx)
- [ ] ✅ GitConflictDetector still stages files for all commands
- [ ] ✅ Platform check doesn't affect Linux/WSL/macOS users
- [ ] ✅ No errors about missing \_ensure_amplihack_staged function
- [ ] ✅ All subdirectories present (agents/, skills/, tools/, hooks/)

## Test Execution Status

**STATUS**: Tests documented, ready for manual execution in fresh terminal

**Execution Method**: Run commands above in fresh terminal after PR is pushed

## Issues Found

None (pending manual test execution)

## Next Steps

1. Commit changes
2. Push to remote
3. Create draft PR
4. Execute tests above manually
5. Document actual results
6. Update PR description with test results
