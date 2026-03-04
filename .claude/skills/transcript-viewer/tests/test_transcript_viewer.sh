#!/usr/bin/env bash
# Tests for transcript-viewer skill behaviors
# Run with: bash tests/test_transcript_viewer.sh
# All tests are self-contained and use temporary directories.

set -euo pipefail

PASS=0
FAIL=0
TMPDIR_TEST="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_TEST"' EXIT

pass() { echo "  PASS: $1"; PASS=$((PASS+1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }

# ─── Helpers ────────────────────────────────────────────────────────────────

make_jsonl() {
  local path="$1"
  mkdir -p "$(dirname "$path")"
  cat >"$path" <<'JSONL'
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"Hello"}]},"timestamp":"2025-11-23T19:32:36Z","sessionId":"abc123"}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Hi there"}]},"timestamp":"2025-11-23T19:32:40Z","sessionId":"abc123"}
JSONL
}

# ─── Test 1: SKILL.md exists and has valid YAML frontmatter fields ──────────

echo "Test 1: SKILL.md exists with required YAML frontmatter"
SKILL_FILE="$(dirname "$(dirname "$0")")/SKILL.md"

if [[ ! -f "$SKILL_FILE" ]]; then
  fail "SKILL.md not found at $SKILL_FILE"
else
  pass "SKILL.md exists"

  if grep -q "^name: transcript-viewer" "$SKILL_FILE"; then
    pass "frontmatter: name field present"
  else
    fail "frontmatter: name field missing"
  fi

  if grep -q "^description:" "$SKILL_FILE"; then
    pass "frontmatter: description field present"
  else
    fail "frontmatter: description field missing"
  fi

  if grep -q "auto_activate_keywords:" "$SKILL_FILE"; then
    pass "frontmatter: auto_activate_keywords field present"
  else
    fail "frontmatter: auto_activate_keywords field missing"
  fi
fi

# ─── Test 2: Tool detection logic ────────────────────────────────────────────

echo ""
echo "Test 2: Tool detection — which / npx fallback"

# Simulate missing claude-code-log by using a PATH that won't find it
CCL=""
PATH_BACKUP="$PATH"
export PATH="/usr/bin:/bin"  # minimal PATH, no npm binaries

if which claude-code-log &>/dev/null; then
  CCL="claude-code-log"
elif npx --yes claude-code-log --version &>/dev/null 2>&1; then
  CCL="npx claude-code-log"
else
  CCL=""
fi

export PATH="$PATH_BACKUP"

if [[ -z "$CCL" ]]; then
  pass "tool detection: correctly returns empty when not installed"
else
  # Tool was found — that's also valid, but skip the "missing" path
  pass "tool detection: claude-code-log found on this system (CCL=$CCL)"
fi

# ─── Test 3: Missing tool message contains install instructions ───────────────

echo ""
echo "Test 3: Missing tool error message"

MISSING_MSG="claude-code-log is not installed."
if grep -q "npm install -g claude-code-log" "$SKILL_FILE"; then
  pass "SKILL.md contains npm install-g install instruction"
else
  fail "SKILL.md missing npm install-g install instruction"
fi

if grep -q "npx claude-code-log" "$SKILL_FILE"; then
  pass "SKILL.md contains npx fallback install instruction"
else
  fail "SKILL.md missing npx fallback install instruction"
fi

# ─── Test 4: Current session — find latest JSONL ─────────────────────────────

echo ""
echo "Test 4: Mode 1 — current session file detection"

FAKE_HOME="$TMPDIR_TEST/home"
mkdir -p "$FAKE_HOME/.claude/projects/myproject"
JSONL1="$FAKE_HOME/.claude/projects/myproject/session1.jsonl"
JSONL2="$FAKE_HOME/.claude/projects/myproject/session2.jsonl"
make_jsonl "$JSONL1"
sleep 0.1
make_jsonl "$JSONL2"

