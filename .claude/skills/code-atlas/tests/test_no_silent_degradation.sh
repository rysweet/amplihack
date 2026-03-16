#!/bin/bash
# .claude/skills/code-atlas/tests/test_no_silent_degradation.sh
#
# TDD tests for the no-silent-degradation density guard.
# Validates FORBIDDEN_PATTERNS.md §2 compliance throughout the skill.
#
# Tests validate:
#   - SKILL.md documents density guard with exact thresholds (50 nodes, 100 edges)
#   - SKILL.md contains exact user prompt template
#   - SKILL.md contains no "falls back to table" wording without user prompt
#   - API-CONTRACTS.md contains DensityThresholdConfig schema
#   - API-CONTRACTS.md contains --density-threshold override documentation
#   - API-CONTRACTS.md references FORBIDDEN_PATTERNS §2
#   - No silent fallback code path described in any layer section
#   - SEC-13 threshold integer range validation documented
#   - SEC-14 re-prompt-on-invalid-input documented
#
# Usage: bash .claude/skills/code-atlas/tests/test_no_silent_degradation.sh
# Exit:  0 = all tests passed, non-zero = failures

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------
assert_file_contains() {
    local label="$1"; local pattern="$2"; local file="$3"
    if [[ ! -f "$file" ]]; then
        echo "FAIL: $label — file not found: $file"
        FAIL=$((FAIL + 1))
        return
    fi
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "PASS: $label"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label — pattern '$pattern' not found in $file"
        FAIL=$((FAIL + 1))
    fi
}

assert_not_in_file() {
    local label="$1"; local pattern="$2"; local file="$3"
    if [[ ! -f "$file" ]]; then
        echo "FAIL: $label — file not found: $file"
        FAIL=$((FAIL + 1))
        return
    fi
    # -P (PCRE) is intentionally retained here: the forbidden patterns use PCRE
    # alternation syntax such as "(a |the )?" which BRE cannot express. The -i
    # flag (case-insensitive) is also needed for cross-case matching. Do NOT
    # simplify this to plain grep — it would silently fail to catch violations.
    if grep -qiP "$pattern" "$file" 2>/dev/null; then
        echo "FAIL: $label — forbidden pattern '$pattern' found in $file"
        FAIL=$((FAIL + 1))
    else
        echo "PASS: $label"
        PASS=$((PASS + 1))
    fi
}

echo ""
echo "=== Test Suite: No Silent Degradation (FORBIDDEN_PATTERNS §2) ==="
echo ""

SKILL_MD="${SKILL_DIR}/SKILL.md"
API_MD="${SKILL_DIR}/API-CONTRACTS.md"
SEC_MD="${SKILL_DIR}/SECURITY.md"

# ---------------------------------------------------------------------------
# SECTION 1: SKILL.md Density Guard Documentation
# ---------------------------------------------------------------------------
echo "--- SKILL.md: Density Guard Documentation ---"

assert_file_contains \
    "SKILL.md contains Global Density Guard section" \
    "Global Density Guard\|Density Guard" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md documents node threshold of 50" \
    "50.*nodes\|nodes.*50\|node_count.*50\|50.*node" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md documents edge threshold of 100" \
    "100.*edges\|edges.*100\|edge_count.*100\|100.*edge" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md references FORBIDDEN_PATTERNS §2" \
    "FORBIDDEN_PATTERNS.*§2\|FORBIDDEN_PATTERNS.*2\|§2" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md contains exact prompt wording (nodes and edges)" \
    "nodes and.*edges.*render poorly\|render poorly" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md prompt offers choice (a)" \
    "Full diagram anyway" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md prompt offers choice (b)" \
    "Simplified.*clustered\|clustered.*diagram" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md prompt offers choice (c)" \
    "Table representation" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md documents --density-threshold override" \
    "density-threshold\|--density-threshold" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md applies density guard to all layers 1-8" \
    "all layers\|all.*1.*8\|every layer\|Layers 1.*8" \
    "$SKILL_MD"

echo ""
echo "--- SKILL.md: No Silent Fallback Code Paths ---"

# Check that no section describes silent fallback (without user prompt)
assert_not_in_file \
    "SKILL.md does not describe 'falls back to table' without prompt" \
    "falls back to (a |the )?table (silently|without|automatically)" \
    "$SKILL_MD"

assert_not_in_file \
    "SKILL.md does not have a code path that silently falls back (outside the guard section)" \
    "falls back.*table.*silently\|silently.*falls.*back.*table" \
    "$SKILL_MD"

assert_not_in_file \
    "SKILL.md does not describe 'automatically substitutes table'" \
    "automatically substitut" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md explicitly states what is NEVER permitted" \
    "NEVER.*permit\|never.*permit\|NOT.*Permitted\|FORBIDDEN" \
    "$SKILL_MD"

