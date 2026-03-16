#!/bin/bash
# .claude/skills/code-atlas/tests/run_all_tests.sh
#
# Unified test runner for the code-atlas skill.
# Runs all test suites and reports a combined pass/fail summary.
#
# Usage:
#   bash .claude/skills/code-atlas/tests/run_all_tests.sh
#   bash .claude/skills/code-atlas/tests/run_all_tests.sh --fast   # skip integration tests
#
# Exit: 0 = all suites passed, non-zero = one or more failures
#
# Test Suites:
#   1. test_staleness_triggers.sh       — Layer detection for all 8 layer patterns
#   2. test_rebuild_script.sh           — rebuild-atlas-all.sh behaviors
#   3. test_security_controls.sh        — SEC-01 through SEC-10 controls
#   4. test_atlas_output_structure.sh   — docs/atlas/ output directory structure
#   5. test_layer_contracts.sh          — Per-layer content contracts (Layers 1–8)
#   6. test_bug_hunt_workflow.sh        — Three-pass bug hunt report format
#   7. test_ci_workflow.sh              — CI YAML structure and script path checks
#   8. test_publication_workflow.sh     — SVG generation and GitHub Pages readiness
#   9. test_layer7_8.sh                 — Layer 7/8 output contracts + SEC-11/12/15/16
#  10. test_no_silent_degradation.sh    — Density guard FORBIDDEN_PATTERNS §2 compliance

# Intentionally omits -e: test failures must not abort the suite runner.
# Individual test scripts use set -euo pipefail.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FAST_MODE=false
[[ "${1:-}" == "--fast" ]] && FAST_MODE=true

# ---------------------------------------------------------------------------
# ANSI colors (if terminal supports them)
# ---------------------------------------------------------------------------
if [[ -t 1 ]]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RESET='\033[0m'
    BOLD='\033[1m'
else
    RED=''; GREEN=''; YELLOW=''; RESET=''; BOLD=''
fi

# ---------------------------------------------------------------------------
# Suite runner
# ---------------------------------------------------------------------------
TOTAL_PASS=0
TOTAL_FAIL=0
SUITE_RESULTS=()

run_suite() {
    local name="$1"
    local script="$2"
    local skip_in_fast="${3:-false}"

    if [[ "$FAST_MODE" == "true" && "$skip_in_fast" == "true" ]]; then
        echo -e "${YELLOW}SKIP${RESET}: $name (--fast mode)"
        SUITE_RESULTS+=("SKIP: $name")
        return
    fi

    echo ""
    echo -e "${BOLD}━━━ Suite: $name ━━━${RESET}"

    if [[ ! -f "$script" ]]; then
        echo -e "${RED}ERROR${RESET}: Script not found: $script"
        SUITE_RESULTS+=("ERROR: $name — script not found")
        TOTAL_FAIL=$((TOTAL_FAIL + 1))
        return
    fi

    # Run the suite, capture output and exit code
    suite_output=$(bash "$script" 2>&1)
    suite_exit=$?

    # Show output
    echo "$suite_output"

    # Extract pass/fail counts — single grep, then pure bash string ops (no PCRE, no extra forks).
    local results_line
    results_line=$(grep -o 'Results: [0-9]* passed, [0-9]* failed' <<< "$suite_output" | tail -1)
    if [[ -n "$results_line" ]]; then
        pass_count="${results_line#Results: }"; pass_count="${pass_count%% *}"
        fail_count="${results_line##*, }";      fail_count="${fail_count%% *}"
    else
        pass_count=0
        fail_count=0
    fi

    TOTAL_PASS=$((TOTAL_PASS + pass_count))
    TOTAL_FAIL=$((TOTAL_FAIL + fail_count))

    if [[ "$suite_exit" -eq 0 ]]; then
        SUITE_RESULTS+=("$(echo -e "${GREEN}PASS${RESET}"): $name ($pass_count passed)")
    else
        SUITE_RESULTS+=("$(echo -e "${RED}FAIL${RESET}"): $name ($pass_count passed, $fail_count failed)")
    fi
}

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}╔════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║     Code Atlas — TDD Test Runner       ║${RESET}"
echo -e "${BOLD}╚════════════════════════════════════════╝${RESET}"
echo ""
echo "Running all test suites..."
[[ "$FAST_MODE" == "true" ]] && echo "(Fast mode: integration tests skipped)"

