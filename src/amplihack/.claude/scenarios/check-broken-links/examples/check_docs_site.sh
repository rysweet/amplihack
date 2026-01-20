#!/usr/bin/env bash
#
# check_docs_site.sh - Example script for checking amplihack documentation links
#
# This script demonstrates typical usage of the check-broken-links tool
# to validate the amplihack GitHub Pages documentation site.
#
# Usage:
#   ./check_docs_site.sh
#   ./check_docs_site.sh --verbose
#   ./check_docs_site.sh --json

set -euo pipefail

# Configuration
DOCS_URL="https://rysweet.github.io/amplihack/"
TIMEOUT=10000  # 10 seconds for remote site
VERBOSE=false
JSON_OUTPUT=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --verbose)
            VERBOSE=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--verbose] [--json] [--help]"
            echo ""
            echo "Check amplihack documentation site for broken links."
            echo ""
            echo "Options:"
            echo "  --verbose    Show detailed progress"
            echo "  --json       Output results as JSON"
            echo "  --help       Show this help message"
            exit 0
            ;;
    esac
done

# Print banner
if [ "$JSON_OUTPUT" = false ]; then
    echo "======================================"
    echo "amplihack Documentation Link Checker"
    echo "======================================"
    echo ""
    echo "Target: $DOCS_URL"
    echo "Timeout: ${TIMEOUT}ms"
    echo ""
fi

# Build options
OPTIONS="--timeout $TIMEOUT --recurse"

if [ "$JSON_OUTPUT" = true ]; then
    OPTIONS="$OPTIONS --format json"
fi

# Run link checker
if [ "$VERBOSE" = true ] && [ "$JSON_OUTPUT" = false ]; then
    echo "Running link checker (this may take 30-60 seconds)..."
    echo ""
fi

# Execute the check
cd "$(git rev-parse --show-toplevel)" || exit 1

if python .claude/scenarios/check-broken-links/link_checker.py "$DOCS_URL" $OPTIONS; then
    EXIT_CODE=0
    if [ "$JSON_OUTPUT" = false ]; then
        echo ""
        echo "✓ SUCCESS: All documentation links are valid"
    fi
else
    EXIT_CODE=$?
    if [ "$JSON_OUTPUT" = false ]; then
        echo ""
        echo "✗ FAILURE: Broken links detected (exit code: $EXIT_CODE)"
        echo ""
        echo "Next steps:"
        echo "  1. Review broken links listed above"
        echo "  2. Update or remove invalid URLs in documentation"
        echo "  3. Re-run this script to verify fixes"
    fi
fi

exit $EXIT_CODE
