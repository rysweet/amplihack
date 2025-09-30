#!/bin/bash
# C# Post-Edit Validation Tool - Main Orchestrator
# Coordinates validation pipeline and aggregates results

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CONFIG_FILE="${ROOT_DIR}/.claude/config/cs-validator.json"
CACHE_DIR="${ROOT_DIR}/.cache/cs-validator"

# Default settings
VALIDATION_LEVEL=2
VERBOSE=false
TIMEOUT_SECONDS=30

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --level)
            VALIDATION_LEVEL="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --timeout)
            TIMEOUT_SECONDS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: cs-validator.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --level N          Validation level (1-4, default: 2)"
            echo "  --config PATH      Config file path (default: .claude/config/cs-validator.json)"
            echo "  --verbose          Enable verbose output"
            echo "  --timeout SECONDS  Timeout in seconds (default: 30)"
            echo "  --help             Show this help message"
            echo ""
            echo "Validation Levels:"
            echo "  1 - Syntax check only"
            echo "  2 - Syntax + Build (default)"
            echo "  3 - Syntax + Build + Analyzers"
            echo "  4 - Syntax + Build + Analyzers + Format"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 2
            ;;
    esac
done

# Load configuration if exists
if [ -f "$CONFIG_FILE" ]; then
    if command -v jq &> /dev/null; then
        VALIDATION_LEVEL=$(jq -r '.validationLevel // 2' "$CONFIG_FILE")
        TIMEOUT_SECONDS=$(jq -r '.timeoutSeconds // 30' "$CONFIG_FILE")
        VERBOSE=$(jq -r '.reporting.verbose // false' "$CONFIG_FILE")
    fi
fi

# Check if skip validation is set
if [ "${SKIP_CS_VALIDATION:-0}" = "1" ]; then
    echo "⚠ C# validation skipped (SKIP_CS_VALIDATION=1)"
    exit 0
fi

# Get modified .cs files
MODIFIED_FILES=$(git diff --name-only --diff-filter=ACMR HEAD 2>/dev/null | grep '\.cs$' || true)

if [ -z "$MODIFIED_FILES" ]; then
    echo "✓ No C# files modified"
    exit 0
fi

FILE_COUNT=$(echo "$MODIFIED_FILES" | wc -l | tr -d ' ')
[ "$VERBOSE" = true ] && echo "Found $FILE_COUNT modified C# file(s)"

# Initialize results
mkdir -p "$CACHE_DIR"
RESULTS_FILE="$CACHE_DIR/results.json"
START_TIME=$(date +%s)

cat > "$RESULTS_FILE" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "passed": true,
  "validationLevel": $VALIDATION_LEVEL,
  "checks": [],
  "summary": {
    "totalErrors": 0,
    "totalWarnings": 0,
    "filesChecked": $FILE_COUNT
  }
}
EOF

# Function to update results
update_result() {
    local check_name=$1
    local passed=$2
    local duration=$3
    local errors=${4:-0}

    if command -v jq &> /dev/null; then
        jq --arg name "$check_name" \
           --argjson passed "$passed" \
           --argjson duration "$duration" \
           --argjson errors "$errors" \
           '.checks += [{"name": $name, "passed": $passed, "durationMs": $duration}] |
            .summary.totalErrors += $errors |
            if $passed == false then .passed = false else . end' \
           "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
    fi
}

# Function to run check with timeout
run_check() {
    local check_name=$1
    local check_script=$2
    shift 2

    [ "$VERBOSE" = true ] && echo "  Running $check_name..."

    local check_start=$(date +%s%3N)
    local result=0

    # Run check with timeout
    if timeout "$TIMEOUT_SECONDS" "$check_script" $MODIFIED_FILES; then
        result=0
    else
        result=$?
        if [ $result -eq 124 ]; then
            echo "✗ $check_name timed out after ${TIMEOUT_SECONDS}s"
            exit 3
        fi
    fi

    local check_end=$(date +%s%3N)
    local duration=$((check_end - check_start))

    if [ $result -eq 0 ]; then
        update_result "$check_name" true "$duration" 0
        [ "$VERBOSE" = true ] && echo "  ✓ $check_name passed (${duration}ms)"
    else
        update_result "$check_name" false "$duration" 1
        [ "$VERBOSE" = true ] && echo "  ✗ $check_name failed (${duration}ms)"
    fi

    return $result
}

echo "Running C# validation (Level $VALIDATION_LEVEL)..."

# Level 1: Syntax Check (always run, fast)
if ! run_check "syntax" "$SCRIPT_DIR/csharp-syntax-check.py"; then
    echo ""
    echo "✗ Syntax validation failed"
    END_TIME=$(date +%s)
    TOTAL_TIME=$((END_TIME - START_TIME))
    if command -v jq &> /dev/null; then
        jq --argjson time "$TOTAL_TIME" '.executionTimeMs = ($time * 1000)' "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
        cat "$RESULTS_FILE"
    fi
    exit 1
fi

# Level 2: Build Check
if [ "$VALIDATION_LEVEL" -ge 2 ]; then
    if ! run_check "build" "$SCRIPT_DIR/build-check.sh"; then
        echo ""
        echo "✗ Build validation failed"
        END_TIME=$(date +%s)
        TOTAL_TIME=$((END_TIME - START_TIME))
        if command -v jq &> /dev/null; then
            jq --argjson time "$TOTAL_TIME" '.executionTimeMs = ($time * 1000)' "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
            cat "$RESULTS_FILE"
        fi
        exit 1
    fi
fi

# Level 3+4: Parallel analyzer and format checks
if [ "$VALIDATION_LEVEL" -ge 3 ]; then
    ANALYZER_RESULT=0
    FORMAT_RESULT=0

    # Run analyzer check
    run_check "analyzer" "$SCRIPT_DIR/analyzer-check.sh" &
    ANALYZER_PID=$!

    # Run format check if level 4
    if [ "$VALIDATION_LEVEL" -ge 4 ]; then
        run_check "format" "$SCRIPT_DIR/format-check.sh" &
        FORMAT_PID=$!
    fi

    # Wait for analyzer
    wait $ANALYZER_PID || ANALYZER_RESULT=$?

    # Wait for format if running
    if [ "$VALIDATION_LEVEL" -ge 4 ]; then
        wait $FORMAT_PID || FORMAT_RESULT=$?
    fi

    # Check results
    if [ $ANALYZER_RESULT -ne 0 ] || [ $FORMAT_RESULT -ne 0 ]; then
        echo ""
        echo "✗ Code quality validation failed"
        END_TIME=$(date +%s)
        TOTAL_TIME=$((END_TIME - START_TIME))
        if command -v jq &> /dev/null; then
            jq --argjson time "$TOTAL_TIME" '.executionTimeMs = ($time * 1000)' "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
            cat "$RESULTS_FILE"
        fi
        exit 1
    fi
fi

# Calculate total time
END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

# Update final results
if command -v jq &> /dev/null; then
    jq --argjson time "$TOTAL_TIME" '.executionTimeMs = ($time * 1000)' "$RESULTS_FILE" > "$RESULTS_FILE.tmp" && mv "$RESULTS_FILE.tmp" "$RESULTS_FILE"
fi

# Output results
echo ""
echo "✓ All validation checks passed"
[ "$VERBOSE" = true ] && echo "  Total time: ${TOTAL_TIME}s"

exit 0
