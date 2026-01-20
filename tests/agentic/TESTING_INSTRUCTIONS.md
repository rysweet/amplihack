# Testing Instructions for PR #1973

**Feature**: Claude Code Plugin Architecture
**PR**: #1973
**Branch**: `feat/issue-1948-plugin-architecture`

---

## 🎯 What This Tests

This validates that amplihack successfully installs as a Claude Code plugin and appears in the `/plugin` command.

---

## 🚀 Quick Test (UVX + Manual)

### Prerequisites

- `uvx` installed: `pip install pipx && pipx install uv`
- `claude` (Claude Code CLI) installed
- Clean test environment (backup `~/.claude/` if you have one)

### Test Steps

```bash
# 1. Install amplihack from feature branch
uvx --refresh --from git+https://github.com/rysweet/amplihack@feat/issue-1948-plugin-architecture amplihack

# 2. Verify deployment
ls -lh ~/.amplihack/.claude/AMPLIHACK.md  # Should show ~33KB file
find ~/.amplihack/.claude/skills -maxdepth 1 -type d | wc -l  # Should show 80+ skills

# 3. Create test directory
cd /tmp && mkdir test_plugin_$(date +%s) && cd $_

# 4. Launch Claude Code with plugin directory
claude --plugin-dir ~/.amplihack/.claude/ --add-dir .
```

**In Claude Code TUI:**
1. Press `Enter` to confirm folder permission
2. Type: `/plugin`
3. Press `Enter` to execute
4. Press `Tab` to navigate to "Installed" tab
5. **VERIFY**: You should see `❯ amplihack Plugin · inline · ✔ enabled`

**Expected Result**: ✅ amplihack appears in the Installed plugins list

---

## 🤖 Automated Test (PTY)

### Prerequisites

- Node.js installed
- `uvx` and `claude` available
- amplihack installed (from UVX command above)

### Run Automated Test

```bash
# Navigate to test directory
cd /path/to/amplihack-claude-plugin/tests/agentic

# Install dependencies (one-time)
npm install

# Run the test
node test-claude-plugin-pty.js
```

### Expected Output

```
[4:07:28 PM] Starting Claude Code Plugin PTY Test
✓ Plugin directory found: /home/azureuser/.amplihack/.claude
✓ AMPLIHACK.md exists (32.3KB)
[4:07:28 PM] Spawning Claude Code with PTY...
✓ PTY spawned (PID: 1893439)
[4:07:31 PM] Confirming folder permission...
[4:07:34 PM] Sending /plugin command...
[4:07:35 PM] Executing /plugin command...
[4:07:38 PM] Navigating to Installed tab...
✓ Found "amplihack" in output!
[4:07:43 PM] Process exited (code: 0, signal: 1)
✓ Evidence saved: evidence/pty-test-*/output.txt
✓ Report saved: evidence/pty-test-*/REPORT.md

==================================================
✓ TEST PASSED: amplihack plugin detected!
==================================================
```

### Evidence Files

After the test runs, check:
```bash
ls -lh evidence/pty-test-*/
cat evidence/pty-test-*/REPORT.md
cat evidence/pty-test-*/output.txt  # Full terminal output with ANSI codes
```

---

## 📋 Verification Checklist

- [ ] Plugin installs to `~/.amplihack/.claude/`
- [ ] AMPLIHACK.md exists (32-33KB)
- [ ] 80+ skills deployed
- [ ] plugin.json manifest valid
- [ ] Claude Code launches with `--plugin-dir` flag
- [ ] `/plugin` command executes
- [ ] "Installed" tab shows amplihack
- [ ] Plugin shows as enabled with checkmark ✔

---

## 🏴‍☠️ Test Results from Development

**Date**: 2026-01-20
**Environment**: Ubuntu Linux, Claude Code v2.1.6

### Manual Test: ✅ PASSED
- Plugin visible in Installed tab
- Shown as: `❯ amplihack Plugin · inline · ✔ enabled`

### Automated Test: ✅ PASSED
- PTY test detected "amplihack" in output
- Evidence captured in `evidence/pty-test-1768925248693/`

**Evidence Extract**:
```
❯ amplihack Plugin · inline · ✔ enabled
```

---

## 🔍 Troubleshooting

### Issue: "Plugin directory not found"

**Solution**: Run the UVX install command first:
```bash
uvx --refresh --from git+https://github.com/rysweet/amplihack@feat/issue-1948-plugin-architecture amplihack
```

### Issue: "Claude Code not found"

**Solution**: Install Claude Code CLI:
```bash
npm install -g @anthropic-ai/claude-code
```

### Issue: "amplihack not showing in Installed tab"

**Debug Steps**:
1. Check plugin manifest: `cat ~/.amplihack/.claude/.claude-plugin/plugin.json`
2. Verify AMPLIHACK.md: `ls -lh ~/.amplihack/.claude/AMPLIHACK.md`
3. Check Claude Code loads plugin: Look for tweakcc or other indicators
4. Restart Claude Code with fresh session

### Issue: "Automated test fails"

**Solution**:
1. Ensure amplihack is installed first
2. Check node-pty installed: `npm list node-pty`
3. Run manual test first to verify plugin works
4. Check evidence logs: `cat evidence/pty-test-*/output.txt`

---

## 📊 Test Coverage

This test validates:

| Component | Test Type | Status |
|-----------|-----------|--------|
| Installation (uvx) | Manual | ✅ |
| File Deployment | Automated | ✅ |
| Plugin Manifest | Automated | ✅ |
| Claude Code Launch | Automated | ✅ |
| /plugin Command | Automated | ✅ |
| Plugin Detection | Automated | ✅ |

---

## 🎓 Technical Details

**Why PTY Testing?**

TUI applications like Claude Code require a real terminal (TTY). Our test uses **node-pty** to create a pseudo-terminal (PTY), which:

- ✅ Makes Claude Code think it's running in a real terminal
- ✅ Works in CI/CD without a display
- ✅ Captures all output including ANSI codes
- ✅ Enables automated TUI testing

**How It Works**:
```javascript
const pty = require('node-pty');

// Creates real virtual terminal
const ptyProcess = pty.spawn('claude', [
  '--plugin-dir', '~/.amplihack/.claude/',
  '--add-dir', '/tmp'
], {
  name: 'xterm-256color',
  cols: 120,
  rows: 40
});

// Send commands
ptyProcess.write('/plugin\r');

// Capture output
ptyProcess.onData((data) => {
  if (data.includes('amplihack')) {
    console.log('✓ Plugin detected!');
  }
});
```

---

## 📚 Related Documentation

- **Main README**: `tests/agentic/README.md`
- **PTY Explanation**: `tests/agentic/PTY_TESTING_EXPLAINED.md`
- **Implementation Summary**: `tests/agentic/IMPLEMENTATION_SUMMARY.md`
- **Test Source**: `tests/agentic/test-claude-plugin-pty.js`

---

**Generated for PR #1973**
*2026-01-20 - amplihack agentic testing*
