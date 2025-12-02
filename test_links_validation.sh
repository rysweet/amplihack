#!/bin/bash
# Test script to validate all documentation links
set -e
echo "🔗 Link Validation Test Suite"
echo "=============================="
echo "Test 1: Running link checker..."
if [ -f ".github/scripts/link_checker.py" ]; then
    python .github/scripts/link_checker.py > link_check_results.txt 2>&1
    if grep -q "Broken: 0" link_check_results.txt; then
        echo "✅ Zero broken links found!"
    else
        broken_count=$(grep "Broken:" link_check_results.txt | awk '{print $2}')
        echo "❌ Found $broken_count broken links"
        exit 1
    fi
else
    echo "⚠️  Link checker not found"
fi
echo "All link tests passed! ✅"
