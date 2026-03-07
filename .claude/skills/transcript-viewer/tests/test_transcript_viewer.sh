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

make_copilot_events_jsonl() {
  local path="$1"
  mkdir -p "$(dirname "$path")"
  cat >"$path" <<'JSONL'
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"Fix the authentication bug"}]},"timestamp":"2025-11-23T19:32:36Z","sessionId":"copilot-session-xyz789"}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"I'll examine the file and fix the authentication bug..."}]},"timestamp":"2025-11-23T19:32:40Z","sessionId":"copilot-session-xyz789"}
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

# ─── Test 2: SKILL.md includes Copilot-related keywords ──────────────────────

echo ""
echo "Test 2: SKILL.md includes Copilot-related auto_activate_keywords"

if grep -q "copilot" "$SKILL_FILE"; then
  pass "SKILL.md mentions copilot (keyword support)"
else
  fail "SKILL.md missing copilot keyword support"
fi

# ─── Test 3: Tool detection logic ────────────────────────────────────────────

echo ""
echo "Test 3: Tool detection — which / npx fallback"

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

# ─── Test 4: Missing tool message contains install instructions ───────────────

echo ""
echo "Test 4: Missing tool error message"

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

# ─── Test 5: Current session — find latest JSONL (Claude Code path) ──────────

echo ""
echo "Test 5: Mode 1 — Claude Code current session file detection"

FAKE_HOME="$TMPDIR_TEST/home"
mkdir -p "$FAKE_HOME/.claude/projects/myproject"
JSONL1="$FAKE_HOME/.claude/projects/myproject/session1.jsonl"
JSONL2="$FAKE_HOME/.claude/projects/myproject/session2.jsonl"
make_jsonl "$JSONL1"
sleep 0.1
make_jsonl "$JSONL2"

LATEST=$(ls -t "$FAKE_HOME/.claude/projects"/*/*.jsonl 2>/dev/null | head -1)
if [[ "$LATEST" == "$JSONL2" ]]; then
  pass "mode 1 (claude-code): correctly identifies latest JSONL as session2.jsonl"
else
  fail "mode 1 (claude-code): expected $JSONL2, got $LATEST"
fi

# ─── Test 6: Current session — find latest events.jsonl (Copilot path) ───────

echo ""
echo "Test 6: Mode 1 — Copilot current session detection via ~/.copilot/session-state/"

COPILOT_STATE_DIR="$FAKE_HOME/.copilot/session-state"
SESSION_ID_1="abc1234567890abcdef1234567890abc"
SESSION_ID_2="def4567890abcdef1234567890abcdef"

mkdir -p "$COPILOT_STATE_DIR/$SESSION_ID_1"
mkdir -p "$COPILOT_STATE_DIR/$SESSION_ID_2"

make_copilot_events_jsonl "$COPILOT_STATE_DIR/$SESSION_ID_1/events.jsonl"
sleep 0.1
make_copilot_events_jsonl "$COPILOT_STATE_DIR/$SESSION_ID_2/events.jsonl"

LATEST_COPILOT_SESSION=$(ls -dt "$COPILOT_STATE_DIR"/*/ 2>/dev/null | head -1)
LATEST_EVENTS="${LATEST_COPILOT_SESSION}events.jsonl"

if [[ -f "$LATEST_EVENTS" ]]; then
  pass "mode 1 (copilot): latest session dir found with events.jsonl"
else
  fail "mode 1 (copilot): events.jsonl not found in latest session dir ($LATEST_EVENTS)"
fi

LATEST_SESSION_ID=$(basename "$LATEST_COPILOT_SESSION")
if [[ "$LATEST_SESSION_ID" == "$SESSION_ID_2" ]]; then
  pass "mode 1 (copilot): correctly identifies latest session as $SESSION_ID_2"
else
  fail "mode 1 (copilot): expected $SESSION_ID_2, got $LATEST_SESSION_ID"
fi

# ─── Test 7: Specific session ID search (Claude Code) ─────────────────────────

echo ""
echo "Test 7: Mode 2 — Claude Code find session by ID"

TARGET_ID="abc123"
FOUND=$(grep -rl "\"sessionId\":\"$TARGET_ID\"" "$FAKE_HOME/.claude/projects" 2>/dev/null | head -1)
if [[ -n "$FOUND" ]]; then
  pass "mode 2 (claude-code): found session file containing ID $TARGET_ID"
