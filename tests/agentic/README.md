# Agentic Tests for Claude Code Plugin

This directory contains outside-in agentic tests fer the Claude Code plugin architecture.

## 🏴‍☠️ Quick Start

### Option 1: Node.js PTY Test (Recommended - True Virtual Terminal)

```bash
cd tests/agentic
npm install  # Install node-pty
node test-claude-plugin-pty.js
```

This uses **node-pty** to create a real pseudo-terminal (PTY):

- ✅ True virtual terminal (like SSH or tmux)
- ✅ Claude Code detects proper TTY
- ✅ Works in CI/CD without a display
- ✅ Cross-platform (Linux, macOS, Windows)
- ✅ Professional testing approach

### Option 2: Shell Script with Expect

```bash
cd tests/agentic
./run-plugin-test.sh
```

This uses **expect** for TUI automation:

- ✅ No Node.js dependencies
- ✅ Simple bash script
- ✅ Human-readable logs
- ⚠️ Requires real TTY in some cases

### View Results

After running, check:

```bash
# View test report
cat evidence/claude-code-plugin-test-*/TEST_REPORT.md

# View TUI interaction log
cat evidence/claude-code-plugin-test-*/05-tui-test.log

# View all evidence files
ls -lh evidence/claude-code-plugin-test-*/
```

## Test Files

### 1. Node.js PTY Test (Production Quality)

- **`test-claude-plugin-pty.js`**: Node.js script using node-pty
  - ✅ **Real pseudo-terminal** (PTY)
  - ✅ Works in CI/CD environments
  - ✅ Cross-platform compatible
  - ✅ Professional approach
  - **Dependency**: `node-pty` (installed via npm)

### 2. Shell Script with Expect

- **`run-plugin-test.sh`**: Standalone shell script test runner
  - ✅ No Node.js dependencies
  - ✅ Complete test coverage
  - ✅ Evidence collection
  - ✅ Clear pass/fail reporting
  - **Dependency**: `expect` (pre-installed)

### 3. Gadugi Framework Tests (Future)

- **`claude-code-plugin-test.yaml`**: Gadugi-agentic-test scenario
  - Uses multi-agent testing framework
  - Requires npm package installation
  - More sophisticated reporting
  - **Status**: Requires gadugi framework fixes

### Setup Utilities

- **`setup-plugin-test-env.sh`**: Environment setup script
  - Installs amplihack
  - Verifies deployment
  - Creates test directories
- **`package.json`**: Node.js dependencies
  - Defines node-pty dependency
  - Provides npm test scripts

## Test Architecture

### What We Test

1. **Installation** (`uvx --from git+...`)
   - Plugin deploys to `~/.amplihack/.claude/`
   - AMPLIHACK.md exists (33KB)
   - 80+ skills deployed

2. **Plugin Manifest**
   - `.claude-plugin/plugin.json` exists
   - Contains "amplihack" reference
   - Valid JSON structure

3. **Claude Code Integration**
   - Launches with `--plugin-dir` flag
   - `/plugin` command works
   - "amplihack" appears in plugin list

### How We Test - Two Approaches

#### Approach 1: node-pty (PTY Virtualization)

**What is a PTY?**
A pseudo-terminal (PTY) is a pair of virtual character devices that provide a bidirectional communication channel. One end appears to be a real terminal (for the application), the other end is controlled by a program (our test).

**How node-pty works:**

```javascript
const pty = require("node-pty");

// Creates a real virtual terminal
const ptyProcess = pty.spawn(
  "claude",
  ["--plugin-dir", "~/.amplihack/.claude/", "--add-dir", "/tmp"],
  {
    name: "xterm-256color", // Terminal type
    cols: 120, // Terminal width
    rows: 40, // Terminal height
    env: { TERM: "xterm-256color" },
  }
);

// Send input
ptyProcess.write("/plugin\r");

// Receive output
ptyProcess.onData((data) => {
  if (data.includes("amplihack")) {
    console.log("Plugin detected!");
  }
});
```

**Benefits:**

- ✅ Claude Code sees a real terminal (isatty() returns true)
- ✅ Works in CI/CD (no display needed)
- ✅ TUI apps behave normally
- ✅ Captures all ANSI escape codes
- ✅ Cross-platform (same code everywhere)

#### Approach 2: expect (TCL Automation)

**How expect works:**

```tcl
#!/usr/bin/expect -f
spawn claude --plugin-dir ~/.amplihack/.claude/ --add-dir /tmp
expect "Claude"
send "/plugin\r"
expect "amplihack"
```