# ---------------------------------------------------------------------------
# SECTION 2: API-CONTRACTS.md Density Guard Contract
# ---------------------------------------------------------------------------
echo ""
echo "--- API-CONTRACTS.md: Density Guard Contract ---"

assert_file_contains \
    "API-CONTRACTS.md has DensityThresholdConfig schema" \
    "DensityThresholdConfig" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md documents default node threshold of 50" \
    "Default.*50\|nodes.*50\|50.*node" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md documents default edge threshold of 100" \
    "Default.*100\|edges.*100\|100.*edge" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md documents DENSITY_THRESHOLD_EXCEEDED error code" \
    "DENSITY_THRESHOLD_EXCEEDED" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md documents --density-threshold override" \
    "density-threshold\|--density-threshold" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md contains exact required prompt wording" \
    "nodes and.*edges.*render poorly\|DENSITY_PROMPT\|Required Prompt Wording" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md states NEVER fallback silently" \
    "NEVER.*fall back.*silently\|never.*silent\|contract violation" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md documents non-interactive context behaviour" \
    "non-interactive\|non_interactive" \
    "$API_MD"

# ---------------------------------------------------------------------------
# SECTION 3: SECURITY.md SEC-13 and SEC-14
# ---------------------------------------------------------------------------
echo ""
echo "--- SECURITY.md: SEC-13 (threshold validation) and SEC-14 (prompt choices) ---"

assert_file_contains \
    "SECURITY.md contains SEC-13 threshold validation" \
    "SEC-13" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md SEC-13 specifies range 1-10,000" \
    "1.*10.000\|1.*10,000\|range.*10000\|1–10" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md SEC-13 rejects value 0" \
    "0.*disables\|value.*0\|rejects.*0\|Rejected.*0" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md SEC-13 rejects negative values" \
    "negative\|Negative" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md contains SEC-14 prompt validation" \
    "SEC-14" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md SEC-14 only accepts a, b, c" \
    "'a'.*'b'.*'c'\|a.*b.*c.*only\|only.*a.*b.*c" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md SEC-14 requires re-prompting on invalid input" \
    "re-prompt\|reprompt\|loop.*re-prompt" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md SEC-14 logs choice (not raw input)" \
    "log.*choice\|choice.*log\|not.*raw input" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md checklist includes SEC-13" \
    "SEC-13.*threshold\|SEC-13.*integer\|SEC-13.*range" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md checklist includes SEC-14" \
    "SEC-14.*accept\|SEC-14.*re-prompt\|SEC-14.*only.*a" \
    "$SEC_MD"

# ---------------------------------------------------------------------------
# SECTION 4: Cross-Document FORBIDDEN_PATTERNS §2 Compliance
# ---------------------------------------------------------------------------
echo ""
echo "--- Cross-Document FORBIDDEN_PATTERNS §2 Compliance ---"

assert_file_contains \
    "SKILL.md explicitly references FORBIDDEN_PATTERNS.md §2" \
    "FORBIDDEN_PATTERNS.md.*§2\|FORBIDDEN_PATTERNS.*§2" \
    "$SKILL_MD"

assert_file_contains \
    "API-CONTRACTS.md references FORBIDDEN_PATTERNS §2" \
    "FORBIDDEN_PATTERNS.*§2\|FORBIDDEN_PATTERNS.*2" \
    "$API_MD"

# Verify Density Guard applies to each layer
for layer in 1 2 3 4 5 6 7 8; do
    assert_file_contains \
        "Density guard coverage: Layer $layer mentioned in density guard context" \
        "Layer $layer\|layer $layer\|layers.*$layer" \
        "$SKILL_MD"
done

# ---------------------------------------------------------------------------
# SECTION 5: Recipe Density Guard Parameters
# ---------------------------------------------------------------------------
echo ""
echo "--- Recipe YAML: Density Guard Parameters ---"

RECIPE="${SKILL_DIR}/../../../amplifier-bundle/recipes/code-atlas.yaml"

if [[ -f "$RECIPE" ]]; then
    assert_file_contains \
        "Recipe documents density_threshold_nodes parameter" \
        "density_threshold_nodes" \
        "$RECIPE"

    assert_file_contains \
        "Recipe documents density_threshold_edges parameter" \
        "density_threshold_edges" \
        "$RECIPE"

    assert_file_contains \
        "Recipe density parameters have minimum: 1" \
        "minimum.*1\|min.*1" \
        "$RECIPE"

    assert_file_contains \
        "Recipe density parameters have maximum: 10000" \
        "maximum.*10000\|max.*10000" \
        "$RECIPE"

    assert_file_contains \
        "Recipe SEC-17 compliance note present" \
        "SEC-17\|structured data\|no shell interpolation" \
        "$RECIPE"
else
    echo "FAIL: Recipe not found at $RECIPE"
    FAIL=$((FAIL + 1))
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "════════════════════════════════════════"
echo "Results: $PASS passed, $FAIL failed"
echo "════════════════════════════════════════"

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
else
    exit 0
fi
