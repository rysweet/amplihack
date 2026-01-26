# Quick Test Reference Card

**PR #1973 - Claude Code Plugin Architecture**

---

## 🏴‍☠️ ONE-LINE TEST COMMAND

```bash
uvx --refresh --from git+https://github.com/rysweet/amplihack@feat/issue-1948-plugin-architecture amplihack
```

**What this does:**

- Installs amplihack to `~/.amplihack/.claude/`
- Deploys all plugin files (AMPLIHACK.md, skills, manifest)
- Makes plugin available to Claude Code

---

## 🎯 VERIFY INSTALLATION

```bash
# Check AMPLIHACK.md deployed
ls -lh ~/.amplihack/.claude/AMPLIHACK.md

# Count skills
find ~/.amplihack/.claude/skills -maxdepth 1 -type d | wc -l

# Check plugin manifest
cat ~/.amplihack/.claude/.claude-plugin/plugin.json
```

**Expected:**

- AMPLIHACK.md: ~33KB
- Skills: 80+ directories
- plugin.json: Contains "amplihack"

---

## 🖥️ MANUAL TUI TEST

```bash
# Create test directory
cd /tmp && mkdir test_$(date +%s) && cd $_

# Launch Claude Code with plugin
claude --plugin-dir ~/.amplihack/.claude/ --add-dir .

# In Claude Code:
# 1. Press Enter (confirm folder permission)
# 2. Type: /plugin
# 3. Press Enter
# 4. Press Tab (navigate to "Installed" tab)
# 5. Look for: ❯ amplihack Plugin · inline · ✔ enabled
```

---

## 🤖 AUTOMATED TEST

```bash
cd /path/to/amplihack-claude-plugin/tests/agentic

# Install dependencies (one-time)
npm install

# Run test
node test-claude-plugin-pty.js
```

**Expected Output:**

```
✓ Plugin directory found
✓ AMPLIHACK.md exists (32.3KB)
✓ PTY spawned
✓ Found "amplihack" in output!

==================================================
✓ TEST PASSED: amplihack plugin detected!
==================================================
```

---

## 🐛 TROUBLESHOOTING

### "Plugin directory not found"

```bash
# Re-run UVX install
uvx --refresh --from git+https://github.com/rysweet/amplihack@feat/issue-1948-plugin-architecture amplihack
```

### "Claude Code not found"

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code
```

### "Test failed - amplihack not detected"

```bash
# Manual verification
cat ~/.amplihack/.claude/.claude-plugin/plugin.json
# Should contain: "amplihack"
```

---

## 📝 COPY-PASTE FOR SLACK/ISSUES

```
✅ Plugin Test Passed!

Installation:
uvx --refresh --from git+https://github.com/rysweet/amplihack@feat/issue-1948-plugin-architecture amplihack

Manual Test:
claude --plugin-dir ~/.amplihack/.claude/ --add-dir /tmp
(then type /plugin, press Tab to "Installed", look for "amplihack")

Automated Test:
cd tests/agentic && npm install && node test-claude-plugin-pty.js

Result: ✓ amplihack detected in /plugin command
```

---

**🏴‍☠️ Quick and easy, just like a pirate likes it! 🏴‍☠️**
