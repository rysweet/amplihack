#!/bin/bash
# .claude/skills/code-atlas/tests/test_layer7_8.sh
#
# TDD tests for Layer 7 (Service Component Architecture) and
# Layer 8 (AST+LSP Symbol Bindings) documentation and output contracts.
#
# Tests validate:
#   - SKILL.md contains Layer 7 and Layer 8 section documentation
#   - API-CONTRACTS.md contains Layer 7/8 filesystem contracts and error codes
#   - SECURITY.md contains SEC-11 through SEC-16 definitions
#   - Output filesystem contract assertions (when atlas has been built)
#   - SEC-11 service name sanitization assertions
#   - SEC-12 LSP output sanitization assertions
#   - SEC-15 Layer 8 credential redaction assertions
#   - SEC-16 relative-path enforcement assertions
#
# THESE TESTS WILL FAIL until the skill documentation is complete.
# Output structure tests (section: "Atlas Output Structure") also require
# /code-atlas to have been run first.
#
# Usage: bash .claude/skills/code-atlas/tests/test_layer7_8.sh
# Exit:  0 = all tests passed, non-zero = failures

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
ATLAS_DIR="${REPO_ROOT}/docs/atlas"

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
        echo "FAIL: $label — '$pattern' not found in $file"
        FAIL=$((FAIL + 1))
    fi
}

assert_file_exists() {
    local label="$1"; local file="$2"
    if [[ -f "$file" ]]; then
        echo "PASS: $label"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label — file not found: $file"
        FAIL=$((FAIL + 1))
    fi
}

assert_dir_exists() {
    local label="$1"; local dir="$2"
    if [[ -d "$dir" ]]; then
        echo "PASS: $label"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label — directory not found: $dir"
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
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "FAIL: $label — forbidden pattern '$pattern' found in $file"
        FAIL=$((FAIL + 1))
    else
        echo "PASS: $label"
        PASS=$((PASS + 1))
    fi
}

echo ""
echo "=== Test Suite: Layer 7 and Layer 8 Contracts ==="
echo ""

# ---------------------------------------------------------------------------
# SECTION 1: SKILL.md Documentation Tests
# ---------------------------------------------------------------------------
echo "--- SKILL.md: Layer 7 Documentation ---"

SKILL_MD="${SKILL_DIR}/SKILL.md"

assert_file_contains \
    "SKILL.md contains Layer 7 heading" \
    "Layer 7: Service Component Architecture" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md Layer 7 references SEC-11" \
    "SEC-11" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md Layer 7 mentions per-service module structure" \
    "per-service\|internal.*module\|package.*structure" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md Layer 7 output path documented" \
    "service-components" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md Layer 7 service name sanitisation documented" \
    "sanitis\|a-zA-Z0-9_-.*1,64" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md Layer 7 density guard applies" \
    "Density guard" \
    "$SKILL_MD"

echo ""
echo "--- SKILL.md: Layer 8 Documentation ---"

assert_file_contains \
    "SKILL.md contains Layer 8 heading" \
    "Layer 8: AST+LSP Symbol Bindings" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md Layer 8 references SEC-12" \
    "SEC-12" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md Layer 8 references SEC-15" \
    "SEC-15" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md Layer 8 lists operating modes" \
    "lsp-assisted\|static-approximation" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md Layer 8 mode label contract documented" \
    "Mode.*line 1\|line 1.*Mode" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md Layer 8 lists dead-code.md output" \
    "dead-code.md" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md Layer 8 lists mismatched-interfaces.md output" \
    "mismatched-interfaces.md" \
    "$SKILL_MD"

assert_file_contains \
    "SKILL.md Layer 8 lists symbol-references.mmd output" \
    "symbol-references.mmd" \
    "$SKILL_MD"

# ---------------------------------------------------------------------------
# SECTION 2: API-CONTRACTS.md Tests
# ---------------------------------------------------------------------------
echo ""
echo "--- API-CONTRACTS.md: Layer 7/8 Contracts ---"

API_MD="${SKILL_DIR}/API-CONTRACTS.md"