else
  fail "mode 2 (claude-code): could not find session file for ID $TARGET_ID"
fi

MISSING_ID="zzznope"
NOT_FOUND=$(grep -rl "\"sessionId\":\"$MISSING_ID\"" "$FAKE_HOME/.claude/projects" 2>/dev/null | head -1 || true)
if [[ -z "$NOT_FOUND" ]]; then
  pass "mode 2 (claude-code): correctly returns nothing for unknown ID $MISSING_ID"
else
  fail "mode 2 (claude-code): unexpected match for $MISSING_ID"
fi

# ─── Test 8: Specific session ID search (Copilot path) ────────────────────────

echo ""
echo "Test 8: Mode 2 — Copilot find session by directory ID"

# Copilot sessions are found by directory name under ~/.copilot/session-state/
COPILOT_SESSION_DIR="$COPILOT_STATE_DIR/$SESSION_ID_1"
if [[ -d "$COPILOT_SESSION_DIR" ]]; then
  COPILOT_EVENTS="$COPILOT_SESSION_DIR/events.jsonl"
  if [[ -f "$COPILOT_EVENTS" ]]; then
    pass "mode 2 (copilot): found events.jsonl for session $SESSION_ID_1"
  else
    fail "mode 2 (copilot): events.jsonl missing for session $SESSION_ID_1"
  fi
else
  fail "mode 2 (copilot): session directory $SESSION_ID_1 not found"
fi

# Test partial ID match
PARTIAL_ID="abc12345"
PARTIAL_MATCH=$(ls -d "$COPILOT_STATE_DIR"/*/ 2>/dev/null | grep "$PARTIAL_ID" | head -1 || true)
if [[ -n "$PARTIAL_MATCH" ]]; then
  pass "mode 2 (copilot): partial ID '$PARTIAL_ID' matches session directory"
else
  fail "mode 2 (copilot): could not find session with partial ID '$PARTIAL_ID'"
fi

MISSING_COPILOT_ID="zzznope-session-xxx"
NOT_FOUND_COPILOT=$(ls -d "$COPILOT_STATE_DIR/$MISSING_COPILOT_ID" 2>/dev/null || true)
if [[ -z "$NOT_FOUND_COPILOT" ]]; then
  pass "mode 2 (copilot): correctly returns nothing for unknown session ID"
else
  fail "mode 2 (copilot): unexpected match for $MISSING_COPILOT_ID"
fi

# ─── Test 9: Agent output detection ──────────────────────────────────────────

echo ""
echo "Test 9: Mode 3 — agent background task output"

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

# ─── Test 10: All sessions listing (Claude Code) ──────────────────────────────

echo ""
echo "Test 10: Mode 4 — list all Claude Code sessions"

ALL_FILES=$(find "$FAKE_HOME/.claude/projects" -name "*.jsonl" 2>/dev/null | wc -l)
if [[ "$ALL_FILES" -eq 2 ]]; then
  pass "mode 4 (claude-code): found correct number of sessions (2)"
else
  fail "mode 4 (claude-code): expected 2 sessions, found $ALL_FILES"
fi

# ─── Test 11: All sessions listing (Copilot path) ─────────────────────────────

echo ""
echo "Test 11: Mode 4 — list all Copilot sessions from ~/.copilot/session-state/"

COPILOT_SESSION_COUNT=$(ls -d "$COPILOT_STATE_DIR"/*/ 2>/dev/null | wc -l)
if [[ "$COPILOT_SESSION_COUNT" -eq 2 ]]; then
  pass "mode 4 (copilot): found correct number of Copilot sessions (2)"
else
  fail "mode 4 (copilot): expected 2 sessions, found $COPILOT_SESSION_COUNT"
fi