# ---------------------------------------------------------------------------
# Suite 1: Staleness Triggers
# ---------------------------------------------------------------------------
run_suite \
    "Staleness Triggers (check-atlas-staleness.sh)" \
    "${SCRIPT_DIR}/test_staleness_triggers.sh"

# ---------------------------------------------------------------------------
# Suite 2: Rebuild Script
# ---------------------------------------------------------------------------
run_suite \
    "Rebuild Script (rebuild-atlas-all.sh)" \
    "${SCRIPT_DIR}/test_rebuild_script.sh"

# ---------------------------------------------------------------------------
# Suite 3: Security Controls
# ---------------------------------------------------------------------------
run_suite \
    "Security Controls (SEC-01 through SEC-10)" \
    "${SCRIPT_DIR}/test_security_controls.sh"

# ---------------------------------------------------------------------------
# Suite 4: Atlas Output Structure
# ---------------------------------------------------------------------------
run_suite \
    "Atlas Output Structure (docs/atlas/ directory contract)" \
    "${SCRIPT_DIR}/test_atlas_output_structure.sh" \
    "false"  # not skipped in fast mode — but tests will fail until /code-atlas runs

# ---------------------------------------------------------------------------
# Suite 5: Layer Content Contracts
# ---------------------------------------------------------------------------
run_suite \
    "Layer Content Contracts (per-layer output requirements)" \
    "${SCRIPT_DIR}/test_layer_contracts.sh"

# ---------------------------------------------------------------------------
# Suite 6: Bug Hunt Workflow
# ---------------------------------------------------------------------------
run_suite \
    "Bug Hunt Workflow (Pass 1 + Pass 2 report format)" \
    "${SCRIPT_DIR}/test_bug_hunt_workflow.sh"

# ---------------------------------------------------------------------------
# Suite 7: CI Workflow
# ---------------------------------------------------------------------------
run_suite \
    "CI Workflow (atlas-ci.yml structure + integration)" \
    "${SCRIPT_DIR}/test_ci_workflow.sh"

# ---------------------------------------------------------------------------
# Suite 8: Publication Workflow
# ---------------------------------------------------------------------------
run_suite \
    "Publication Workflow (SVG generation + GitHub Pages readiness)" \
    "${SCRIPT_DIR}/test_publication_workflow.sh"

# ---------------------------------------------------------------------------
# Suite 9: Layer 7 and Layer 8 Contracts (v1.1.0)
# ---------------------------------------------------------------------------
run_suite \
    "Layer 7 and 8 Contracts (service components + AST/LSP bindings)" \
    "${SCRIPT_DIR}/test_layer7_8.sh"

# ---------------------------------------------------------------------------
# Suite 10: No Silent Degradation — FORBIDDEN_PATTERNS §2 Compliance (v1.1.0)
# ---------------------------------------------------------------------------
run_suite \
    "No Silent Degradation (density guard + FORBIDDEN_PATTERNS §2)" \
    "${SCRIPT_DIR}/test_no_silent_degradation.sh"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}════════════════════════════════════════${RESET}"
echo -e "${BOLD}           Test Suite Summary           ${RESET}"
echo -e "${BOLD}════════════════════════════════════════${RESET}"
echo ""
for result in "${SUITE_RESULTS[@]}"; do
    echo "  $result"
done
echo ""
echo -e "  Total: ${GREEN}${TOTAL_PASS} passed${RESET}, ${RED}${TOTAL_FAIL} failed${RESET}"
echo ""

if [[ "$TOTAL_FAIL" -gt 0 ]]; then
    echo -e "${RED}Some tests failed.${RESET}"
    echo ""
    echo "Expected failures (require /code-atlas to run first):"
    echo "  • test_atlas_output_structure.sh: docs/atlas/ doesn't exist (run /code-atlas first)"
    echo "  • test_layer_contracts.sh: docs/atlas/ doesn't exist (run /code-atlas first)"
    echo "  • test_publication_workflow.sh: SVGs not generated (run /code-atlas publish first)"
    echo "  • test_bug_hunt_workflow.sh: bug reports not generated (run /code-atlas first)"
    echo "  • test_layer7_8.sh (output structure section): layer7/8 dirs not yet created (run /code-atlas first)"
    echo "  • test_no_silent_degradation.sh: should pass on documentation alone (no atlas run needed)"
    echo ""
    echo "Unexpected failures need investigation."
    exit 1
else
    echo -e "${GREEN}All 10 test suites passed. Atlas skill is fully implemented.${RESET}"
    exit 0
fi