assert_file_contains \
    "API-CONTRACTS.md version is v1.1.0" \
    "1.1.0" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md LayerID updated to include 7 and 8" \
    "LayerID.*7.*8\|7.*8.*LayerID\|1.*2.*3.*4.*5.*6.*7.*8" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md contains Layer 7 filesystem contract" \
    "Layer7Output\|service-components" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md contains Layer 8 filesystem contract" \
    "Layer8Output\|ast-lsp-bindings" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md contains LAYER7_SOURCE_NOT_FOUND error code" \
    "LAYER7_SOURCE_NOT_FOUND" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md contains LAYER8_LSP_UNAVAILABLE error code" \
    "LAYER8_LSP_UNAVAILABLE" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md contains DENSITY_THRESHOLD_EXCEEDED error code" \
    "DENSITY_THRESHOLD_EXCEEDED" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md documents lsp-setup delegation contract (§2f)" \
    "lsp-setup\|LSPSetupDelegation" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md contains LSPSymbolReport schema" \
    "LSPSymbolReport" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md contains StaticSymbolReport schema" \
    "StaticSymbolReport\|static-approximation" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md documents mode label contract" \
    "mode.*label\|Mode.*line.*1\|first line" \
    "$API_MD"

assert_file_contains \
    "API-CONTRACTS.md BugReport pass extended to 1|2|3" \
    "pass.*1.*2.*3\|1 | 2 | 3" \
    "$API_MD"

# ---------------------------------------------------------------------------
# SECTION 3: SECURITY.md Tests (SEC-11 through SEC-16)
# ---------------------------------------------------------------------------
echo ""
echo "--- SECURITY.md: SEC-11 through SEC-16 ---"

SEC_MD="${SKILL_DIR}/SECURITY.md"

assert_file_contains \
    "SECURITY.md contains SEC-11 service name sanitisation" \
    "SEC-11" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md SEC-11 regex pattern documented" \
    "a-zA-Z0-9_-.*1,64" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md contains SEC-12 LSP output sanitisation" \
    "SEC-12" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md contains SEC-15 Layer 8 credential redaction" \
    "SEC-15" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md SEC-15 lists all four Layer 8 files" \
    "symbol-references.mmd" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md contains SEC-16 relative-path enforcement" \
    "SEC-16" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md SEC-16 mentions os.path.relpath" \
    "relpath\|relative.*path" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md SEC-09 scope extended to Layer 8 outputs" \
    "Layer 8.*output\|layer8.*output" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md SEC-10 scope extended to experiments/" \
    "experiments" \
    "$SEC_MD"

assert_file_contains \
    "SECURITY.md checklist includes SEC-11" \
    "SEC-11.*sanitised\|sanitised.*SEC-11" \
    "$SEC_MD"

# ---------------------------------------------------------------------------
# SECTION 4: Atlas Output Structure Tests (require /code-atlas to have run)
# ---------------------------------------------------------------------------
echo ""
echo "--- Atlas Output Structure (requires /code-atlas run first) ---"

assert_dir_exists \
    "service-components/ directory exists" \
    "${ATLAS_DIR}/service-components"

assert_file_exists \
    "service-components/README.md exists" \
    "${ATLAS_DIR}/service-components/README.md"

assert_dir_exists \
    "ast-lsp-bindings/ directory exists" \
    "${ATLAS_DIR}/ast-lsp-bindings"

assert_file_exists \
    "ast-lsp-bindings/README.md exists" \
    "${ATLAS_DIR}/ast-lsp-bindings/README.md"

assert_file_exists \
    "ast-lsp-bindings/symbol-references.mmd exists" \
    "${ATLAS_DIR}/ast-lsp-bindings/symbol-references.mmd"

assert_file_exists \
    "ast-lsp-bindings/dead-code.md exists" \
    "${ATLAS_DIR}/ast-lsp-bindings/dead-code.md"

assert_file_exists \
    "ast-lsp-bindings/mismatched-interfaces.md exists" \
    "${ATLAS_DIR}/ast-lsp-bindings/mismatched-interfaces.md"

# Layer 8 README mode label on line 1 (SEC-12)
if [[ -f "${ATLAS_DIR}/ast-lsp-bindings/README.md" ]]; then
    first_line=$(head -1 "${ATLAS_DIR}/ast-lsp-bindings/README.md")
    if echo "$first_line" | grep -q "\*\*Mode:\*\*.*lsp-assisted\|\*\*Mode:\*\*.*static-approximation"; then
        echo "PASS: Layer 8 README line 1 contains mode label"
        PASS=$((PASS + 1))
    else
        echo "FAIL: Layer 8 README line 1 does not start with '**Mode:**' — got: '$first_line'"
        FAIL=$((FAIL + 1))
    fi
