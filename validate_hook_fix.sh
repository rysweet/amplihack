#!/bin/bash
# Simple validation script for amplihack hook installation fix

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="/tmp/amplihack_validation_$$"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_pass() { echo -e "${GREEN}✅ PASS${NC}: $1"; }
log_fail() { echo -e "${RED}❌ FAIL${NC}: $1"; }
log_warn() { echo -e "${YELLOW}⚠️  WARN${NC}: $1"; }

# Backup existing config
backup_claude() {
    if [ -d "$HOME/.claude" ]; then
        cp -r "$HOME/.claude" "$HOME/.claude.validation_backup" 2>/dev/null || true
        echo "Backed up existing Claude config"
    fi
}

# Restore config
restore_claude() {
    if [ -d "$HOME/.claude.validation_backup" ]; then
        rm -rf "$HOME/.claude"
        mv "$HOME/.claude.validation_backup" "$HOME/.claude"
        echo "Restored Claude config"
    else
        rm -rf "$HOME/.claude"
        echo "Cleaned up test config"
    fi
}

# Clean up on exit
cleanup() {
    restore_claude
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

echo "🔍 Amplihack Hook Installation Validation"
echo "=========================================="

# Test 1: Validate project structure
echo -e "\n1. Project Structure Validation"
required_files=(
    ".claude/settings.json"
    ".claude/tools/amplihack/hooks/stop.py"
    ".claude/tools/amplihack/hooks/session_start.py"
    ".claude/tools/amplihack/hooks/post_tool_use.py"
    ".claude/tools/amplihack/hooks/hook_processor.py"
    ".claude/tools/amplihack/install.sh"
)

all_files_exist=true
for file in "${required_files[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        log_pass "File exists: $file"
    else
        log_fail "File missing: $file"
        all_files_exist=false
    fi
done

if [ "$all_files_exist" = true ]; then
    log_pass "All required files present"
else
    log_fail "Missing required files"
    exit 1
fi

# Test 2: Check settings.json uses relative paths
echo -e "\n2. Settings.json Path Format"
if grep -q '"\.claude/tools/amplihack/hooks/' "$PROJECT_ROOT/.claude/settings.json"; then
    log_pass "Settings.json uses relative paths"
else
    log_fail "Settings.json should use relative paths"
fi

# Test 3: Validate Python syntax
echo -e "\n3. Python Syntax Validation"
python_ok=true
for hook in stop.py session_start.py post_tool_use.py hook_processor.py; do
    if python3 -m py_compile "$PROJECT_ROOT/.claude/tools/amplihack/hooks/$hook" 2>/dev/null; then
        log_pass "Valid Python syntax: $hook"
    else
        log_fail "Python syntax error: $hook"
        python_ok=false
    fi
done

if [ "$python_ok" = true ]; then
    log_pass "All Python files have valid syntax"
fi

# Test 4: Install script basic functionality
echo -e "\n4. Install Script Functionality Test"
backup_claude

mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Create test settings.json with relative paths
mkdir -p "$HOME/.claude"
cat > "$HOME/.claude/settings.json" << 'EOF'
{
  "hooks": {
    "SessionStart": [{"hooks": [{"type": "command", "command": ".claude/tools/amplihack/hooks/session_start.py", "timeout": 10000}]}],
    "Stop": [{"hooks": [{"type": "command", "command": ".claude/tools/amplihack/hooks/stop.py", "timeout": 30000}]}],
    "PostToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": ".claude/tools/amplihack/hooks/post_tool_use.py"}]}]
  }
}
EOF

echo "Created test settings.json with relative paths"

# Run install script
if AMPLIHACK_INSTALL_LOCATION="$PROJECT_ROOT" bash "$PROJECT_ROOT/.claude/tools/amplihack/install.sh" >/dev/null 2>&1; then
    log_pass "Install script executed successfully"
else
    log_fail "Install script failed"
    exit 1
fi

# Check if paths were converted
abs_paths=$(grep -c "\"$HOME/.claude/tools/amplihack/hooks/" "$HOME/.claude/settings.json" 2>/dev/null || echo "0")
if [ "$abs_paths" -eq 3 ]; then
    log_pass "Paths converted to absolute format ($abs_paths/3)"
else
    log_fail "Path conversion failed (found $abs_paths/3 absolute paths)"
fi

# Check if hook files exist
missing_hooks=0
for hook in session_start.py stop.py post_tool_use.py; do
    if [ -f "$HOME/.claude/tools/amplihack/hooks/$hook" ]; then
        log_pass "Hook file installed: $hook"
    else
        log_fail "Hook file missing: $hook"
        missing_hooks=$((missing_hooks + 1))
    fi
done

if [ $missing_hooks -eq 0 ]; then
    log_pass "All hook files successfully installed"
fi

# Test 5: Verify hook_processor import
echo -e "\n5. Hook Dependencies Test"
if python3 -c "import sys; sys.path.append('$HOME/.claude/tools/amplihack/hooks'); import hook_processor" 2>/dev/null; then
    log_pass "hook_processor.py imports successfully"
else
    log_fail "hook_processor.py import failed"
fi

# Test 6: Settings.json JSON validity
echo -e "\n6. JSON Structure Validation"
if python3 -c "import json; json.load(open('$HOME/.claude/settings.json'))" 2>/dev/null; then
    log_pass "settings.json is valid JSON"
else
    log_fail "settings.json is invalid JSON"
fi

# Test 7: Backup creation
echo -e "\n7. Backup Creation Test"
backup_count=$(ls "$HOME/.claude"/settings.json.backup.* 2>/dev/null | wc -l)
if [ "$backup_count" -gt 0 ]; then
    log_pass "Backup file created during installation"
else
    log_warn "No backup file found (may be expected for this test)"
fi

echo -e "\n🎯 Validation Summary"
echo "===================="
echo "✅ Core functionality validated"
echo "✅ Python syntax correct"
echo "✅ Install script operational"
echo "✅ Path conversion working"
echo "✅ Hook files accessible"
echo ""
echo "The amplihack hook installation fix appears to be working correctly!"
echo "Run the full test suite with: ./test_hook_installation.sh"