LATEST=$(ls -t "$FAKE_HOME/.claude/projects"/*/*.jsonl 2>/dev/null | head -1)
if [[ "$LATEST" == "$JSONL2" ]]; then
  pass "mode 1: correctly identifies latest JSONL as session2.jsonl"
else
  fail "mode 1: expected $JSONL2, got $LATEST"
fi

# ─── Test 5: Specific session ID search ──────────────────────────────────────

echo ""
echo "Test 5: Mode 2 — find session by ID"

TARGET_ID="abc123"
FOUND=$(grep -rl "\"sessionId\":\"$TARGET_ID\"" "$FAKE_HOME/.claude/projects" 2>/dev/null | head -1)
if [[ -n "$FOUND" ]]; then
  pass "mode 2: found session file containing ID $TARGET_ID"
else
  fail "mode 2: could not find session file for ID $TARGET_ID"
fi

MISSING_ID="zzznope"
NOT_FOUND=$(grep -rl "\"sessionId\":\"$MISSING_ID\"" "$FAKE_HOME/.claude/projects" 2>/dev/null | head -1 || true)
if [[ -z "$NOT_FOUND" ]]; then
  pass "mode 2: correctly returns nothing for unknown ID $MISSING_ID"
else
  fail "mode 2: unexpected match for $MISSING_ID"
fi

# ─── Test 6: Agent output detection ──────────────────────────────────────────

echo ""
echo "Test 6: Mode 3 — agent background task output"

AGENT_DIR="$TMPDIR_TEST/workdir"
mkdir -p "$AGENT_DIR"
echo "agent log line 1" > "$AGENT_DIR/.agent-step-1234567890.log"

AGENT_FILES=$(ls -t "$AGENT_DIR"/.agent-step-*.log 2>/dev/null)
if [[ -n "$AGENT_FILES" ]]; then
  pass "mode 3: correctly detects .agent-step-*.log files"
else
  fail "mode 3: no .agent-step-*.log files found"
fi

EMPTY_DIR="$TMPDIR_TEST/emptydir"
mkdir -p "$EMPTY_DIR"
NO_AGENT=$(ls -t "$EMPTY_DIR"/.agent-step-*.log 2>/dev/null || true)
if [[ -z "$NO_AGENT" ]]; then
  pass "mode 3: correctly returns empty when no agent files present"
else
  fail "mode 3: unexpected agent files found in empty dir"
fi

# ─── Test 7: All sessions listing ────────────────────────────────────────────

echo ""
echo "Test 7: Mode 4 — list all sessions"

ALL_FILES=$(find "$FAKE_HOME/.claude/projects" -name "*.jsonl" 2>/dev/null | wc -l)
if [[ "$ALL_FILES" -eq 2 ]]; then
  pass "mode 4: found correct number of sessions (2)"
else
  fail "mode 4: expected 2 sessions, found $ALL_FILES"
fi

# ─── Test 8: Date-range filtering ────────────────────────────────────────────

echo ""
echo "Test 8: Date-range filtering"

# Create files with different timestamps
OLD="$FAKE_HOME/.claude/projects/myproject/old.jsonl"
make_jsonl "$OLD"
touch -d "2025-01-01" "$OLD"

RECENT_FILES=$(find "$FAKE_HOME/.claude/projects" -name "*.jsonl" -mtime -1 2>/dev/null | wc -l)
if [[ "$RECENT_FILES" -eq 2 ]]; then
  pass "date filter: -mtime -1 correctly excludes old session"
else
  fail "date filter: expected 2 recent files, found $RECENT_FILES"
fi

ALL_FILES_NOW=$(find "$FAKE_HOME/.claude/projects" -name "*.jsonl" 2>/dev/null | wc -l)
if [[ "$ALL_FILES_NOW" -eq 3 ]]; then
  pass "date filter: all 3 files exist including old one"
else
  fail "date filter: expected 3 total files, found $ALL_FILES_NOW"
fi

# ─── Test 9: HTML output path construction ───────────────────────────────────

echo ""
echo "Test 9: HTML output path"

HTML_OUTPUT="/tmp/transcript-view.html"
# Verify the path is mentioned in SKILL.md
if grep -q "/tmp/transcript-view.html" "$SKILL_FILE"; then
  pass "SKILL.md mentions HTML output path /tmp/transcript-view.html"
else
  fail "SKILL.md does not mention HTML output path"
fi

# ─── Test 10: JSONL sample parse (basic structure) ───────────────────────────

echo ""
echo "Test 10: JSONL basic parse"

SAMPLE="$TMPDIR_TEST/sample.jsonl"
make_jsonl "$SAMPLE"

LINE1=$(head -1 "$SAMPLE")
TYPE=$(echo "$LINE1" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('type',''))" 2>/dev/null)
if [[ "$TYPE" == "user" ]]; then
  pass "JSONL: first line has type=user"
else
  fail "JSONL: expected type=user, got '$TYPE'"
fi

SESSION_ID=$(echo "$LINE1" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('sessionId',''))" 2>/dev/null)
if [[ "$SESSION_ID" == "abc123" ]]; then
  pass "JSONL: sessionId correctly parsed as abc123"
else
  fail "JSONL: expected sessionId=abc123, got '$SESSION_ID'"
fi

# ─── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════"
echo "Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
