#!/usr/bin/env bash
# End-to-End tests for dynamic-debugger skill
#
# Testing pyramid distribution:
# - This file contains 3 E2E tests (~10% of total test coverage)
# - Tests focus on complete debugging scenarios from start to finish

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
SCRIPTS_DIR="${SKILL_DIR}/scripts"

# Temporary directory for tests
TEST_TEMP_DIR=""

# Cleanup function
cleanup() {
    if [[ -n "${TEST_TEMP_DIR}" ]] && [[ -d "${TEST_TEMP_DIR}" ]]; then
        echo "Cleaning up test directory: ${TEST_TEMP_DIR}"
        rm -rf "${TEST_TEMP_DIR}"
    fi

    # Clean up any test artifacts in skill directory
    rm -f "${SKILL_DIR}/.dap_mcp.pid"
    rm -f "${SKILL_DIR}/.dap_mcp.log"
}

trap cleanup EXIT

# Helper functions
log_test() {
    echo ""
    echo "==========================================="
    echo "TEST: $1"
    echo "==========================================="
}

log_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

log_skip() {
    echo -e "${YELLOW}⊘ SKIP:${NC} $1"
    TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
}

# Setup test environment
setup_test_env() {
    TEST_TEMP_DIR=$(mktemp -d)
    echo "Created test directory: ${TEST_TEMP_DIR}"
}

create_python_project() {
    local project_dir="$1"

    mkdir -p "${project_dir}"

    # Create requirements.txt
    cat > "${project_dir}/requirements.txt" <<'EOF'
pytest>=7.0.0
requests>=2.28.0
EOF

    # Create main.py
    cat > "${project_dir}/main.py" <<'EOF'
def main():
    print("Hello from Python!")
    result = calculate(5, 3)
    print(f"Result: {result}")

def calculate(a, b):
    return a + b

if __name__ == "__main__":
    main()
EOF

    # Create a bug for debugging
    cat > "${project_dir}/buggy.py" <<'EOF'
def divide(a, b):
    # Intentional bug: no zero check
    return a / b

if __name__ == "__main__":
    print(divide(10, 0))  # Will cause error
EOF

    echo "Created Python project at: ${project_dir}"
}

create_javascript_project() {
    local project_dir="$1"

    mkdir -p "${project_dir}"

    # Create package.json
    cat > "${project_dir}/package.json" <<'EOF'
{
  "name": "test-project",
  "version": "1.0.0",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "test": "echo \"No tests yet\""
  }
}
EOF

    # Create index.js
    cat > "${project_dir}/index.js" <<'EOF'
function main() {
    console.log("Hello from JavaScript!");
    const result = calculate(5, 3);
    console.log("Result:", result);
}

function calculate(a, b) {
    return a + b;
}

main();
EOF

    echo "Created JavaScript project at: ${project_dir}"
}

# ============================================================================
# E2E TEST 1: Complete Python Debugging Session
# ============================================================================

test_e2e_python_debug_session() {
    log_test "E2E Test 1: Complete Python Debugging Session"

    setup_test_env
    local project_dir="${TEST_TEMP_DIR}/python_project"
    create_python_project "${project_dir}"

    # Step 1: Detect language
    echo "Step 1: Detecting language..."
    if ! python3 "${SCRIPTS_DIR}/detect_language.py" --path "${project_dir}" --json > "${TEST_TEMP_DIR}/detect_result.json"; then
        log_fail "Language detection failed"
        return 1
    fi

    local detected_lang=$(jq -r '.language' "${TEST_TEMP_DIR}/detect_result.json")
    local detected_debugger=$(jq -r '.debugger' "${TEST_TEMP_DIR}/detect_result.json")

    if [[ "${detected_lang}" != "python" ]]; then
        log_fail "Expected language 'python', got '${detected_lang}'"
        return 1
    fi

    if [[ "${detected_debugger}" != "debugpy" ]]; then
        log_fail "Expected debugger 'debugpy', got '${detected_debugger}'"
        return 1
    fi

    echo "  ✓ Detected: ${detected_lang} (debugger: ${detected_debugger})"

    # Step 2: Generate configuration
    echo "Step 2: Generating DAP configuration..."
    if ! python3 "${SCRIPTS_DIR}/generate_dap_config.py" \
        "${detected_lang}" \
        --project-dir "${project_dir}" \
        --entry-point "main" \
        --output "${TEST_TEMP_DIR}/debug_config.json" \
        --validate; then
        log_fail "Configuration generation failed"
        return 1
    fi

    if [[ ! -f "${TEST_TEMP_DIR}/debug_config.json" ]]; then
        log_fail "Configuration file not created"
        return 1
    fi

    echo "  ✓ Configuration generated and validated"

    # Step 3: Verify configuration structure
    echo "Step 3: Verifying configuration structure..."
    local config_name=$(jq -r '.name' "${TEST_TEMP_DIR}/debug_config.json")
    local config_type=$(jq -r '.type' "${TEST_TEMP_DIR}/debug_config.json")
    local config_request=$(jq -r '.request' "${TEST_TEMP_DIR}/debug_config.json")

    if [[ -z "${config_name}" ]] || [[ "${config_name}" == "null" ]]; then
        log_fail "Configuration missing 'name' field"
        return 1
    fi

    if [[ "${config_type}" != "python" ]]; then
        log_fail "Configuration type should be 'python', got '${config_type}'"
        return 1
    fi

    if [[ -z "${config_request}" ]] || [[ "${config_request}" == "null" ]]; then
        log_fail "Configuration missing 'request' field"
        return 1
    fi

    echo "  ✓ Configuration structure valid"

    # Step 4: Test cleanup
    echo "Step 4: Testing cleanup workflow..."
    # Create mock PID file
    echo "99999" > "${SKILL_DIR}/.dap_mcp.pid"

    if bash "${SCRIPTS_DIR}/cleanup_debug.sh"; then
        echo "  ✓ Cleanup completed successfully"
    else
        log_fail "Cleanup failed"
        return 1
    fi

    # Verify PID file was removed
    if [[ -f "${SKILL_DIR}/.dap_mcp.pid" ]]; then
        log_fail "PID file not removed by cleanup"
        return 1
    fi

    log_pass "Complete Python debugging session workflow"
}

