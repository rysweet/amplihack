#!/usr/bin/env bash
# Tests for crusty-old-engineer skill (COE Advisor)
# Run with: bash .claude/skills/crusty-old-engineer/tests/test_crusty_old_engineer.sh
# All tests are self-contained. Validates SKILL.md structure, frontmatter,
# required sections per issue #3564, documentation consistency, and security.

set -euo pipefail

PASS=0
FAIL=0

pass() { echo "  PASS: $1"; PASS=$((PASS+1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }

# Resolve paths relative to this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
SKILL_FILE="$SKILL_DIR/SKILL.md"
REPO_ROOT="$(cd "$SKILL_DIR/../../.." && pwd)"
HOWTO_FILE="$REPO_ROOT/docs/howto/use-crusty-old-engineer.md"
INDEX_FILE="$REPO_ROOT/docs/index.md"
CATALOG_FILE="$REPO_ROOT/docs/skills/SKILL_CATALOG.md"

# ─── Test 1: SKILL.md exists ────────────────────────────────────────────────

echo "Test 1: SKILL.md exists"

if [[ -f "$SKILL_FILE" ]]; then
  pass "SKILL.md exists at $SKILL_FILE"
else
  fail "SKILL.md not found at $SKILL_FILE"
  echo "  (Cannot run remaining tests without SKILL.md)"
  echo ""
  echo "═══════════════════════════════"
  echo "Results: $PASS passed, $FAIL failed"
  echo "═══════════════════════════════"
  exit 1
fi

# ─── Test 2: YAML frontmatter — required fields ─────────────────────────────

echo ""
echo "Test 2: YAML frontmatter — required fields"

FRONTMATTER=$(sed -n '/^---$/,/^---$/p' "$SKILL_FILE")

if echo "$FRONTMATTER" | grep -q "^name: crusty-old-engineer"; then
  pass "frontmatter: name is 'crusty-old-engineer'"
else
  fail "frontmatter: name field missing or incorrect (expected 'crusty-old-engineer')"
fi

if echo "$FRONTMATTER" | grep -q "^version:"; then
  pass "frontmatter: version field present"
else
  fail "frontmatter: version field missing"
fi

if echo "$FRONTMATTER" | grep -q "^description:"; then
  pass "frontmatter: description field present"
else
  fail "frontmatter: description field missing"
fi

if echo "$FRONTMATTER" | grep -q "^allowed-tools:"; then
  pass "frontmatter: allowed-tools field present"
else
  fail "frontmatter: allowed-tools field missing"
fi

if echo "$FRONTMATTER" | grep -q "^user-invocable: true"; then
  pass "frontmatter: user-invocable is true"
else
  fail "frontmatter: user-invocable should be true (skill is directly invokable)"
fi

if echo "$FRONTMATTER" | grep -q "^auto-activation:"; then
  pass "frontmatter: auto-activation section present"
else
  fail "frontmatter: auto-activation section missing"
fi

# ─── Test 3: Auto-activation keywords ───────────────────────────────────────

echo ""
echo "Test 3: Auto-activation keywords from issue #3564"

REQUIRED_KEYWORDS=("crusty" "reality check" "what could go wrong" "should I use" "is this a good idea")

for kw in "${REQUIRED_KEYWORDS[@]}"; do
  if grep -q "$kw" "$SKILL_FILE"; then
    pass "auto-activation keyword present: '$kw'"
  else
    fail "auto-activation keyword missing: '$kw'"
  fi
done

# ─── Test 4: Allowed-tools — least privilege check ──────────────────────────

echo ""
echo "Test 4: Allowed-tools — least privilege (security)"

TOOLS_LINE=$(grep "^allowed-tools:" "$SKILL_FILE" || true)

for tool in "Read" "Grep" "Glob"; do
  if echo "$TOOLS_LINE" | grep -q "$tool"; then
    pass "allowed-tools includes read-oriented tool: $tool"
  else
    fail "allowed-tools missing expected read-oriented tool: $tool"
  fi
done

for tool in "Write" "Edit"; do
  if echo "$TOOLS_LINE" | grep -q "\"$tool\""; then
    fail "allowed-tools includes write tool '$tool' — COE is advisory-only, should not modify files"
  else
    pass "allowed-tools correctly excludes write tool: $tool"
  fi
done

# ─── Test 5: Required sections from issue #3564 ─────────────────────────────

echo ""
echo "Test 5: Required sections from issue #3564 spec"

REQUIRED_SECTIONS=(
  "When to Use"
  "Tone and Voice"
  "Core Behaviors"
  "Output Structure"
  "Execution Steps"
  "Explicit Non-Goals"
  "Example"
  "Final Note"
)

for section in "${REQUIRED_SECTIONS[@]}"; do
  if grep -qi "$section" "$SKILL_FILE"; then
    pass "required section present: '$section'"
  else
    fail "required section MISSING: '$section'"
  fi
done

# ─── Test 6: Core Behaviors — all 4 behaviors present ───────────────────────

echo ""
echo "Test 6: Core Behaviors — all 4 required behaviors"

REQUIRED_BEHAVIORS=(
  "Grounded Skepticism"
  "Constructive Progress"
  "Evidence-Linked Judgment"
  "Prior Effort Expectation"
)

for behavior in "${REQUIRED_BEHAVIORS[@]}"; do
  if grep -q "$behavior" "$SKILL_FILE"; then
    pass "core behavior present: '$behavior'"
  else
    fail "core behavior MISSING: '$behavior'"
  fi
done

# ─── Test 7: Output Structure — all 5 sections ──────────────────────────────

echo ""
echo "Test 7: Output Structure — all 5 response sections"

OUTPUT_SECTIONS=(
  "Short framing"
  "Key risks"
  "Recommended approach"
  "References"
  "Optional aside"
)

for section in "${OUTPUT_SECTIONS[@]}"; do
  if grep -qi "$section" "$SKILL_FILE"; then
    pass "output section present: '$section'"
  else
    fail "output section MISSING: '$section'"
  fi
done

# ─── Test 8: Tone constraints — disallowed tones documented ─────────────────

echo ""
echo "Test 8: Tone constraints — disallowed tones explicitly listed"

DISALLOWED_TONES=("Promotional" "Inspirational" "Evangelical")

for tone in "${DISALLOWED_TONES[@]}"; do
  if grep -qi "$tone" "$SKILL_FILE"; then
    pass "disallowed tone explicitly listed: '$tone'"
  else
    fail "disallowed tone not documented: '$tone' (should be explicitly called out)"
  fi
done

REQUIRED_TONES=("Direct" "Skeptical" "Grounded")

for tone in "${REQUIRED_TONES[@]}"; do
  if grep -qi "$tone" "$SKILL_FILE"; then
    pass "required tone documented: '$tone'"
  else
    fail "required tone not documented: '$tone'"
  fi
done

# ─── Test 9: Evidence-Linked Judgment — source hierarchy ────────────────────

echo ""
echo "Test 9: Evidence-Linked Judgment — source types documented"

if grep -qi "Preferred sources" "$SKILL_FILE" || grep -qi "Primary" "$SKILL_FILE"; then
  pass "evidence: preferred/primary sources documented"
else
  fail "evidence: no preferred/primary source category documented"
fi

if grep -qi "Discouraged" "$SKILL_FILE" || grep -qi "not.*authority" "$SKILL_FILE"; then
  pass "evidence: discouraged sources or anti-patterns documented"
else
  fail "evidence: no discouraged source guidance"
fi

if grep -qi "postmortem" "$SKILL_FILE" || grep -qi "SRE" "$SKILL_FILE"; then
  pass "evidence: concrete source examples mentioned (postmortems/SRE)"
else
  fail "evidence: no concrete source examples (should mention postmortems, SRE book, etc.)"
fi

# ─── Test 10: Non-Goals — explicit boundaries ───────────────────────────────

echo ""
echo "Test 10: Non-Goals — explicit boundaries"

NONGOALS=("Shame" "insult" "sarcasm" "fabricat")

for ng in "${NONGOALS[@]}"; do
  if grep -qi "$ng" "$SKILL_FILE"; then
    pass "non-goal boundary documented: '$ng'"
  else
    fail "non-goal boundary missing: '$ng' (should be explicitly prohibited)"
  fi
done

# ─── Test 11: Execution Steps — numbered steps present ──────────────────────

echo ""
echo "Test 11: Execution Steps — numbered steps"

STEP_COUNT=$(grep -cE "^[0-9]+\." "$SKILL_FILE" || true)
if [[ "$STEP_COUNT" -ge 4 ]]; then
  pass "execution steps: at least 4 numbered steps ($STEP_COUNT found)"
else
  fail "execution steps: expected at least 4 numbered steps, found $STEP_COUNT"
fi

if grep -qi "Read the user" "$SKILL_FILE" || grep -qi "question or proposal" "$SKILL_FILE"; then
  pass "execution steps: step to read/understand user input"
else
  fail "execution steps: missing step to understand user input"
fi

if grep -qi "Assess prior effort" "$SKILL_FILE" || grep -qi "prior investigation" "$SKILL_FILE"; then
  pass "execution steps: step to assess prior effort"
else
  fail "execution steps: missing step to assess prior effort"
fi

if grep -qi "Research" "$SKILL_FILE" && grep -qi "WebSearch\|primary sources" "$SKILL_FILE"; then
  pass "execution steps: research step with source finding"
else
  fail "execution steps: missing research step"
fi

if grep -qi "Deliver the response" "$SKILL_FILE" || grep -qi "Output Structure" "$SKILL_FILE"; then
  pass "execution steps: delivery step referencing output structure"
else
  fail "execution steps: missing delivery step"
fi

# ─── Test 12: Example section — has concrete tone reference ─────────────────

echo ""
echo "Test 12: Example section — concrete tone reference"

EXAMPLE_HAS_FRAMING=false
EXAMPLE_HAS_RISKS=false
EXAMPLE_HAS_APPROACH=false

if grep -qi "Example" "$SKILL_FILE"; then
  if grep -q "dependency eviction\|refactor\|operational fallout" "$SKILL_FILE"; then
    EXAMPLE_HAS_FRAMING=true
  fi
  if grep -q "API compatibility\|Test coverage\|debugging ghosts\|longer than you expect" "$SKILL_FILE"; then
    EXAMPLE_HAS_RISKS=true
  fi
  if grep -q "isolating\|narrow interfaces\|Replace one at a time\|Ship after each" "$SKILL_FILE"; then
    EXAMPLE_HAS_APPROACH=true
  fi
fi

if $EXAMPLE_HAS_FRAMING; then
  pass "example: includes short framing"
else
  fail "example: missing concrete framing content"
fi

if $EXAMPLE_HAS_RISKS; then
  pass "example: includes risk examples"
else
  fail "example: missing risk content"
fi

if $EXAMPLE_HAS_APPROACH; then
  pass "example: includes recommended approach"
else
  fail "example: missing recommended approach content"
fi

# ─── Test 13: SKILL.md file size — reasonable bounds ────────────────────────

echo ""
echo "Test 13: SKILL.md file size — reasonable bounds"

LINE_COUNT=$(wc -l < "$SKILL_FILE")
if [[ "$LINE_COUNT" -ge 100 ]]; then
  pass "file size: at least 100 lines ($LINE_COUNT lines — substantive)"
else
  fail "file size: only $LINE_COUNT lines — likely incomplete (expected >= 100)"
fi

if [[ "$LINE_COUNT" -le 400 ]]; then
  pass "file size: under 400 lines ($LINE_COUNT lines — not bloated)"
else
  fail "file size: $LINE_COUNT lines — may be overly verbose (expected <= 400)"
fi

# ─── Test 14: No executable code in SKILL.md ────────────────────────────────

echo ""
echo "Test 14: No executable code or secrets"

if grep -qE "^(import |from .* import |require\(|const |let |var )" "$SKILL_FILE"; then
  fail "SKILL.md contains executable code imports — should be instruction-only"
else
  pass "no executable code imports found"
fi

if grep -qiE "(sk-|ghp_|Bearer |xoxb-)" "$SKILL_FILE"; then
  fail "SKILL.md may contain secrets or API keys"
else
  pass "no actual secrets detected"
fi

# ─── Test 15: Documentation — howto guide exists ────────────────────────────

echo ""
echo "Test 15: Documentation — howto guide exists"

if [[ -f "$HOWTO_FILE" ]]; then
  pass "howto guide exists: docs/howto/use-crusty-old-engineer.md"
else
  fail "howto guide MISSING: docs/howto/use-crusty-old-engineer.md"
fi

# ─── Test 16: Documentation — howto guide content consistency ───────────────

echo ""
echo "Test 16: Documentation — howto guide content consistency"

if [[ -f "$HOWTO_FILE" ]]; then
  if grep -q "/crusty-old-engineer" "$HOWTO_FILE"; then
    pass "howto: documents /crusty-old-engineer invocation"
  else
    fail "howto: missing /crusty-old-engineer invocation"
  fi

  if grep -qi "auto.activat" "$HOWTO_FILE"; then
    pass "howto: documents auto-activation"
  else
    fail "howto: missing auto-activation documentation"
  fi

  if grep -q "Short Framing\|Short framing" "$HOWTO_FILE"; then
    pass "howto: documents Short Framing output section"
  else
    fail "howto: missing Short Framing output section"
  fi

  if grep -q "Key Risks\|sharp edges\|Sharp Edges" "$HOWTO_FILE"; then
    pass "howto: documents Key Risks output section"
  else
    fail "howto: missing Key Risks output section"
  fi

  if grep -q "Recommended Approach\|Recommended approach" "$HOWTO_FILE"; then
    pass "howto: documents Recommended Approach output section"
  else
    fail "howto: missing Recommended Approach output section"
  fi

  if grep -qi "Not every section appears" "$HOWTO_FILE"; then
    pass "howto: clarifies sections are selectively included"
  else
    fail "howto: missing clarification that sections are selectively included"
  fi

  INVOKE_LINE=$(grep -n "/crusty-old-engineer" "$HOWTO_FILE" | head -1 | cut -d: -f1)
  AUTO_LINE=$(grep -n "auto.activat" "$HOWTO_FILE" | head -1 | cut -d: -f1)
  if [[ -n "$INVOKE_LINE" && -n "$AUTO_LINE" && "$INVOKE_LINE" -lt "$AUTO_LINE" ]]; then
    pass "howto: direct invocation documented before auto-activation"
  else
    fail "howto: direct invocation should appear before auto-activation"
  fi
else
  fail "howto: cannot test content — file missing"
fi

# ─── Test 17: Documentation — skill catalog entry ───────────────────────────

echo ""
echo "Test 17: Documentation — skill catalog entry"

if [[ -f "$CATALOG_FILE" ]]; then
  if grep -q "crusty-old-engineer" "$CATALOG_FILE"; then
    pass "catalog: crusty-old-engineer listed"
  else
    fail "catalog: crusty-old-engineer NOT listed in SKILL_CATALOG.md"
  fi

  if grep -q "3564" "$CATALOG_FILE"; then
    pass "catalog: references issue #3564"
  else
    fail "catalog: missing issue #3564 reference"
  fi
else
  fail "catalog: SKILL_CATALOG.md not found"
fi

# ─── Test 18: Documentation — index.md links ────────────────────────────────

echo ""
echo "Test 18: Documentation — index.md references"

if [[ -f "$INDEX_FILE" ]]; then
  if grep -qi "crusty" "$INDEX_FILE"; then
    pass "index.md: references crusty-old-engineer"
  else
    fail "index.md: no reference to crusty-old-engineer skill"
  fi

  LINK_TARGET=$(grep -oP '\(.*crusty.*\)' "$INDEX_FILE" | head -1 | tr -d '()')
  if [[ -n "$LINK_TARGET" ]]; then
    RESOLVED_PATH="$REPO_ROOT/docs/$LINK_TARGET"
    if [[ -f "$RESOLVED_PATH" ]]; then
      pass "index.md: link target exists ($LINK_TARGET)"
    else
      fail "index.md: broken link — '$LINK_TARGET' does not resolve to existing file"
    fi
  else
    pass "index.md: no file link to validate (may use anchor reference)"
  fi
else
  fail "index.md: file not found"
fi

# ─── Test 19: Integration — SKILL.md and howto alignment ────────────────────

echo ""
echo "Test 19: Integration — SKILL.md and howto content alignment"

if [[ -f "$HOWTO_FILE" && -f "$SKILL_FILE" ]]; then
  if grep -q "Grounded Skepticism" "$SKILL_FILE" && grep -q "Prior Effort" "$SKILL_FILE"; then
    pass "integration: SKILL.md documents all 4 core behaviors"
  else
    fail "integration: SKILL.md missing core behaviors"
  fi

  if grep -qi "prior effort\|already tried\|already researched" "$HOWTO_FILE"; then
    pass "integration: howto references prior effort expectation"
  else
    fail "integration: howto missing prior effort concept (key COE differentiator)"
  fi

  if grep -qi "mechanical\|not useful for\|When NOT" "$HOWTO_FILE"; then
    pass "integration: howto documents when NOT to use COE"
  else
    fail "integration: howto missing 'when not to use' guidance"
  fi
else
  fail "integration: cannot test — files missing"
fi

# ─── Test 20: Edge case — frontmatter YAML is well-formed ──────────────────

echo ""
echo "Test 20: Frontmatter YAML well-formedness"

FIRST_LINE=$(head -1 "$SKILL_FILE")
if [[ "$FIRST_LINE" == "---" ]]; then
  pass "frontmatter: starts with --- delimiter"
else
  fail "frontmatter: first line should be '---', got '$FIRST_LINE'"
fi

DELIM_COUNT=$(grep -c "^---$" "$SKILL_FILE" || true)
if [[ "$DELIM_COUNT" -ge 2 ]]; then
  pass "frontmatter: has closing --- delimiter ($DELIM_COUNT found)"
else
  fail "frontmatter: missing closing --- delimiter (only $DELIM_COUNT found)"
fi

if grep -q 'keywords:.*\[' "$SKILL_FILE" || grep -A20 "keywords:" "$SKILL_FILE" | grep -q "^ *-"; then
  pass "frontmatter: keywords is a list structure"
else
  fail "frontmatter: keywords should be a YAML list"
fi

if grep -q 'allowed-tools:.*\[' "$SKILL_FILE" || grep -A20 "allowed-tools:" "$SKILL_FILE" | grep -q "^ *-"; then
  pass "frontmatter: allowed-tools is a list structure"
else
  fail "frontmatter: allowed-tools should be a YAML list"
fi

# ─── Test 21: Research capability — WebSearch/WebFetch referenced ───────────

echo ""
echo "Test 21: Research capability — WebSearch/WebFetch referenced"

if grep -q "WebSearch" "$SKILL_FILE"; then
  pass "skill references WebSearch for evidence gathering"
else
  fail "skill does not reference WebSearch — needed for Evidence-Linked Judgment"
fi

if grep -q "WebFetch" "$SKILL_FILE"; then
  pass "skill references WebFetch for source retrieval"
else
  fail "skill does not reference WebFetch — needed for primary source access"
fi

# ─── Test 22: Constructive requirement — must offer way forward ─────────────

echo ""
echo "Test 22: Constructive progress — must offer way forward"

if grep -qi "viable.*forward\|way forward\|proceed\|safer first steps" "$SKILL_FILE"; then
  pass "constructive: documents requirement to offer viable path forward"
else
  fail "constructive: missing requirement to always offer a way forward"
fi

if grep -qi "Dismissal without direction.*not acceptable\|not.*dismiss" "$SKILL_FILE"; then
  pass "constructive: explicitly prohibits dismissal without direction"
else
  fail "constructive: should explicitly prohibit pure dismissal"
fi

# ─── Summary ─────────────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════"
echo "Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
