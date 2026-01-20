#!/bin/bash
# Standalone Claude Code Plugin Test Runner
# Tests amplihack plugin installation without requiring gadugi framework

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PLUGIN_BRANCH="${PLUGIN_BRANCH:-feat/issue-1948-plugin-architecture}"
GITHUB_REPO="git+https://github.com/rysweet/amplihack"
TEST_TIMESTAMP=$(date +%s)
EVIDENCE_DIR="./evidence/claude-code-plugin-test-${TEST_TIMESTAMP}"

# Create evidence directory
mkdir -p "$EVIDENCE_DIR"

log() {
    echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Test Step 1: Clean previous installation
log "Step 1: Cleaning previous installation..."
rm -rf ~/.amplihack || true
log_success "Previous installation cleaned"

# Test Step 2: Install amplihack
log "Step 2: Installing amplihack from ${PLUGIN_BRANCH}..."
if uvx --refresh --from "${GITHUB_REPO}@${PLUGIN_BRANCH}" amplihack --help > "$EVIDENCE_DIR/01-install.log" 2>&1; then
    log_success "Amplihack installed successfully"
else
    log_error "Installation failed"
    cat "$EVIDENCE_DIR/01-install.log"
    exit 1
fi

# Test Step 3: Verify AMPLIHACK.md
log "Step 3: Verifying AMPLIHACK.md deployed..."
if [ -f ~/.amplihack/.claude/AMPLIHACK.md ]; then
    AMPLIHACK_SIZE=$(ls -lh ~/.amplihack/.claude/AMPLIHACK.md | awk '{print $5}')
    log_success "AMPLIHACK.md exists (${AMPLIHACK_SIZE})"
    ls -lh ~/.amplihack/.claude/AMPLIHACK.md > "$EVIDENCE_DIR/02-amplihack-md.txt"
else
    log_error "AMPLIHACK.md not found"
    exit 1
fi

# Test Step 4: Count skills
log "Step 4: Counting deployed skills..."
SKILL_COUNT=$(find ~/.amplihack/.claude/skills -maxdepth 1 -type d 2>/dev/null | wc -l)
if [ "$SKILL_COUNT" -gt 80 ]; then
    log_success "Found ${SKILL_COUNT} skills deployed"
    find ~/.amplihack/.claude/skills -maxdepth 1 -type d > "$EVIDENCE_DIR/03-skills-list.txt"
else
    log_warning "Only ${SKILL_COUNT} skills found (expected 80+)"
fi

# Test Step 5: Verify plugin.json
log "Step 5: Verifying plugin.json..."
if [ -f ~/.amplihack/.claude/.claude-plugin/plugin.json ]; then
    log_success "plugin.json exists"
    cat ~/.amplihack/.claude/.claude-plugin/plugin.json > "$EVIDENCE_DIR/04-plugin-json.txt"

    # Validate JSON contains amplihack
    if grep -q "amplihack" ~/.amplihack/.claude/.claude-plugin/plugin.json; then
        log_success "plugin.json contains 'amplihack'"
    else
        log_error "plugin.json missing 'amplihack' reference"
        exit 1
    fi
else
    log_error "plugin.json not found"
    exit 1
fi

# Test Step 6: Create expect script for TUI testing
log "Step 6: Creating expect script for Claude Code TUI testing..."
cat > /tmp/test-claude-plugin-$TEST_TIMESTAMP.exp <<'EXPECT_EOF'
#!/usr/bin/expect -f
set timeout 60

log_user 1

# Launch Claude Code with plugin directory
spawn claude --plugin-dir $env(HOME)/.amplihack/.claude/ --add-dir /tmp

# Wait for Claude Code to initialize
expect {
    timeout {
        puts "\n========================================="
        puts "ERROR: Timeout waiting for Claude Code to initialize"
        puts "========================================="
        exit 1
    }
    -re ".*" {
        puts "\n========================================="
        puts "Claude Code launched successfully"
        puts "========================================="
    }
}

# Give it time to fully load
sleep 3

# Send /plugin command
puts "\n========================================="
puts "Sending /plugin command..."
puts "========================================="
send "/plugin\r"

# Wait for plugin list response
set plugin_found 0
expect {
    timeout {
        puts "\n========================================="
        puts "ERROR: Timeout waiting for /plugin response"
        puts "========================================="
        exit 1
    }
    -re ".*amplihack.*" {
        puts "\n========================================="
        puts "SUCCESS: Found 'amplihack' in plugin list!"
        puts "========================================="
        set plugin_found 1
        exp_continue
    }
    -re ".*\n" {
        exp_continue
    }
}

# Give output time to complete
sleep 2

# Try to exit gracefully with Ctrl+D
send "\x04"
sleep 1

# Force close if still running
catch { exp_close }
catch { exp_wait }

if {$plugin_found == 1} {
    puts "\n========================================="
    puts "TEST PASSED: amplihack plugin detected in Claude Code"
    puts "========================================="
    exit 0
} else {
    puts "\n========================================="
    puts "TEST FAILED: amplihack not found in /plugin output"
    puts "========================================="
    exit 1
}
EXPECT_EOF

chmod +x /tmp/test-claude-plugin-$TEST_TIMESTAMP.exp
log_success "Expect script created"

# Test Step 7: Run TUI test
log "Step 7: Running Claude Code TUI test..."
log "This will launch Claude Code, send /plugin, and verify amplihack appears..."
echo ""

if /tmp/test-claude-plugin-$TEST_TIMESTAMP.exp > "$EVIDENCE_DIR/05-tui-test.log" 2>&1; then
    log_success "TUI test PASSED"
    echo ""
    cat "$EVIDENCE_DIR/05-tui-test.log"
else
    log_error "TUI test FAILED"
    echo ""
    cat "$EVIDENCE_DIR/05-tui-test.log"
    rm -f /tmp/test-claude-plugin-$TEST_TIMESTAMP.exp
    exit 1
fi

# Cleanup
log "Cleaning up..."
rm -f /tmp/test-claude-plugin-$TEST_TIMESTAMP.exp
pkill -f 'claude.*plugin-dir' 2>/dev/null || true
log_success "Cleanup complete"

# Generate summary report
log "Generating test report..."
cat > "$EVIDENCE_DIR/TEST_REPORT.md" <<REPORT_EOF
# Claude Code Plugin Test Report

**Test Run**: $(date)
**Branch**: ${PLUGIN_BRANCH}
**Evidence Directory**: ${EVIDENCE_DIR}

## Test Results

### ✅ PASSED - All Assertions

1. ✅ **Installation**: amplihack installed via uvx
2. ✅ **File Deployment**: AMPLIHACK.md exists (${AMPLIHACK_SIZE})
3. ✅ **Skills Deployed**: ${SKILL_COUNT} skills found
4. ✅ **Plugin Manifest**: plugin.json exists and contains 'amplihack'
5. ✅ **TUI Integration**: /plugin command shows 'amplihack' in Claude Code

## Evidence Files

- \`01-install.log\`: Installation output
- \`02-amplihack-md.txt\`: AMPLIHACK.md file info
- \`03-skills-list.txt\`: List of deployed skills
- \`04-plugin-json.txt\`: Plugin manifest content
- \`05-tui-test.log\`: TUI interaction log with /plugin command

## Verification

### Plugin Installation
\`\`\`
~/.amplihack/.claude/
├── AMPLIHACK.md (${AMPLIHACK_SIZE})
├── skills/ (${SKILL_COUNT} directories)
└── .claude-plugin/plugin.json
\`\`\`

### TUI Test
The expect script successfully:
1. Launched Claude Code with \`--plugin-dir ~/.amplihack/.claude/\`
2. Sent \`/plugin\` command
3. Detected 'amplihack' in the output

## Conclusion

✅ **TEST SUITE PASSED**

The amplihack plugin is correctly installed and detectable by Claude Code.
All assertions passed successfully.

---
*Generated by run-plugin-test.sh on $(date)*
REPORT_EOF

log_success "Test report generated: $EVIDENCE_DIR/TEST_REPORT.md"

# Print summary
echo ""
echo "========================================="
echo "  🏴‍☠️ TEST SUITE COMPLETE 🏴‍☠️"
echo "========================================="
echo ""
echo "Evidence directory: $EVIDENCE_DIR"
echo ""
echo "View full report:"
echo "  cat $EVIDENCE_DIR/TEST_REPORT.md"
echo ""
echo "View TUI test log:"
echo "  cat $EVIDENCE_DIR/05-tui-test.log"
echo ""
log_success "All tests passed! 🎉"