# ============================================================================
# E2E TEST 2: Multi-Language Project Detection
# ============================================================================

test_e2e_multi_language_detection() {
    log_test "E2E Test 2: Multi-Language Project (Python Dominant)"

    setup_test_env
    local project_dir="${TEST_TEMP_DIR}/multi_lang_project"
    mkdir -p "${project_dir}"

    # Create multiple Python files (dominant)
    for i in {1..5}; do
        echo "# Python script ${i}" > "${project_dir}/script_${i}.py"
    done

    # Create fewer JavaScript files
    for i in {1..2}; do
        echo "// JavaScript script ${i}" > "${project_dir}/script_${i}.js"
    done

    # Add Python manifest for higher confidence
    echo "pytest>=7.0.0" > "${project_dir}/requirements.txt"

    # Detect language
    echo "Detecting dominant language in mixed project..."
    if ! python3 "${SCRIPTS_DIR}/detect_language.py" \
        --path "${project_dir}" \
        --json > "${TEST_TEMP_DIR}/multi_detect.json"; then
        log_fail "Detection failed for multi-language project"
        return 1
    fi

    local detected_lang=$(jq -r '.language' "${TEST_TEMP_DIR}/multi_detect.json")
    local confidence=$(jq -r '.confidence' "${TEST_TEMP_DIR}/multi_detect.json")

    if [[ "${detected_lang}" != "python" ]]; then
        log_fail "Expected 'python' as dominant language, got '${detected_lang}'"
        return 1
    fi

    echo "  ✓ Correctly detected Python as dominant (confidence: ${confidence})"

    # Generate config for detected language
    echo "Generating config for detected language..."
    if ! python3 "${SCRIPTS_DIR}/generate_dap_config.py" \
        "${detected_lang}" \
        --project-dir "${project_dir}" \
        --output "${TEST_TEMP_DIR}/multi_config.json" \
        --validate; then
        log_fail "Config generation failed for multi-language project"
        return 1
    fi

    echo "  ✓ Configuration generated successfully"

    log_pass "Multi-language project detection and configuration"
}

# ============================================================================
# E2E TEST 3: Error Recovery Scenario
# ============================================================================

test_e2e_error_recovery() {
    log_test "E2E Test 3: Error Recovery (Stale PID and Retry)"

    setup_test_env
    local project_dir="${TEST_TEMP_DIR}/recovery_project"
    create_python_project "${project_dir}"

    # Step 1: Create stale PID file
    echo "Simulating stale PID file scenario..."
    echo "99999" > "${SKILL_DIR}/.dap_mcp.pid"  # Non-existent PID

    # Step 2: Cleanup should handle stale PID
    echo "Running cleanup on stale PID..."
    if ! bash "${SCRIPTS_DIR}/cleanup_debug.sh"; then
        log_fail "Cleanup failed to handle stale PID"
        return 1
    fi

    # Verify cleanup removed stale PID
    if [[ -f "${SKILL_DIR}/.dap_mcp.pid" ]]; then
        log_fail "Stale PID file not removed"
        return 1
    fi

    echo "  ✓ Stale PID file cleaned up"

    # Step 3: Retry workflow after cleanup
    echo "Retrying detection and config generation..."
    if ! python3 "${SCRIPTS_DIR}/detect_language.py" \
        --path "${project_dir}" \
        --json > "${TEST_TEMP_DIR}/retry_detect.json"; then
        log_fail "Detection failed after cleanup"
        return 1
    fi

    local lang=$(jq -r '.language' "${TEST_TEMP_DIR}/retry_detect.json")

    if ! python3 "${SCRIPTS_DIR}/generate_dap_config.py" \
        "${lang}" \
        --project-dir "${project_dir}" \
        --output "${TEST_TEMP_DIR}/retry_config.json" \
        --validate; then
        log_fail "Config generation failed after cleanup"
        return 1
    fi

    echo "  ✓ Workflow succeeded after recovery"

    log_pass "Error recovery and retry workflow"
}

# ============================================================================
# Main Test Runner
# ============================================================================

main() {
    echo "=========================================="
    echo "Dynamic Debugger E2E Test Suite"
    echo "=========================================="
    echo ""

    # Check prerequisites
    if ! command -v python3 &> /dev/null; then
        echo "ERROR: python3 not found. Required for tests."
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        echo "ERROR: jq not found. Required for JSON parsing."
        echo "Install with: sudo apt-get install jq  # or brew install jq"
        exit 1
    fi

    # Run E2E tests
    test_e2e_python_debug_session || true
    test_e2e_multi_language_detection || true
    test_e2e_error_recovery || true

    # Print summary
    echo ""
    echo "=========================================="
    echo "E2E Test Summary"
    echo "=========================================="
    echo -e "${GREEN}Passed:${NC}  ${TESTS_PASSED}"
    echo -e "${RED}Failed:${NC}  ${TESTS_FAILED}"
    echo -e "${YELLOW}Skipped:${NC} ${TESTS_SKIPPED}"
    echo "=========================================="

    # Exit with appropriate code
    if [[ ${TESTS_FAILED} -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

# Run main if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