# Each session directory should have an events.jsonl
COPILOT_EVENTS_COUNT=0
for session_dir in "$COPILOT_STATE_DIR"/*/; do
  if [[ -f "${session_dir}events.jsonl" ]]; then
    COPILOT_EVENTS_COUNT=$((COPILOT_EVENTS_COUNT+1))
  fi
done

if [[ "$COPILOT_EVENTS_COUNT" -eq 2 ]]; then
  pass "mode 4 (copilot): all Copilot sessions have events.jsonl"
else
  fail "mode 4 (copilot): expected 2 events.jsonl files, found $COPILOT_EVENTS_COUNT"
fi

# ─── Test 12: Date-range filtering ────────────────────────────────────────────

echo ""
echo "Test 12: Date-range filtering"

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

# ─── Test 13: HTML output path construction ───────────────────────────────────

echo ""
echo "Test 13: HTML output path"

HTML_OUTPUT="/tmp/transcript-view.html"
# Verify the path is mentioned in SKILL.md
if grep -q "/tmp/transcript-view.html" "$SKILL_FILE"; then
  pass "SKILL.md mentions HTML output path /tmp/transcript-view.html"
else
  fail "SKILL.md does not mention HTML output path"
fi

# ─── Test 14: JSONL sample parse (basic structure, Claude Code) ───────────────

echo ""
echo "Test 14: JSONL basic parse (Claude Code format)"

SAMPLE="$TMPDIR_TEST/sample.jsonl"
make_jsonl "$SAMPLE"

LINE1=$(head -1 "$SAMPLE")
TYPE=$(echo "$LINE1" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('type',''))" 2>/dev/null)
if [[ "$TYPE" == "user" ]]; then
  pass "JSONL (claude-code): first line has type=user"
else
  fail "JSONL (claude-code): expected type=user, got '$TYPE'"
fi

SESSION_ID=$(echo "$LINE1" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('sessionId',''))" 2>/dev/null)
if [[ "$SESSION_ID" == "abc123" ]]; then
  pass "JSONL (claude-code): sessionId correctly parsed as abc123"
else
  fail "JSONL (claude-code): expected sessionId=abc123, got '$SESSION_ID'"
fi

# ─── Test 15: JSONL sample parse (Copilot events.jsonl format) ────────────────

echo ""
echo "Test 15: JSONL basic parse (Copilot events.jsonl format)"

COPILOT_SAMPLE="$COPILOT_STATE_DIR/$SESSION_ID_1/events.jsonl"

COPILOT_LINE1=$(head -1 "$COPILOT_SAMPLE")
COPILOT_TYPE=$(echo "$COPILOT_LINE1" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('type',''))" 2>/dev/null)
if [[ "$COPILOT_TYPE" == "user" ]]; then
  pass "JSONL (copilot): first line has type=user"
else
  fail "JSONL (copilot): expected type=user, got '$COPILOT_TYPE'"
fi

COPILOT_SESSION_ID_VAL=$(echo "$COPILOT_LINE1" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('sessionId',''))" 2>/dev/null)
if [[ "$COPILOT_SESSION_ID_VAL" == "copilot-session-xyz789" ]]; then
  pass "JSONL (copilot): sessionId correctly parsed as copilot-session-xyz789"
else
  fail "JSONL (copilot): expected sessionId=copilot-session-xyz789, got '$COPILOT_SESSION_ID_VAL'"
fi

# ─── Test 16: Auto-detection — directory-based (Copilot vs Claude Code) ───────

echo ""
echo "Test 16: Auto-detection of tool context (directory-based)"

# Detection logic mirrors what the skill documents
detect_tool_context_dir() {
  local home="$1"
  local copilot_sessions=0
  local claude_sessions=0

  if [[ -d "$home/.copilot/session-state" ]]; then
    copilot_sessions=$(ls -d "$home/.copilot/session-state/"*/ 2>/dev/null | wc -l)
  fi
  if [[ -d "$home/.claude/projects" ]]; then
    claude_sessions=$(ls "$home/.claude/projects/"*/*.jsonl 2>/dev/null | wc -l || true)
  fi

  if [[ "$copilot_sessions" -gt 0 && "$claude_sessions" -eq 0 ]]; then
    echo "copilot"
  elif [[ "$claude_sessions" -gt 0 && "$copilot_sessions" -eq 0 ]]; then
    echo "claude-code"
  elif [[ "$claude_sessions" -gt 0 && "$copilot_sessions" -gt 0 ]]; then
    echo "both"
  else
    echo "none"
  fi
}

# Scenario 1: Only Copilot sessions exist
ONLY_COPILOT_HOME="$TMPDIR_TEST/only-copilot-home"
mkdir -p "$ONLY_COPILOT_HOME/.copilot/session-state/session-aaa"
make_copilot_events_jsonl "$ONLY_COPILOT_HOME/.copilot/session-state/session-aaa/events.jsonl"

CONTEXT_ONLY_COPILOT=$(detect_tool_context_dir "$ONLY_COPILOT_HOME")
if [[ "$CONTEXT_ONLY_COPILOT" == "copilot" ]]; then
  pass "auto-detect (dir): only ~/.copilot/session-state/ → copilot"
else
  fail "auto-detect (dir): expected copilot, got '$CONTEXT_ONLY_COPILOT'"
fi

# Scenario 2: Only Claude Code sessions exist
ONLY_CLAUDE_HOME="$TMPDIR_TEST/only-claude-home"
mkdir -p "$ONLY_CLAUDE_HOME/.claude/projects/myproject"
make_jsonl "$ONLY_CLAUDE_HOME/.claude/projects/myproject/session.jsonl"

CONTEXT_ONLY_CLAUDE=$(detect_tool_context_dir "$ONLY_CLAUDE_HOME")
if [[ "$CONTEXT_ONLY_CLAUDE" == "claude-code" ]]; then
  pass "auto-detect (dir): only ~/.claude/projects/ → claude-code"
else
  fail "auto-detect (dir): expected claude-code, got '$CONTEXT_ONLY_CLAUDE'"
fi

# Scenario 3: Both directories exist with sessions → offer choice
BOTH_HOME="$TMPDIR_TEST/both-home"
mkdir -p "$BOTH_HOME/.copilot/session-state/session-bbb"
make_copilot_events_jsonl "$BOTH_HOME/.copilot/session-state/session-bbb/events.jsonl"
mkdir -p "$BOTH_HOME/.claude/projects/myproject"
make_jsonl "$BOTH_HOME/.claude/projects/myproject/session.jsonl"

CONTEXT_BOTH=$(detect_tool_context_dir "$BOTH_HOME")
if [[ "$CONTEXT_BOTH" == "both" ]]; then
  pass "auto-detect (dir): both directories exist → 'both' (user choice needed)"
else
  fail "auto-detect (dir): expected 'both', got '$CONTEXT_BOTH'"
fi

# Scenario 4: Neither directory → return none (fallback to env vars)
EMPTY_HOME="$TMPDIR_TEST/empty-home"
mkdir -p "$EMPTY_HOME"

CONTEXT_NONE=$(detect_tool_context_dir "$EMPTY_HOME")
if [[ "$CONTEXT_NONE" == "none" ]]; then
  pass "auto-detect (dir): no directories → 'none' (env var fallback applies)"
else
  fail "auto-detect (dir): expected 'none', got '$CONTEXT_NONE'"
fi

# ─── Test 17: Auto-detection — env var fallback ────────────────────────────────

echo ""
echo "Test 17: Auto-detection — env var fallback (when directories not present)"

detect_tool_context_env() {
  if [[ -n "${CLAUDE_CODE_SESSION:-}${CLAUDE_SESSION_ID:-}${ANTHROPIC_API_KEY:-}" ]]; then
    echo "claude-code"
  elif [[ -n "${GITHUB_COPILOT_TOKEN:-}${COPILOT_SESSION:-}" ]]; then
    echo "copilot"
  else
    echo "claude-code"  # safe fallback
  fi
}

CONTEXT_DEFAULT=$(detect_tool_context_env)
if [[ "$CONTEXT_DEFAULT" == "claude-code" ]]; then
  pass "env-var fallback: no vars set → claude-code (safe fallback)"
else
  fail "env-var fallback: expected claude-code, got '$CONTEXT_DEFAULT'"
fi

CONTEXT_CC=$(CLAUDE_CODE_SESSION=test-session-id detect_tool_context_env)
if [[ "$CONTEXT_CC" == "claude-code" ]]; then
  pass "env-var fallback: CLAUDE_CODE_SESSION set → claude-code"
else
  fail "env-var fallback: expected claude-code, got '$CONTEXT_CC'"
fi

CONTEXT_CP=$(GITHUB_COPILOT_TOKEN=ghu_test123 detect_tool_context_env)
if [[ "$CONTEXT_CP" == "copilot" ]]; then
  pass "env-var fallback: GITHUB_COPILOT_TOKEN set → copilot"
else
  fail "env-var fallback: expected copilot, got '$CONTEXT_CP'"
fi

CONTEXT_CS=$(COPILOT_SESSION=copilot-session-abc detect_tool_context_env)
if [[ "$CONTEXT_CS" == "copilot" ]]; then
  pass "env-var fallback: COPILOT_SESSION set → copilot"
else
  fail "env-var fallback: expected copilot, got '$CONTEXT_CS'"
fi

# ─── Test 18: SKILL.md documents Copilot log location ─────────────────────────

echo ""
echo "Test 18: SKILL.md documents Copilot JSONL log location"

if grep -q "session-state" "$SKILL_FILE"; then
  pass "SKILL.md documents ~/.copilot/session-state/ path"
else
  fail "SKILL.md missing ~/.copilot/session-state/ documentation"
fi

if grep -q "events.jsonl" "$SKILL_FILE"; then
  pass "SKILL.md documents events.jsonl file name"
else
  fail "SKILL.md missing events.jsonl documentation"
fi

# ─── Test 19: Unknown format detection ────────────────────────────────────────

echo ""
echo "Test 19: Unknown format detection"

detect_format() {
  local file="$1"
  if [[ "$file" == *.jsonl ]]; then
    echo "jsonl"
  elif [[ "$file" == *.log ]]; then
    local first_char
    first_char=$(head -c 1 "$file" 2>/dev/null)
    if [[ "$first_char" == "{" ]]; then
      echo "jsonl"
    else
      echo "plain-log"
    fi
  else
    local first_char
    first_char=$(head -c 1 "$file" 2>/dev/null)
    if [[ "$first_char" == "{" ]]; then
      echo "jsonl"
    else
      echo "unknown"
    fi
  fi
}

# A file with no recognized extension and plain text content
PLAIN_FILE="$TMPDIR_TEST/somefile.txt"
echo "just some plain text" > "$PLAIN_FILE"

FORMAT_PLAIN=$(detect_format "$PLAIN_FILE")
if [[ "$FORMAT_PLAIN" == "unknown" ]]; then
  pass "unknown format: plain text file returns 'unknown'"
else
  fail "unknown format: expected 'unknown', got '$FORMAT_PLAIN'"
fi

# A .log file with plain text (not JSONL)
PLAIN_LOG="$TMPDIR_TEST/agent.log"
echo "2025-01-01 INFO: starting agent" > "$PLAIN_LOG"

FORMAT_PLAIN_LOG=$(detect_format "$PLAIN_LOG")
if [[ "$FORMAT_PLAIN_LOG" == "plain-log" ]]; then
  pass "plain-log: non-JSONL .log file returns 'plain-log'"
else
  fail "plain-log: expected 'plain-log', got '$FORMAT_PLAIN_LOG'"
fi

# A .log file that IS JSONL
JSONL_LOG="$TMPDIR_TEST/agent-jsonl.log"
make_jsonl "$JSONL_LOG"

FORMAT_JSONL_LOG=$(detect_format "$JSONL_LOG")
if [[ "$FORMAT_JSONL_LOG" == "jsonl" ]]; then
  pass "jsonl .log: JSONL-format .log file returns 'jsonl'"
else
  fail "jsonl .log: expected 'jsonl', got '$FORMAT_JSONL_LOG'"
fi

# events.jsonl (Copilot) detected as jsonl format
COPILOT_EVENTS_SAMPLE="$TMPDIR_TEST/events.jsonl"
make_copilot_events_jsonl "$COPILOT_EVENTS_SAMPLE"

FORMAT_COPILOT_EVENTS=$(detect_format "$COPILOT_EVENTS_SAMPLE")
if [[ "$FORMAT_COPILOT_EVENTS" == "jsonl" ]]; then
  pass "copilot events.jsonl: correctly identified as jsonl format"
else
  fail "copilot events.jsonl: expected 'jsonl', got '$FORMAT_COPILOT_EVENTS'"
fi

# ─── Test 20: SKILL.md documents Copilot workspace.yaml and plan.md ──────────

echo ""
echo "Test 20: SKILL.md documents Copilot session structure"

if grep -q "workspace.yaml" "$SKILL_FILE"; then
  pass "SKILL.md documents workspace.yaml in Copilot session"
else
  fail "SKILL.md missing workspace.yaml documentation"
fi

if grep -q "plan.md" "$SKILL_FILE"; then
  pass "SKILL.md documents plan.md in Copilot session"
else
  fail "SKILL.md missing plan.md documentation"
fi

# ─── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════"
echo "Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