else
    echo "FAIL: Layer 8 README not found (run /code-atlas first)"
    FAIL=$((FAIL + 1))
fi

# SEC-16: no absolute paths in Layer 8 dead-code.md
if [[ -f "${ATLAS_DIR}/ast-lsp-bindings/dead-code.md" ]]; then
    if grep -qP '^/' "${ATLAS_DIR}/ast-lsp-bindings/dead-code.md" 2>/dev/null; then
        echo "FAIL: SEC-16 violation — absolute path found in layer8/dead-code.md"
        FAIL=$((FAIL + 1))
    else
        echo "PASS: SEC-16 — no absolute paths in layer8/dead-code.md"
        PASS=$((PASS + 1))
    fi
else
    echo "FAIL: layer8/dead-code.md not found (run /code-atlas first)"
    FAIL=$((FAIL + 1))
fi

# SEC-15: no raw credential patterns in Layer 8 outputs (verify redaction worked)
for f in symbol-references.mmd dead-code.md mismatched-interfaces.md; do
    layer8_file="${ATLAS_DIR}/ast-lsp-bindings/${f}"
    if [[ -f "$layer8_file" ]]; then
        if grep -qiP 'password\s*=\s*\S+|secret\s*=\s*\S+|token\s*=\s*\S+|api_key\s*=\s*\S+' "$layer8_file" 2>/dev/null; then
            echo "FAIL: SEC-15 violation — potential credential in layer8/${f}"
            FAIL=$((FAIL + 1))
        else
            echo "PASS: SEC-15 — no obvious credential patterns in layer8/${f}"
            PASS=$((PASS + 1))
        fi
    fi
done

# ---------------------------------------------------------------------------
# SECTION 5: Recipe YAML Tests
# ---------------------------------------------------------------------------
echo ""
echo "--- Recipe YAML: code-atlas.yaml ---"

RECIPE="${REPO_ROOT}/amplifier-bundle/recipes/code-atlas.yaml"

assert_file_exists \
    "amplifier-bundle/recipes/code-atlas.yaml exists" \
    "$RECIPE"

assert_file_contains \
    "Recipe has exactly 10 steps" \
    "validate-prerequisites\|build-all-layers\|bug-hunt-mermaid\|bug-hunt-graphviz\|merge-bug-findings\|validate-bugs-security\|validate-bugs-architect\|validate-bugs-tester\|tally-validation-votes\|ensure-label\|file-issues\|ingest-to-graph\|publish-atlas\|summarise-and-report" \
    "$RECIPE"

assert_file_contains \
    "Recipe step: validate-prerequisites" \
    "validate-prerequisites" \
    "$RECIPE"

assert_file_contains \
    "Recipe step: build-all-layers" \
    "build-all-layers" \
    "$RECIPE"

assert_file_contains \
    "Recipe step: build-all-layers" \
    "build-all-layers" \
    "$RECIPE"

assert_file_contains \
    "Recipe step: build-all-layers" \
    "build-all-layers" \
    "$RECIPE"

assert_file_contains \
    "Recipe step: build-all-layers" \
    "build-all-layers" \
    "$RECIPE"

assert_file_contains \
    "Recipe step: bug-hunt-mermaid" \
    "bug-hunt-mermaid" \
    "$RECIPE"

assert_file_contains \
    "Recipe step: bug-hunt-graphviz" \
    "bug-hunt-graphviz" \
    "$RECIPE"

assert_file_contains \
    "Recipe step: merge-bug-findings" \
    "merge-bug-findings" \
    "$RECIPE"

assert_file_contains \
    "Recipe step: publish-atlas" \
    "publish-atlas" \
    "$RECIPE"

assert_file_contains \
    "Recipe step: summarise-and-report" \
    "summarise-and-report" \
    "$RECIPE"

assert_file_contains \
    "Recipe SEC-17: parameters passed as structured data" \
    "SEC-17\|structured data\|no shell interpolation\|yaml.safe_load" \
    "$RECIPE"

# Validate YAML is parseable
if command -v python3 &>/dev/null; then
    if python3 -c "import yaml; yaml.safe_load(open('${RECIPE}'))" 2>/dev/null; then
        echo "PASS: Recipe YAML is valid (python3 yaml.safe_load)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: Recipe YAML is invalid — parse error"
        FAIL=$((FAIL + 1))
    fi
else
    echo "SKIP: python3 not available — cannot validate YAML syntax"
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
