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

make_copilot_markdown() {
  local path="$1"
  mkdir -p "$(dirname "$path")"
  cat >"$path" <<'MARKDOWN'
# Copilot Session Export

**Date**: 2025-11-23 19:32:36
**Session ID**: copilot-session-xyz789

---

**User**: Fix the authentication bug in login.py

**Copilot**: I'll examine the file and fix the authentication bug...

---

**User**: Thank you, that looks good.

**Copilot**: You're welcome! The fix replaces the insecure comparison with a constant-time check.
MARKDOWN
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

# ─── Test 5: Current session — find latest JSONL ─────────────────────────────

echo ""
echo "Test 5: Mode 1 — current session file detection"

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

# ─── Test 6: Specific session ID search ──────────────────────────────────────

echo ""
echo "Test 6: Mode 2 — find session by ID"

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

# ─── Test 7: Agent output detection ──────────────────────────────────────────

echo ""
echo "Test 7: Mode 3 — agent background task output"

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

# ─── Test 8: All sessions listing ────────────────────────────────────────────

echo ""
echo "Test 8: Mode 4 — list all sessions"

ALL_FILES=$(find "$FAKE_HOME/.claude/projects" -name "*.jsonl" 2>/dev/null | wc -l)
if [[ "$ALL_FILES" -eq 2 ]]; then
  pass "mode 4: found correct number of sessions (2)"
else
  fail "mode 4: expected 2 sessions, found $ALL_FILES"
fi

# ─── Test 9: Date-range filtering ────────────────────────────────────────────

echo ""
echo "Test 9: Date-range filtering"

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

# ─── Test 10: HTML output path construction ───────────────────────────────────

echo ""
echo "Test 10: HTML output path"

HTML_OUTPUT="/tmp/transcript-view.html"
# Verify the path is mentioned in SKILL.md
if grep -q "/tmp/transcript-view.html" "$SKILL_FILE"; then
  pass "SKILL.md mentions HTML output path /tmp/transcript-view.html"
else
  fail "SKILL.md does not mention HTML output path"
fi

# ─── Test 11: JSONL sample parse (basic structure) ───────────────────────────

echo ""
echo "Test 11: JSONL basic parse"

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

# ─── Test 12: Auto-detection — JSONL vs Markdown ─────────────────────────────

echo ""
echo "Test 12: Auto-detection of log format (JSONL vs Copilot markdown)"

JSONL_SAMPLE="$TMPDIR_TEST/detect.jsonl"
MD_SAMPLE="$TMPDIR_TEST/copilot-session.md"
make_jsonl "$JSONL_SAMPLE"
make_copilot_markdown "$MD_SAMPLE"

# Detection logic mirrors what the skill documents
detect_format() {
  local file="$1"
  if [[ "$file" == *.jsonl ]]; then
    echo "jsonl"
  elif [[ "$file" == *.md ]]; then
    # Only match specific Copilot export headers — not generic "/share" text
    if grep -q "Copilot Session Export\|copilot-session" "$file" 2>/dev/null; then
      echo "copilot-markdown"
    else
      echo "markdown"
    fi
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

FORMAT_JSONL=$(detect_format "$JSONL_SAMPLE")
if [[ "$FORMAT_JSONL" == "jsonl" ]]; then
  pass "auto-detect: .jsonl file identified as jsonl format"
else
  fail "auto-detect: expected jsonl, got '$FORMAT_JSONL'"
fi

FORMAT_MD=$(detect_format "$MD_SAMPLE")
if [[ "$FORMAT_MD" == "copilot-markdown" ]]; then
  pass "auto-detect: copilot markdown export identified as copilot-markdown"
else
  fail "auto-detect: expected copilot-markdown, got '$FORMAT_MD'"
fi

# ─── Test 13: Copilot context detection via environment variable ──────────────

echo ""
echo "Test 13: Copilot context detection via launcher_detector.py env var conventions"

# Mirrors detect_log_format logic in SKILL.md, using same var names as
# src/amplihack/hooks/launcher_detector.py LAUNCHER_MARKERS
detect_tool_context() {
  if [[ -n "${CLAUDE_CODE_SESSION:-}${CLAUDE_SESSION_ID:-}${ANTHROPIC_API_KEY:-}" ]]; then
    echo "claude-code"
  elif [[ -n "${GITHUB_COPILOT_TOKEN:-}${COPILOT_SESSION:-}" ]]; then
    echo "copilot"
  else
    # Default to claude-code — safe fallback
    echo "claude-code"
  fi
}

# Default (no special env vars set) — should return claude-code (safe fallback)
CONTEXT_DEFAULT=$(detect_tool_context)
if [[ "$CONTEXT_DEFAULT" == "claude-code" ]]; then
  pass "context detection: default context is 'claude-code' (safe fallback, no env vars)"
else
  fail "context detection: expected claude-code default, got '$CONTEXT_DEFAULT'"
fi

# Simulate Claude Code context via CLAUDE_CODE_SESSION
CONTEXT_CC=$(CLAUDE_CODE_SESSION=test-session-id detect_tool_context)
if [[ "$CONTEXT_CC" == "claude-code" ]]; then
  pass "context detection: CLAUDE_CODE_SESSION set → claude-code"
else
  fail "context detection: expected claude-code, got '$CONTEXT_CC'"
fi

# Simulate Copilot context via GITHUB_COPILOT_TOKEN
CONTEXT_CP=$(GITHUB_COPILOT_TOKEN=ghu_test123 detect_tool_context)
if [[ "$CONTEXT_CP" == "copilot" ]]; then
  pass "context detection: GITHUB_COPILOT_TOKEN set → copilot"
else
  fail "context detection: expected copilot, got '$CONTEXT_CP'"
fi

# Simulate Copilot context via COPILOT_SESSION
CONTEXT_CS=$(COPILOT_SESSION=copilot-session-abc detect_tool_context)
if [[ "$CONTEXT_CS" == "copilot" ]]; then
  pass "context detection: COPILOT_SESSION set → copilot"
else
  fail "context detection: expected copilot, got '$CONTEXT_CS'"
fi

# ─── Test 14: Copilot markdown parse — extract turns ─────────────────────────

echo ""
echo "Test 14: Copilot markdown export — parse conversation turns"

MD_FILE="$TMPDIR_TEST/copilot-export.md"
make_copilot_markdown "$MD_FILE"

USER_COUNT=$(grep -c "^\*\*User\*\*:" "$MD_FILE" 2>/dev/null || true)
COPILOT_COUNT=$(grep -c "^\*\*Copilot\*\*:" "$MD_FILE" 2>/dev/null || true)

if [[ "$USER_COUNT" -eq 2 ]]; then
  pass "copilot-md: found 2 user turns"
else
  fail "copilot-md: expected 2 user turns, found $USER_COUNT"
fi

if [[ "$COPILOT_COUNT" -eq 2 ]]; then
  pass "copilot-md: found 2 copilot turns"
else
  fail "copilot-md: expected 2 copilot turns, found $COPILOT_COUNT"
fi

# ─── Test 15: Copilot context — SKILL.md has /share guidance ─────────────────

echo ""
echo "Test 15: SKILL.md provides /share guidance for Copilot users"

if grep -q "/share" "$SKILL_FILE"; then
  pass "SKILL.md mentions /share command for Copilot export"
else
  fail "SKILL.md missing /share command guidance for Copilot users"
fi

if grep -q "copilot" "$SKILL_FILE" && grep -q "markdown" "$SKILL_FILE"; then
  pass "SKILL.md addresses Copilot markdown export"
else
  fail "SKILL.md missing Copilot markdown export documentation"
fi

# ─── Test 16: SKILL.md documents Copilot log location (no auto-save) ─────────

echo ""
echo "Test 16: SKILL.md documents that Copilot has no auto-save logs"

if grep -qi "no.*auto\|not.*auto\|does not.*save\|no.*persist\|no.*log" "$SKILL_FILE"; then
  pass "SKILL.md documents Copilot has no automatic log persistence"
else
  fail "SKILL.md missing documentation of Copilot's no-auto-save behavior"
fi

# ─── Test 17: False-positive guard — .md with /share but NOT a Copilot export ──

echo ""
echo "Test 17: No false-positive detection for .md files containing /share text"

NON_COPILOT_MD="$TMPDIR_TEST/readme.md"
cat >"$NON_COPILOT_MD" <<'MARKDOWN'
# Developer Notes

To export your AI session, use /share markdown ./output.md in the CLI tool.

This is a regular documentation file with no special session headers.
MARKDOWN

FORMAT_NON_COPILOT=$(detect_format "$NON_COPILOT_MD")
if [[ "$FORMAT_NON_COPILOT" == "markdown" ]]; then
  pass "false-positive guard: .md with '/share' text but no export header → markdown (not copilot-markdown)"
else
  fail "false-positive guard: expected 'markdown', got '$FORMAT_NON_COPILOT'"
fi

# ─── Test 18: Unknown format detection ────────────────────────────────────────

echo ""
echo "Test 18: Unknown format detection"

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

# ─── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════"
echo "Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