**Benefits:**

- ✅ No compilation needed (pure script)
- ✅ Battle-tested (since 1990)
- ✅ Human-readable logs
- ⚠️ Requires TTY in some environments

**Evidence Collection** (Both Approaches):

- Installation logs
- File listings
- TUI interaction captures
- JSON manifests
- Terminal output with ANSI codes

## Prerequisites

- **uvx**: `pip install pipx && pipx ensurepath && pipx install uv`
- **expect**: Pre-installed on most systems
- **Claude Code**: `claude` command available
- **Internet**: For uvx package fetch

## Test Outputs

### Success Output

```
========================================
  🏴‍☠️ TEST SUITE COMPLETE 🏴‍☠️
========================================

Evidence directory: ./evidence/claude-code-plugin-test-1234567890

View full report:
  cat ./evidence/claude-code-plugin-test-1234567890/TEST_REPORT.md

View TUI test log:
  cat ./evidence/claude-code-plugin-test-1234567890/05-tui-test.log

✓ All tests passed! 🎉
```

### Failure Output

Each failed assertion shows:

- ✗ Clear error message
- Evidence file location
- Debugging instructions

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Plugin Tests

on: [push, pull_request]

jobs:
  test-plugin:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: |
          pip install pipx
          pipx install uv

      - name: Run plugin test
        run: |
          cd tests/agentic
          ./run-plugin-test.sh

      - name: Upload evidence
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: plugin-test-evidence
          path: tests/agentic/evidence/
```

## Troubleshooting

### Test Times Out

**Symptom**: Expect script timeouts waiting for Claude Code

**Solutions**:

1. Check Claude Code is installed: `which claude`
2. Test manual launch: `claude --version`
3. Increase timeout in expect script (default: 60s)

### "amplihack" Not Found

**Symptom**: TUI test fails to find amplihack in /plugin output

**Debug Steps**:

1. Check installation: `ls -lh ~/.amplihack/.claude/`
2. Verify plugin.json: `cat ~/.amplihack/.claude/.claude-plugin/plugin.json`
3. Manual test:
   ```bash
   claude --plugin-dir ~/.amplihack/.claude/ --add-dir /tmp
   # Type: /plugin
   # Look for "amplihack"
   ```

### Installation Fails

**Symptom**: uvx fails to install amplihack

**Solutions**:

1. Check network: `ping github.com`
2. Verify branch exists: `git ls-remote https://github.com/rysweet/amplihack`
3. Try different branch: `PLUGIN_BRANCH=main ./run-plugin-test.sh`

## Future Enhancements

### Gadugi Framework Integration

Once gadugi-agentic-test npm package is published:

```bash
# Install framework
npm install -g @gadugi/agentic-test

# Run YAML scenario
gadugi-agentic-test run claude-code-plugin-test.yaml
```

Benefits:

- Multi-agent orchestration
- Richer reporting
- Parallel test execution
- Built-in screenshot comparison

### Additional Tests

Planned test scenarios:

- **Plugin updates**: Upgrade existing installation
- **Multiple projects**: Shared plugin across projects
- **LSP auto-detection**: Verify LSP servers configured
- **Hook execution**: Test hooks with ${CLAUDE_PLUGIN_ROOT}
- **Skill loading**: Verify all 83 skills accessible

## Philosophy Alignment

These tests follow amplihack's core principles:

### Outside-In Testing

✅ **User perspective**: Tests verify `/plugin` command (what users see)
✅ **Implementation agnostic**: Tests don't care about internal code
✅ **Behavior-driven**: Focus on observable outcomes

### Ruthless Simplicity

✅ **Minimal dependencies**: Just expect + shell
✅ **Clear evidence**: Human-readable logs
✅ **No complexity**: Straightforward bash script

### Zero-BS Implementation

✅ **No stubs**: Real Claude Code launch
✅ **Real interactions**: Actual /plugin command
✅ **Working tests**: Every test validates real behavior

## Related Documentation

- **PR #1973**: Complete plugin architecture implementation
- **Issue #1948**: Plugin system requirements
- **CLAUDE.md**: Plugin architecture design
- **outside-in-testing skill**: General agentic testing framework

---

**Remember**: These tests verify the plugin works from the user's perspective. If the test passes, the plugin is working correctly!

🏴‍☠️ _"We test like a pirate: direct, honest, and focused on the treasure (working software)!"_ 🏴‍☠️
